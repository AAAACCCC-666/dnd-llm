from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, AsyncGenerator
import json

from .. import schemas
from ..db import crud, database
from ..services import langchain_service  # 使用新的 LangChain 服务
from ..services.options_service import generate_conversation_options
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/messages", response_model=schemas.ChatMessage)
async def send_message(
    session_id: str,
    request: schemas.MessageSendRequest,
    db: Session = Depends(database.get_db),
):
    # 1. Check if session exists
    db_session = crud.get_session(db, session_id=session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Save user message
    user_message = schemas.ChatMessageCreate(
        session_id=session_id, role="user", content=request.content
    )
    db_user_message = crud.create_chat_message(db, message=user_message)

    # 3. Call LangChain service (non-streaming for this endpoint)
    # For a simple non-streaming response, you might call a different service method
    # This example assumes the main interaction is streaming, so we'll focus on that.
    # Here, we'll just return the saved user message as a placeholder.
    # A full implementation would get a response from the LLM.

    # Placeholder: In a real scenario, you'd get a response from the LLM
    # and save it. For now, just returning the user's message.
    # We will implement the actual LLM call in the streaming endpoint.
    return db_user_message


@router.get("/history", response_model=List[schemas.ChatMessage])
def get_chat_history(
    session_id: str = Query(..., description="The ID of the chat session"),
    db: Session = Depends(database.get_db),
):
    db_session = crud.get_session(db, session_id=session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 使用支持选项的新函数
    messages = crud.get_messages_with_suggestions_by_session(db, session_id=session_id)
    return messages


async def sse_event_stream(
    session_id: str, user_content: str, db: Session
) -> AsyncGenerator[str, None]:
    """
    Handles the streaming of SSE events from LangChain service.
    Saves assistant messages to the database.
    """
    try:
        # 1. Save user message (if not already saved by a POST endpoint)
        #    For a GET stream, the user message might be passed as a query param or part of the initial setup.
        #    Here, we assume user_content is the new message to process.
        user_msg_schema = schemas.ChatMessageCreate(
            session_id=session_id, role="user", content=user_content
        )
        crud.create_chat_message(db, message=user_msg_schema)

        # 2. Check character health - if <= 0, generate death narration and end game
        characters = crud.get_characters_by_session_id(db, session_id=session_id)
        player_character = None
        for char in characters:
            if getattr(char, "is_player", False):
                player_character = char
                break
        if player_character is not None and player_character.health is not None and player_character.health <= 0:  # type: ignore
            # Generate death narration (could be more detailed based on context)
            death_narration = (
                f"Your health has dropped to {player_character.health}. "
                "You succumb to your injuries and die. Game over."
            )
            # Save assistant message with death narration
            death_msg = schemas.ChatMessageCreate(
                session_id=session_id,
                role="assistant",
                content=death_narration,
            )
            crud.create_chat_message(db, message=death_msg)
            # Send death narration as delta
            yield f"data: {json.dumps({'delta': death_narration})}\n\n"
            # Send game over event to frontend
            yield f"data: {json.dumps({'event': 'game_over', 'message': 'You are dead. The game is over.'})}\n\n"
            # Send stream_end to close stream
            yield f"data: {json.dumps({'event': 'stream_end', 'reason': 'player_death'})}\n\n"
            db.commit()
            db.close()
            return

        # 3. Call simplified LangChain service - 直接传递session_id和db
        current_assistant_content = ""

        async for event_data in langchain_service.get_langchain_stream(session_id, db):
            if "delta" in event_data and event_data.get("event") is None:
                chunk = event_data.get("delta", "")
                current_assistant_content += chunk
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
            else:
                # 同时检查 "type" 和 "event" 字段以支持不同的事件格式
                event_type = event_data.get("type") or event_data.get("event")

                if event_type == "suggestions_generated":
                    # 直接转发选项生成事件
                    yield f"data: {json.dumps(event_data)}\n\n"
                elif event_type == "tool_start":
                    # If there's preceding text from the assistant, save it first.
                    if current_assistant_content:
                        pre_tool_call_assistant_msg = schemas.ChatMessageCreate(
                            session_id=session_id,
                            role="assistant",
                            content=current_assistant_content,
                        )
                        crud.create_chat_message(
                            db, message=pre_tool_call_assistant_msg
                        )
                        current_assistant_content = (
                            ""  # Reset for any text after tool calls
                        )

                    # Save the assistant message that requests the tool call
                    assistant_tool_request_msg = schemas.ChatMessageCreate(
                        session_id=session_id,
                        role="assistant",
                        content=None,  # Or a placeholder like f"Calling tool: {event_data['name']}"
                        name=event_data["name"],
                        tool_call_id=event_data["id"],
                        tool_arguments=event_data.get("args", {}),
                    )
                    crud.create_chat_message(db, message=assistant_tool_request_msg)
                    yield f"data: {json.dumps({'event': 'tool_call_start', 'id': event_data['id'], 'name': event_data['name'], 'arguments': event_data.get('args', {})})}\n\n"

                elif event_type == "tool_result" or event_type == "tool_error":
                    tool_call_id = event_data["id"]
                    tool_name = event_data["name"]
                    payload_content = (
                        event_data.get("result")
                        if event_type == "tool_result"
                        else event_data.get("error", "Unknown error")
                    )
                    tool_msg_schema = schemas.ChatMessageCreate(
                        session_id=session_id,
                        role="tool",
                        content=str(payload_content),
                        name=tool_name,
                        tool_call_id=tool_call_id,
                    )
                    crud.create_chat_message(db, message=tool_msg_schema)

                    event_name_to_yield = (
                        "tool_call_result"
                        if event_type == "tool_result"
                        else "tool_call_error"
                    )
                    yield f"data: {json.dumps({'event': event_name_to_yield, 'id': tool_call_id, 'name': tool_name, 'payload': payload_content})}\n\n"

                    # After processing tool_result, check if health dropped to <=0
                    if (
                        tool_name == "modify_character_integer_attribute"
                        and event_type == "tool_result"
                    ):
                        # Parse character_id from tool arguments (if available)
                        # We can't easily get character_id from payload, but we can query the session's player character
                        characters = crud.get_characters_by_session_id(
                            db, session_id=session_id
                        )
                        player_character = None
                        for char in characters:
                            if getattr(char, "is_player", False):
                                player_character = char
                                break
                        if player_character is not None and player_character.health is not None and player_character.health <= 0:  # type: ignore
                            # Generate death narration
                            death_narration = (
                                f"Your health has dropped to {player_character.health}. "
                                "You succumb to your injuries and die. Game over."
                            )
                            # Save assistant message with death narration
                            death_msg = schemas.ChatMessageCreate(
                                session_id=session_id,
                                role="assistant",
                                content=death_narration,
                            )
                            crud.create_chat_message(db, message=death_msg)
                            # Send death narration as delta
                            yield f"data: {json.dumps({'delta': death_narration})}\n\n"
                            # Send game over event
                            yield f"data: {json.dumps({'event': 'game_over', 'message': 'You are dead. The game is over.'})}\n\n"
                            # Send stream_end to close stream
                            yield f"data: {json.dumps({'event': 'stream_end', 'reason': 'player_death'})}\n\n"
                            db.commit()
                            db.close()
                            return

                elif event_type == "stream_end":
                    # Save any remaining assistant content (text generated after tool calls)
                    last_assistant_message = None
                    if current_assistant_content:
                        final_assistant_text_msg = schemas.ChatMessageCreate(
                            session_id=session_id,
                            role="assistant",
                            content=current_assistant_content,
                        )
                        last_assistant_message = crud.create_chat_message(
                            db, message=final_assistant_text_msg
                        )
                        current_assistant_content = ""  # Clear after saving

                    # If no assistant message was saved at all during this turn (e.g. only tool calls happened and no text output)
                    # and no tool request message was saved, save an empty assistant message.
                    # This case might be rare if tool_start always saves an assistant message.
                    # However, if the stream ends without any delta or tool_start, we might need this.
                    # Let's refine: if no assistant message (text or tool request) has been saved for this turn,
                    # and no tool messages were processed, it implies an empty or non-interactive response.
                    # The current logic for tool_start ensures an assistant message is saved for tool requests.
                    # The logic for current_assistant_content ensures text parts are saved.
                    # So, an explicit empty assistant message might only be needed if the stream is truly empty.

                    # The `langchain_service` is expected to yield `stream_end` once.
                    # All messages should have been saved by this point based on the events.
                    db.commit()  # Commit all changes made during the stream
                    yield f"data: {json.dumps({'event': 'stream_end', 'reason': event_data.get('reason')})}\n\n"

                    # 在流结束后生成选项
                    if last_assistant_message:
                        try:
                            # 确保获取正确的消息ID
                            message_id = getattr(last_assistant_message, "id", None)
                            if message_id is not None:
                                suggestions = await generate_conversation_options(
                                    session_id, db, message_id
                                )
                                if suggestions:
                                    yield f"data: {json.dumps({'event': 'suggestions_generated', 'suggestions': suggestions})}\n\n"
                        except Exception as e:
                            logger.error(f"Error generating conversation options: {e}")
                            # 选项生成失败不影响主流程

                    return

        # Fallback save logic (should ideally not be hit if stream_end is always processed)
        # This section attempts to save any residual data if the loop finishes unexpectedly.
        if current_assistant_content:  # Any final text not caught by stream_end
            fallback_assistant_msg = schemas.ChatMessageCreate(
                session_id=session_id,
                role="assistant",
                content=current_assistant_content,
            )
            crud.create_chat_message(db, message=fallback_assistant_msg)

        if db.new or db.dirty or db.deleted:  # Check if there's anything to commit
            db.commit()

    except Exception as e:
        logger.error(f"Error during SSE stream processing: {e}")
        yield f"data: {json.dumps({'error': str(e), 'event': 'error'})}\n\n"
    finally:
        db.close()  # Ensure the session is closed if get_db was used directly


@router.post("/stream")  # Changed from GET with query params to POST with request body
async def chat_stream_sse(
    request: schemas.MessageSendRequest,  # content is now in the request body
    session_id: str = Query(
        ..., description="The ID of the chat session"
    ),  # session_id can remain a query param or be moved to path
    # db: Session = Depends(database.get_db), # get_db creates a new session
):
    # Create a new DB session specifically for this stream if needed, or manage carefully
    # For long-lived SSE, it's often better to manage session scope carefully.
    # Here, get_db() will provide a session, and it will be closed in sse_event_stream's finally block.
    db_for_stream = next(database.get_db())

    db_session = crud.get_session(db_for_stream, session_id=session_id)
    if not db_session:
        db_for_stream.close()
        raise HTTPException(status_code=404, detail="Session not found for streaming")

    return StreamingResponse(
        sse_event_stream(session_id, request.content, db_for_stream),
        media_type="text/event-stream",
    )
