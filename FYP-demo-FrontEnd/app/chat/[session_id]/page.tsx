/* eslint-disable @typescript-eslint/no-unused-vars */
"use client"

import * as React from "react"
import { useEffect, useState, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { NavActions } from "@/components/nav-actions"
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, History } from "lucide-react";
import { CharacterMissingNotice } from "@/components/chat/create-character-multi-step";
import { ChatInterface } from "@/components/chat/chat-interface";
import { CharacterInfo } from "@/components/chat/character-info";
import { Inventory } from "@/components/chat/inventory";
import { ArchiveSelector } from "@/components/chat/archive-selector";
import { NewAdventureButton } from "@/components/chat/new-adventure-button";
import { HomeButton } from "@/components/chat/home-button";
import { buildApiUrl } from "@/lib/api";
import { StorySynopsisStep } from "@/components/chat/story-synopsis-step"
import { createStoryForSession, getStoryIdForSession } from "@/lib/story";

interface ToolCall {
  id: string;
  name: string;
  status: "start" | "result" | "error";
  args?: unknown;
  result?: unknown;
  error?: string;
}

// Define chat message types (can be moved to shared types file)
export interface ChatMessage {
  id: number;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  suggestions?: string[]; // Options array
  tool_calls?: ToolCall[]; // Tool calls array
}

// Define D&D base data and character creation types
export interface DndDataResponse {
  races: { [id: string]: string };
  classes: { [id: string]: string };
  spells: { [id: string]: string };
  features: { [id: string]: string };
  proficiencies: { [id: string]: string };
}

export interface CharacterCreatePayload {
  name: string;
  session_id: string;
  race_id: number;
  class_id: number;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  proficiency_ids: number[];
  spell_ids: number[];
  is_player: boolean;
  is_male?: boolean;
}

export type CharacterCreationFormData = Omit<CharacterCreatePayload, 'session_id' | 'is_player'>;

export default function ChatPage() {
  const params = useParams();
  const sessionId = params?.session_id as string | undefined;
  const router = useRouter();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const scrollAreaRootRef = useRef<HTMLDivElement | null>(null);
  const [showScrollToBottomButton, setShowScrollToBottomButton] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [showHistory, setShowHistory] = useState(false); // Control whether to show history conversation

  // New state management
  type PageStatus = "loading" | "character_missing" | "synopsis" | "chat_ready" | "error";
  const [pageStatus, setPageStatus] = useState<PageStatus>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [storyId, setStoryId] = useState<string | null>(null);
  // Game over state
  const [gameOver, setGameOver] = useState<boolean>(false);
  const [gameOverMessage, setGameOverMessage] = useState<string | null>(null);

  // Character creation related states
  const [dndData, setDndData] = useState<DndDataResponse | null>(null);
  const [isCreatingCharacter, setIsCreatingCharacter] = useState(false);
  const [characterCreationError, setCharacterCreationError] = useState<string | null>(null);
  const [characterCreated, setCharacterCreated] = useState(false);
  const [playerDataRefreshToken, setPlayerDataRefreshToken] = useState(0);
  const characterInfoRef = useRef<{ clearHighlights: () => void } | null>(null);

  const fetchDndData = React.useCallback(async () => {
    if (!sessionId) return;
    try {
      setCharacterCreationError(null);
      const response = await fetch(buildApiUrl("/characters/dnd-data"));
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error fetching D&D data" }));
        throw new Error(errorData.detail || `Failed to fetch D&D data: ${response.statusText}`);
      }
      const data: DndDataResponse = await response.json();
      setDndData(data);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "An unknown error occurred while fetching D&D data.";
      setCharacterCreationError(errMsg);
      console.error("Error fetching D&D data:", err);
    }
  }, [sessionId]);

  const handleCreateCharacter = async (formData: CharacterCreationFormData) => {
    if (!sessionId) {
      setCharacterCreationError("Session ID is missing.");
      return;
    }

    setIsCreatingCharacter(true);
    setCharacterCreationError(null);

    const payload: CharacterCreatePayload = {
      ...formData,
      session_id: sessionId,
      is_player: true,
    };

    try {
      const response = await fetch(buildApiUrl("/characters"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error creating character" }));
        throw new Error(errorData.detail || `Failed to create character: ${response.statusText} (${response.status})`);
      }

      setCharacterCreated(true);

      try {
        // After successful character creation, create corresponding Story for current session and save story_id
        const createdStoryId = await createStoryForSession(sessionId);
        setStoryId(createdStoryId);
        setPageStatus('synopsis');
      } catch (storyErr) {
        console.error("Error creating story after character creation:", storyErr);

        // 检查是否是LLM配置错误，提供更友好的错误信息
        const errorMessage = storyErr instanceof Error ? storyErr.message : "Unknown error";
        if (errorMessage.includes("LLM配置错误") || errorMessage.includes("LLM configuration")) {
          console.warn("LLM configuration error detected, falling back to direct chat mode");
          // 显示用户友好的提示信息
          setCharacterCreationError("故事生成功能暂时不可用，已切换到直接聊天模式。请检查后端LLM配置。");
        }

        // If story generation fails, fall back to direct chat flow
        setPageStatus('chat_ready');
        await handleSendMessage("start the adventure");
      }


    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "An unknown error occurred during character creation.";
      setCharacterCreationError(errMsg);
      console.error("Error creating character:", err);
    } finally {
      setIsCreatingCharacter(false);
    }
  };

  const fetchData = React.useCallback(async () => {
    if (!sessionId) {
      setPageStatus('error');
      setErrorMessage("Session ID is missing.");
      return;
    }
    setPageStatus('loading');
    setErrorMessage(null);
    setSendError(null);
    setMessages([]);
    setCharacterCreationError(null); // Reset character creation error on new fetch
    setCharacterCreated(false); // Reset character created flag

    try {
      const sessionInfoUrl = buildApiUrl(`/sessions/${sessionId}`);
      const sessionResponse = await fetch(sessionInfoUrl);

      if (!sessionResponse.ok) {
        const errorData = await sessionResponse.json().catch(() => ({ detail: "Unknown error fetching session info" }));
        let errMsg = `Failed to load session details: ${sessionResponse.statusText} (${sessionResponse.status})`;
        if (errorData.detail) errMsg += ` - ${errorData.detail}`;
        setErrorMessage(errMsg);
        setPageStatus('error');
        if (sessionResponse.status === 404) router.push('/');
        return;
      }

      const sessionData = await sessionResponse.json();

      // Try to restore the story_id corresponding to this session from local storage (if previously created)
      const existingStoryId = sessionId ? getStoryIdForSession(sessionId) : null;
      if (existingStoryId) {
        setStoryId(existingStoryId);
      } else {
        setStoryId(null);
      }
      if (sessionData.is_main_character_exist) {
        const chatHistoryUrl = buildApiUrl(`/chat/history?session_id=${sessionId}`);
        const chatResponse = await fetch(chatHistoryUrl);
        if (!chatResponse.ok) {
          const errorData = await chatResponse.json().catch(() => ({ detail: "Unknown error fetching chat history" }));
          let errMsg = `Failed to load chat history: ${chatResponse.statusText} (${chatResponse.status})`;
          if (errorData.detail) errMsg += ` - ${errorData.detail}`;
          setErrorMessage(errMsg);
          setPageStatus('error');
          return;
        }
        const chatData: ChatMessage[] = await chatResponse.json();
        setMessages(chatData);
        setPageStatus('chat_ready');
        setCharacterCreated(true);
      } else {
        setPageStatus('character_missing');
        await fetchDndData(); // Get data needed for character creation
      }

    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "An unknown error occurred during data fetching.";
      setErrorMessage(errMsg);
      setPageStatus('error');
      console.error("Error fetching data:", err);
    }
  }, [sessionId, router, fetchDndData]);


  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (pageStatus === 'chat_ready' && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "auto" });
    }
  }, [messages, pageStatus]);

  useEffect(() => {
    const viewport = scrollAreaRootRef.current?.querySelector<HTMLDivElement>('[data-radix-scroll-area-viewport]');
    if (!viewport) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = viewport;
      // Show button when scrollbar is not at bottom (with 10px threshold)
      const atBottom = scrollHeight - scrollTop - clientHeight < 10;
      setShowScrollToBottomButton(!atBottom);
    };

    viewport.addEventListener("scroll", handleScroll);
    handleScroll(); // Check immediately after component loads

    return () => {
      viewport.removeEventListener("scroll", handleScroll);
    };
  }, [messages, pageStatus]); // Dependency on pageStatus

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    // Or, if ScrollArea has its own scroll API, it can also be used
    // const viewport = scrollAreaRootRef.current?.querySelector<HTMLDivElement>('[data-radix-scroll-area-viewport]');
    // viewport?.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' });
  };

  const handleSendMessage = async (content: string) => { // Accept content parameter
    if (!content.trim() || !sessionId || isSending || (pageStatus !== 'chat_ready' && pageStatus !== 'character_missing')) return;

    // Clear attribute highlights when user sends a message (new conversation turn)
    if (characterInfoRef.current) {
      characterInfoRef.current.clearHighlights();
    }

    setIsSending(true);
    setSendError(null); // Use sendError for this context

    const userMessageContent = content.trim(); // Use the passed content

    // Optimistically add user message
    const userMessage: ChatMessage = {
      id: Date.now(), // Temporary ID
      session_id: sessionId,
      role: "user",
      content: userMessageContent,
      created_at: new Date().toISOString(),
    };
    setMessages((prevMessages) => [...prevMessages, userMessage]);

    const assistantMessageId = Date.now() + 1; // Temporary ID for assistant message
    const placeholderAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      session_id: sessionId,
      role: "assistant",
      content: "▋", // Typing indicator
      created_at: new Date().toISOString(),
    };
    setMessages((prevMessages) => [...prevMessages, placeholderAssistantMessage]);

    let accumulatedContent = "";
    let streamEndedGracefully = false;

    try {
      const streamUrl = buildApiUrl(`/chat/stream?session_id=${sessionId}`);
      const response = await fetch(streamUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: userMessageContent }),
      });

      if (!response.ok || !response.body) {
        const errorText = response.body ? await response.text().catch(() => "Could not read error body.") : "No response body";
        throw new Error(
          `API request failed: ${response.status} ${response.statusText}. ${errorText}`
        );
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let playerDataRefreshedForThisTurn = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (!streamEndedGracefully) {
            console.warn("SSE stream ended prematurely without a stream_end event.");
            setMessages((prevMessages) =>
              prevMessages.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: accumulatedContent || "Response stream ended." }
                  : msg
              )
            );
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        let eolIndex;
        while ((eolIndex = buffer.indexOf("\n\n")) >= 0) {
          const eventString = buffer.substring(0, eolIndex);
          buffer = buffer.substring(eolIndex + 2);

          if (eventString.startsWith("data: ")) {
            const jsonData = eventString.substring("data: ".length);
            try {
              const parsedData = JSON.parse(jsonData);
              if (parsedData.delta) {
                accumulatedContent += parsedData.delta;
                setMessages((prevMessages) =>
                  prevMessages.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: accumulatedContent + "▋" }
                      : msg
                  )
                );
              } else if (parsedData.event === "tool_call_start") {
                const toolCallId = typeof parsedData.id === "string" ? parsedData.id : String(parsedData.id ?? `${assistantMessageId}-tool`);
                const toolCall: ToolCall = {
                  id: toolCallId,
                  name: parsedData.name,
                  status: "start",
                  args: parsedData.arguments,
                };
                setMessages((prevMessages) =>
                  prevMessages.map((msg) => {
                    if (msg.id === assistantMessageId) {
                      const updatedToolCalls = msg.tool_calls ? [...msg.tool_calls, toolCall] : [toolCall];
                      return { ...msg, tool_calls: updatedToolCalls };
                    }
                    return msg;
                  })
                );
              } else if (parsedData.event === "tool_call_result") {
                const toolCallId = typeof parsedData.id === "string" ? parsedData.id : String(parsedData.id ?? "");
                setMessages((prevMessages) =>
                  prevMessages.map((msg) => {
                    if (msg.id === assistantMessageId && msg.tool_calls) {
                      const updatedToolCalls = msg.tool_calls.map((tc) =>
                        tc.id === toolCallId
                          ? { ...tc, status: "result" as const, result: parsedData.payload }
                          : tc
                      );
                      return { ...msg, tool_calls: updatedToolCalls };
                    }
                    return msg;
                  })
                );
              } else if (parsedData.event === "tool_call_error") {
                const toolCallId = typeof parsedData.id === "string" ? parsedData.id : String(parsedData.id ?? "");
                const errorPayload = parsedData.payload;
                const errorMessage =
                  typeof errorPayload === "string"
                    ? errorPayload
                    : errorPayload
                      ? JSON.stringify(errorPayload)
                      : "Unknown tool call error";
                setMessages((prevMessages) =>
                  prevMessages.map((msg) => {
                    if (msg.id === assistantMessageId && msg.tool_calls) {
                      const updatedToolCalls = msg.tool_calls.map((tc) =>
                        tc.id === toolCallId
                          ? { ...tc, status: "error" as const, error: errorMessage }
                          : tc
                      );
                      return { ...msg, tool_calls: updatedToolCalls };
                    }
                    return msg;
                  })
                );
                setSendError(`Tool Call Error: ${errorMessage}`);
              } else if (parsedData.event === "stream_end") {
                streamEndedGracefully = true;
                setMessages((prevMessages) =>
                  prevMessages.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: accumulatedContent, created_at: new Date().toISOString() }
                      : msg
                  )
                );
                if (!playerDataRefreshedForThisTurn) {
                  playerDataRefreshedForThisTurn = true;
                  setPlayerDataRefreshToken((prev) => prev + 1);
                }
                // No need to explicitly break or return here, outer loop's done will handle it.
              } else if (parsedData.event === "suggestions_generated") {
                // Handle suggestions generation event
                const suggestions = parsedData.suggestions || [];
                if (suggestions.length > 0) {
                  // Update current assistant message, add suggestions
                  setMessages((prevMessages) =>
                    prevMessages.map((msg) =>
                      msg.id === assistantMessageId
                        ? { ...msg, suggestions }
                        : msg
                    )
                  );
                }
              } else if (parsedData.event === "game_over") {
                // Handle game over event
                const message = parsedData.message || "You are dead. The game is over.";
                setGameOver(true);
                setGameOverMessage(message);
                // Optionally, we can also add a system message to the chat
                const gameOverMessage: ChatMessage = {
                  id: Date.now() + 2,
                  session_id: sessionId,
                  role: "assistant",
                  content: `[Game over] ${message}`,
                  created_at: new Date().toISOString(),
                };
                setMessages((prevMessages) => [...prevMessages, gameOverMessage]);
              } else if (parsedData.event === "error" || parsedData.error) { // Handle explicit error events
                const sseErrorMsg = parsedData.error || "Unknown SSE error event";
                console.error("SSE Error Event:", sseErrorMsg);
                setSendError(`LLM Error: ${sseErrorMsg}`);
                setMessages(prev => prev.map(msg => msg.id === assistantMessageId ? { ...msg, content: `${accumulatedContent}\n\nError: ${sseErrorMsg}`.replace("▋", "") } : msg));
                streamEndedGracefully = true; // Treat error as a form of stream end for cleanup
              }
            } catch (e) {
              console.error("Error parsing SSE JSON data:", e, jsonData);
            }
          }
        }
      }
    } catch (err) {
      console.error("Failed to send message or process stream:", err);
      const errMessage = err instanceof Error ? err.message : "An unknown error occurred.";
      setSendError(errMessage);
      setMessages((prevMessages) =>
        prevMessages.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: `Error: ${errMessage}`.replace("▋", "") }
            : msg
        )
      );
    } finally {
      setIsSending(false);
      // Final cleanup of assistant message placeholder
      setMessages(prev => prev.map(msg => {
        if (msg.id === assistantMessageId) {
          let finalContent = msg.content;
          if (finalContent.endsWith("▋")) {
            finalContent = finalContent.slice(0, -1); // Remove typing indicator
          }
          // If accumulated content is empty and no error was explicitly set for this message
          // and there are no tool calls (tool calls indicate a valid response)
          if (accumulatedContent === "" && !sendError && !msg.content.toLowerCase().includes("error") && (!msg.tool_calls || msg.tool_calls.length === 0)) {
            finalContent = "Assistant provided no response.";
          }
          return { ...msg, content: finalContent || "Response processing finished." };
        }
        return msg;
      }));
    }
  };

  // Get current conversation (most recent set of user-assistant dialogue)
  const getCurrentConversation = (allMessages: ChatMessage[]): ChatMessage[] => {
    if (allMessages.length === 0) return [];

    // Find the most recent assistant message
    const lastAssistantMessageIndex = allMessages
      .map((msg, index) => ({ msg, index }))
      .filter(({ msg }) => msg.role === "assistant")
      .pop()?.index;

    if (lastAssistantMessageIndex === undefined) {
      // If no assistant messages, return all messages
      return allMessages;
    }

    // Find the user message corresponding to the most recent assistant message
    let startIndex = lastAssistantMessageIndex;
    while (startIndex > 0 && allMessages[startIndex - 1].role === "user") {
      startIndex--;
    }

    // Return all messages from the found user message to the most recent assistant message
    return allMessages.slice(startIndex);
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Top bar */}
      <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-background px-3">
        <div className="flex-1">
          <h1 className="text-lg font-semibold">Chat: {sessionId?.substring(0, 8)}...</h1>
        </div>
        <div className="flex items-center gap-2">
          <HomeButton />
          <NewAdventureButton />
          <ArchiveSelector />
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-2"
          >
            <History className="h-4 w-4" />
            {showHistory ? "Current Conversation" : "History Conversation"}
          </Button>
          <NavActions />
        </div>
      </header>
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {pageStatus === 'loading' && (
          <div className="p-6 space-y-3">
            <Skeleton className="h-16 w-3/4" />
            <Skeleton className="h-12 w-1/2 ml-auto" />
            <Skeleton className="h-20 w-5/6" />
          </div>
        )}
        {pageStatus === 'error' && errorMessage && (
          <Alert variant="destructive" className="m-6">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error Loading Chat</AlertTitle>
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        )}
        {pageStatus === 'character_missing' && sessionId && (
          <CharacterMissingNotice
            sessionId={sessionId}
            dndData={dndData}
            onSubmit={handleCreateCharacter}
            isCreating={isCreatingCharacter}
            error={characterCreationError}
          />
        )}
        {pageStatus === 'synopsis' && sessionId && storyId && (
          <StorySynopsisStep
            storyId={storyId}
            sessionId={sessionId}
            onConfirm={async () => {
              setPageStatus('chat_ready');
              await handleSendMessage("start the adventure");
            }}
          />
        )}

        {pageStatus === 'chat_ready' && sessionId && (
          <div className="flex h-full">
            {/* Left sidebar */}
            <div className="w-80 border-r bg-background flex flex-col">
              {/* Top left - Mini map placeholder */}
              <div className="p-4 border-b">
                <div className="bg-gray-100 rounded-lg border-2 border-dashed border-gray-300 h-40 flex items-center justify-center">
                  <div className="text-center text-gray-500">
                    <div className="text-lg mb-2">🗺️</div>
                    <div className="text-sm">Mini Map</div>
                    <div className="text-xs text-gray-400 mt-1">Feature to be implemented</div>
                  </div>
                </div>
              </div>

              {/* Bottom left - Character information */}
              <div className="flex-1 p-4 overflow-y-auto">
                <CharacterInfo
                  ref={characterInfoRef}
                  sessionId={sessionId}
                  refreshToken={playerDataRefreshToken}
                />
              </div>
            </div>

            {/* Middle - Main chat area */}
            <div className="flex-1 flex flex-col">
              <ChatInterface
                sessionId={sessionId}
                initialMessages={showHistory ? messages : getCurrentConversation(messages)}
                onSendMessage={handleSendMessage}
                isSending={isSending}
                sendError={sendError}
                messagesEndRef={messagesEndRef}
                scrollAreaRootRef={scrollAreaRootRef}
                showScrollToBottomButton={showScrollToBottomButton}
                scrollToBottom={scrollToBottom}
                showHistory={showHistory}
                gameOver={gameOver}
                gameOverMessage={gameOverMessage || "You are dead. The game is over."}
              />
            </div>

            {/* Right sidebar - Inventory */}
            <div className="w-80 border-l bg-background p-4 overflow-y-auto">
              <Inventory sessionId={sessionId} refreshToken={playerDataRefreshToken} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
