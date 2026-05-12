import json
import time
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import cast

from .. import schemas
from ..db import crud, database, models
from ..utils.character_utils import character_to_dict
from ..services.outline_planner_agent import generate_plot_outline
from ..services.synopsis_agent import (
    generate_plot_synopsis,
    generate_plot_synopsis_stream,
)
from ..services.revision_agent import run_revision

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=schemas.StoryWithOutlineResponse,
    summary="Create a new story and generate initial plot outline",
)
async def create_story_and_outline(
    request: schemas.StoryCreateRequest,
    db: Session = Depends(database.get_db),
):
    """
    创建新故事并生成剧情列表。

    流程：
    1. 使用 OutlinePlannerAgent 根据 theme/style 生成剧情列表（至少 N 个节点）。
    2. 在数据库中创建 Story 记录。
    3. 将生成的剧情列表作为 version=1 的 PlotOutline 存库，并标记 is_active=true。
    4. 返回 story_id 和当前激活的剧情列表。
    """
    player_character = None
    if request.session_id:
        characters = crud.get_characters_by_session_id(db, request.session_id)
        player_character_model = next(
            (c for c in characters if getattr(c, "is_player", False)), None
        )
        if player_character_model:
            player_character = character_to_dict(player_character_model, db)

    outline = await generate_plot_outline(
        theme=request.theme or request.title,
        min_nodes=request.N,
        style=request.style,
        player_character=player_character,
    )

    if outline is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate plot outline. Please check LLM configuration.",
        )

    story = crud.create_story(
        db=db,
        title=request.title,
        theme=request.theme,
        created_by=request.created_by,
    )

    db_outline = crud.create_plot_outline_for_story(
        db=db,
        story_id=int(getattr(story, "id", 0)),
        outline=outline,
        version=1,
        is_active=True,
    )

    response = schemas.StoryWithOutlineResponse(
        story_id=int(getattr(story, "id", 0)),
        title=cast(str, story.title),
        theme=(
            cast(str, story.theme)
            if getattr(story, "theme", None) is not None
            else None
        ),
        outline_version=int(getattr(db_outline, "version", 1)),
        outline=outline,
    )
    return response


@router.get(
    "/{story_id}",
    response_model=schemas.StoryDetailResponse,
    summary="Get story details with active outline and latest synopsis",
)
def get_story_detail(
    story_id: int,
    db: Session = Depends(database.get_db),
):
    """
    获取指定故事的详情：基础 Story 信息 + 当前激活的剧情列表 + 最新激活的简介。
    """
    story = crud.get_story(db, story_id=story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    db_outline = crud.get_active_plot_outline(db, story_id=story_id)
    outline_schema = None
    if db_outline is not None:
        try:
            nodes_raw = db_outline.nodes or []
            if not isinstance(nodes_raw, list):
                raise TypeError("Stored outline nodes are not a list")

            nodes = [schemas.PlotNodeSchema(**node_data) for node_data in nodes_raw]
            outline_schema = schemas.PlotOutlineSchema(nodes=nodes)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse stored plot outline: {e}",
            ) from e

    latest_synopsis = (
        db.query(models.Synopsis)
        .filter(models.Synopsis.story_id == story_id)
        .order_by(models.Synopsis.created_at.desc())
        .first()
    )

    story_schema = schemas.StorySchema.model_validate(story)
    synopsis_schema = (
        schemas.SynopsisSchema.model_validate(latest_synopsis)
        if latest_synopsis is not None
        else None
    )

    return schemas.StoryDetailResponse(
        story=story_schema,
        outline=outline_schema,
        synopsis=synopsis_schema,
    )


@router.post(
    "/{story_id}/synopsis",
    response_model=schemas.SynopsisSchema,
    summary="Generate synopsis for an existing story based on active plot outline",
)
async def generate_story_synopsis(
    story_id: int,
    request: schemas.SynopsisCreateRequest | None = None,
    stream: bool = False,
    db: Session = Depends(database.get_db),
):
    """
    根据当前剧情列表生成简介，可选使用 SSE 实时返回 token 增量。

    流程：
    1. 读取当前活跃的 PlotOutline；
    2. 调用 SynopsisAgent 生成简介；
    3. 非 stream 模式直接写数据库并回传结果，stream 模式则边生成边推 `delta`，最终触发 `done` 事件返回新简介 ID。
    """
    story = crud.get_story(db, story_id=story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    db_outline = crud.get_active_plot_outline(db, story_id=story_id)
    if db_outline is None:
        raise HTTPException(
            status_code=400,
            detail="No active plot outline found for this story.",
        )

    try:
        nodes_raw = db_outline.nodes or []
        if not isinstance(nodes_raw, list):
            raise TypeError("Stored outline nodes are not a list")

        nodes = [schemas.PlotNodeSchema(**node_data) for node_data in nodes_raw]
        outline_schema = schemas.PlotOutlineSchema(nodes=nodes)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse stored plot outline: {e}",
        ) from e

    style = request.style if request else None
    word_limit = request.word_limit if request else 100
    language = request.language if request else None

    if not stream:
        synopsis_text = await generate_plot_synopsis(
            outline=outline_schema,
            style=style,
            word_limit=word_limit,
            language=language,
        )

        if synopsis_text is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate synopsis from outline. Please try again.",
            )

        db_synopsis = crud.create_synopsis_for_story(
            db=db,
            story_id=int(getattr(story, "id", 0)),
            outline_version=int(getattr(db_outline, "version", 1)),
            content=synopsis_text,
            is_active=True,
        )

        return db_synopsis

    async def _synopsis_stream():
        text_parts: list[str] = []
        async for event in generate_plot_synopsis_stream(
            outline=outline_schema,
            style=style,
            word_limit=word_limit,
            language=language,
        ):
            if "delta" in event:
                text_parts.append(event["delta"])
                yield f"data: {json.dumps({'event': 'delta', 'text': event['delta']}, ensure_ascii=False)}\n\n"
            elif event.get("event") == "error":
                yield f"data: {json.dumps({'event': 'error', 'message': event.get('message')}, ensure_ascii=False)}\n\n"
                return

        final_text = "".join(text_parts).strip()
        if not final_text:
            yield f"data: {json.dumps({'event': 'error', 'message': 'Empty synopsis generated'}, ensure_ascii=False)}\n\n"
            return

        db_synopsis = crud.create_synopsis_for_story(
            db=db,
            story_id=int(getattr(story, "id", 0)),
            outline_version=int(getattr(db_outline, "version", 1)),
            content=final_text,
            is_active=True,
        )

        payload = {
            "event": "done",
            "synopsis_id": int(getattr(db_synopsis, "id", 0)),
            "outline_version": int(getattr(db_outline, "version", 1)),
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(_synopsis_stream(), media_type="text/event-stream")


@router.patch(
    "/{story_id}/nodes/{node_index}",
    response_model=schemas.PlotOutlineSchema,
    summary="Update status of a specific plot node (DM action)",
)
def update_plot_node_status(
    story_id: int,
    node_index: int,
    request: schemas.PlotNodeStatusUpdateRequest,
    db: Session = Depends(database.get_db),
):
    """
    DM 接口：更新某个剧情节点的状态（Pending / InProgress / Finish / Canceled）。
    操作对象为该故事当前激活的剧情列表。
    """
    story = crud.get_story(db, story_id=story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    outline = crud.update_plot_node_status(
        db=db,
        story_id=story_id,
        node_index=node_index,
        new_status=request.status,
    )
    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Active plot outline or specified node not found for this story.",
        )

    nodes_raw = outline.nodes or []
    if not isinstance(nodes_raw, list):
        raise HTTPException(
            status_code=500,
            detail="Stored outline nodes are not a list.",
        )

    nodes = [schemas.PlotNodeSchema(**node_data) for node_data in nodes_raw]
    return schemas.PlotOutlineSchema(nodes=nodes)


@router.patch(
    "/{story_id}/nodes/{node_index}/ending",
    response_model=schemas.PlotOutlineSchema,
    summary="Mark or unmark a plot node as ending (DM action)",
)
def mark_plot_node_as_ending(
    story_id: int,
    node_index: int,
    request: schemas.PlotNodeEndingUpdateRequest,
    db: Session = Depends(database.get_db),
):
    """
    DM 接口：标记/取消某个剧情节点为结局节点。
    操作对象为该故事当前激活的剧情列表。
    """
    story = crud.get_story(db, story_id=story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    outline = crud.mark_plot_node_as_ending(
        db=db,
        story_id=story_id,
        node_index=node_index,
        is_ending=request.is_ending,
    )
    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Active plot outline or specified node not found for this story.",
        )

    nodes_raw = outline.nodes or []
    if not isinstance(nodes_raw, list):
        raise HTTPException(
            status_code=500,
            detail="Stored outline nodes are not a list.",
        )

    nodes = [schemas.PlotNodeSchema(**node_data) for node_data in nodes_raw]
    return schemas.PlotOutlineSchema(nodes=nodes)


@router.post(
    "/{story_id}/feedback",
    response_model=schemas.PlayerFeedbackSchema,
    summary="Submit player feedback and trigger RevisionAgent",
)
async def submit_story_feedback(
    story_id: int,
    request: schemas.PlayerFeedbackCreateRequest,
    stream: bool = False,
    db: Session = Depends(database.get_db),
):
    """
    提交玩家反馈并调用 RevisionAgent 触发剧情与简介的更新流程。

    - 接收前端传来的 PlayerFeedbackSchema，保存原始反馈内容与版本号；
    - 将当前剧情、现有简介与反馈文本交给 RevisionAgent 生成新的 outline/synopsis，再通过 SSE 持续返回 delta，最终发送 done 事件。
    """
    logger.info(
        "Received feedback request story_id=%s stream=%s type=%s text=%s",
        story_id,
        stream,
        request.type,
        request.feedback_text,
    )
    logger.info("Starting feedback processing for story %s", story_id)

    story = crud.get_story(db, story_id=story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    try:
        logger.info("Getting active plot outline for story %s", story_id)
        db_outline = crud.get_active_plot_outline(db, story_id=story_id)
        if db_outline is None:
            logger.error("No active plot outline found for story %s", story_id)
            raise HTTPException(
                status_code=400,
                detail="No active plot outline found for this story.",
            )
        logger.info(
            "Found active outline version %s for story %s", db_outline.version, story_id
        )

        try:
            nodes_raw = db_outline.nodes or []
            if not isinstance(nodes_raw, list):
                raise TypeError("Stored outline nodes are not a list")

            nodes = [schemas.PlotNodeSchema(**node_data) for node_data in nodes_raw]
            outline_schema = schemas.PlotOutlineSchema(nodes=nodes)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse stored plot outline: {e}",
            ) from e

        logger.info("Getting latest synopsis for story %s", story_id)
        latest_synopsis = (
            db.query(models.Synopsis)
            .filter(models.Synopsis.story_id == story_id)
            .order_by(models.Synopsis.created_at.desc())
            .first()
        )
        logger.info("Latest synopsis found: %s", latest_synopsis is not None)
        original_synopsis_text: str | None = (
            cast(str, latest_synopsis.content) if latest_synopsis is not None else None
        )

        logger.info("Creating player feedback record for story %s", story_id)
        feedback = crud.create_player_feedback(
            db=db,
            story_id=story_id,
            outline_version=int(getattr(db_outline, "version", 1)),
            synopsis_id=(
                int(getattr(latest_synopsis, "id", 0))
                if latest_synopsis is not None
                else None
            ),
            feedback_text=request.feedback_text,
            feedback_type=request.type,
            processed=False,
        )
        # 保存feedback_id供流式响应使用
        feedback_id = int(getattr(feedback, "id", 0))
        logger.info("Created feedback record with id %s", feedback_id)

        logger.info("Starting RevisionAgent for story %s", story_id)
        revision_start = time.monotonic()
        try:
            revision = await run_revision(
                original_outline=outline_schema,
                original_synopsis=original_synopsis_text or "",
                feedback_text=request.feedback_text,
                task_type=request.type,
            )
        except Exception as exc:
            logger.exception("RevisionAgent call failed for story %s", story_id)
            raise HTTPException(
                status_code=500,
                detail="RevisionAgent call failed, please try again later.",
            ) from exc

        revision_duration = time.monotonic() - revision_start
        nodes_count = len(revision.outline.nodes) if revision is not None else 0
        logger.info(
            "RevisionAgent completed for story %s in %.2fs (nodes=%s)",
            story_id,
            revision_duration,
            nodes_count,
        )

        if revision is None:
            logger.error("RevisionAgent returned None for story %s", story_id)
            raise HTTPException(
                status_code=500,
                detail="RevisionAgent failed to produce a result.",
            )

        logger.info("Persisting new outline for story %s", story_id)
        try:
            latest_outline = crud.get_latest_outline_for_story(db, story_id=story_id)
            next_version = (
                int(getattr(latest_outline, "version", 1)) if latest_outline else 1
            ) + 1
            logger.info(
                "Creating new outline version %s for story %s", next_version, story_id
            )

            new_outline_record = crud.create_plot_outline_for_story(
                db=db,
                story_id=story_id,
                outline=revision.outline,
                version=next_version,
                is_active=True,
            )
            logger.info(
                "Successfully created new outline record with id %s",
                new_outline_record.id,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to persist new outline after revision for story %s", story_id
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to process player feedback, please try again.",
            ) from exc

        if not stream:
            # 复用RevisionAgent生成的简介，避免重复调用SynopsisAgent
            new_synopsis_text = revision.synopsis
            logger.info(
                "Using synopsis from RevisionAgent, text length: %s",
                len(new_synopsis_text) if new_synopsis_text else 0,
            )

            if not new_synopsis_text:
                logger.error(
                    "RevisionAgent returned empty synopsis for story %s",
                    story_id,
                )
                raise HTTPException(
                    status_code=500,
                    detail="RevisionAgent failed to generate synopsis.",
                )

            logger.info("Creating synopsis record in database for story %s", story_id)
            try:
                new_synopsis_record = crud.create_synopsis_for_story(
                    db=db,
                    story_id=story_id,
                    outline_version=int(getattr(new_outline_record, "version", 1)),
                    content=new_synopsis_text,
                    is_active=True,
                )
                logger.info(
                    "Successfully created synopsis record with id %s",
                    new_synopsis_record.id,
                )
            except Exception as e:
                logger.exception(
                    "Failed to create synopsis record for story %s", story_id
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save synopsis to database: {str(e)}",
                ) from e

            logger.info("Marking feedback as processed for story %s", story_id)
            try:
                processed_feedback = crud.mark_feedback_processed(
                    db=db,
                    feedback_id=int(getattr(feedback, "id", 0)),
                    outline_version=int(getattr(new_outline_record, "version", 1)),
                    synopsis_id=int(getattr(new_synopsis_record, "id", 0)),
                )
                logger.info("Successfully marked feedback as processed")
            except Exception as e:
                logger.exception(
                    "Failed to mark feedback processed for story %s", story_id
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update feedback status: {str(e)}",
                ) from e

            if processed_feedback is None:
                logger.error(
                    "mark_feedback_processed returned None for story %s", story_id
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update feedback status after revision.",
                )

            logger.info(
                "Feedback processing completed successfully for story %s", story_id
            )
            return processed_feedback

        async def _feedback_stream():
            stream_start = time.monotonic()
            try:
                logger.info(f"Starting feedback stream for story {story_id}")

                # 先发送一个心跳事件，确保连接建立
                heartbeat_data = f"data: {json.dumps({'event': 'heartbeat', 'message': 'stream_started'}, ensure_ascii=False)}\n\n"
                logger.info(f"Sending heartbeat event to establish SSE connection")
                yield heartbeat_data
                logger.info("Heartbeat event sent successfully")

                # 复用RevisionAgent生成的简介，通过流式方式发送
                new_synopsis_text = revision.synopsis
                logger.info(
                    "Using synopsis from RevisionAgent for streaming, text length: %s",
                    len(new_synopsis_text) if new_synopsis_text else 0,
                )

                if not new_synopsis_text:
                    logger.error(
                        "RevisionAgent returned empty synopsis for story %s", story_id
                    )
                    error_data = f"data: {json.dumps({'event': 'error', 'message': 'RevisionAgent failed to generate synopsis'}, ensure_ascii=False)}\n\n"
                    yield error_data
                    return

                # 将简介文本分割成字符流式发送，保持流式体验
                logger.info("Starting synopsis streaming from RevisionAgent output")
                chunk_count = 0
                for i, char in enumerate(new_synopsis_text):
                    chunk_count += 1
                    chunk_data = json.dumps(
                        {"event": "delta", "text": char}, ensure_ascii=False
                    )
                    sse_chunk = f"data: {chunk_data}\n\n"
                    yield sse_chunk

                logger.info("Synopsis streaming completed, sent %s chunks", chunk_count)
                logger.info(
                    "Feedback stream collected %s chars for story %s in %.2fs",
                    len(new_synopsis_text),
                    story_id,
                    time.monotonic() - stream_start,
                )

                # 使用新的数据库会话来避免会话过期问题
                new_db = database.SessionLocal()
                try:
                    logger.info(
                        "Creating synopsis record in database for story %s", story_id
                    )
                    new_synopsis_record = crud.create_synopsis_for_story(
                        db=new_db,
                        story_id=story_id,
                        outline_version=int(getattr(new_outline_record, "version", 1)),
                        content=new_synopsis_text,
                        is_active=True,
                    )
                    logger.info(
                        "Successfully created synopsis record with id %s",
                        new_synopsis_record.id,
                    )

                    logger.info("Marking feedback as processed for story %s", story_id)
                    processed_feedback = crud.mark_feedback_processed(
                        db=new_db,
                        feedback_id=feedback_id,
                        outline_version=int(getattr(new_outline_record, "version", 1)),
                        synopsis_id=int(getattr(new_synopsis_record, "id", 0)),
                    )
                    logger.info("Successfully marked feedback as processed")

                    if processed_feedback is None:
                        logger.error(
                            "Failed to mark feedback processed for story %s after streaming synopsis",
                            story_id,
                        )
                        yield f"data: {json.dumps({'event': 'error', 'message': 'Failed to update feedback status after revision.'}, ensure_ascii=False)}\n\n"
                        return

                    payload = {
                        "event": "done",
                        "feedback_id": int(getattr(processed_feedback, "id", 0)),
                        "outline_version": int(
                            getattr(new_outline_record, "version", 1)
                        ),
                        "synopsis_id": int(getattr(new_synopsis_record, "id", 0)),
                    }
                    logger.info("Sending done event with payload: %s", payload)
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.exception(
                        "Database operation failed in feedback stream for story %s",
                        story_id,
                    )
                    yield f"data: {json.dumps({'event': 'error', 'message': f'Database operation failed: {str(e)}'}, ensure_ascii=False)}\n\n"
                    return
                finally:
                    new_db.close()
            except Exception as exc:
                logger.exception("Feedback streaming failed for story %s", story_id)
                yield f"data: {json.dumps({'event': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
                return
            finally:
                stream_duration = time.monotonic() - stream_start
                logger.info(
                    "Feedback stream for story %s finished in %.2fs",
                    story_id,
                    stream_duration,
                )

        return StreamingResponse(_feedback_stream(), media_type="text/event-stream")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to handle feedback request for story %s", story_id)
        raise HTTPException(
            status_code=500,
            detail="Failed to process player feedback, please try again.",
        ) from exc
