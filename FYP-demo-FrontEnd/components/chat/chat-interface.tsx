"use client";

import * as React from "react";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, ArrowDown, Send } from "lucide-react";
import { DocumentQuery } from "./document-query";

interface ToolCall {
  id: string;
  name: string;
  status: "start" | "result" | "error";
  args?: unknown;
  result?: unknown;
  error?: string;
}

interface ChatMessage {
  id: number;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  suggestions?: string[]; // Options array
  tool_calls?: ToolCall[]; // Tool calls array
}

interface ChatInterfaceProps {
  sessionId: string;
  initialMessages: ChatMessage[];
  onSendMessage: (content: string) => Promise<void>;
  isSending: boolean;
  sendError: string | null;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  scrollAreaRootRef: React.RefObject<HTMLDivElement | null>;
  showScrollToBottomButton: boolean;
  scrollToBottom: () => void;
  showHistory: boolean; // Whether to show history conversation
  gameOver?: boolean; // Whether the game is over (player dead)
  gameOverMessage?: string; // Optional message to display
}

export function ChatInterface({
  sessionId,
  initialMessages,
  onSendMessage,
  isSending,
  sendError,
  messagesEndRef,
  scrollAreaRootRef,
  showScrollToBottomButton,
  scrollToBottom,
  showHistory, // Whether to show history conversation
  gameOver = false,
  gameOverMessage = "Game over"
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState("");

  const formatPayload = (payload: unknown) => {
    if (payload === null || payload === undefined) return "";
    if (typeof payload === "string") return payload;
    try {
      return JSON.stringify(payload, null, 2) ?? "";
    } catch (err) {
      console.warn("Failed to stringify tool payload", err, payload);
      return String(payload);
    }
  };

  // The useEffect that was here has been removed as it's redundant.
  // The component will re-render with new `initialMessages` prop directly.

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isSending) return;
    const messageToSend = inputValue.trim();
    setInputValue(""); // Clear input before sending for better UX
    await onSendMessage(messageToSend);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
  };

  return (
    <>
      <DocumentQuery />
      <ScrollArea ref={scrollAreaRootRef} className="flex-1 h-0 bg-muted/30">
        <div className="p-6 space-y-4">
          {/* Display mode prompt */}
          {showHistory && initialMessages.length > 0 && (
            <div className="text-center py-2">
              <p className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-2 inline-block">
                📜 Viewing full conversation history
              </p>
            </div>
          )}
          {!showHistory && initialMessages.length > 0 && (
            <div className="text-center py-2">
              <p className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-2 inline-block">
                💬 Viewing current conversation
              </p>
            </div>
          )}

          {initialMessages.length === 0 && (
            <p className="text-muted-foreground text-center py-10">
              No messages in this chat yet. Start the conversation!
            </p>
          )}
          {sendError && (
            <Alert variant="destructive" className="my-2">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Message Error</AlertTitle>
              <AlertDescription>{sendError}</AlertDescription>
            </Alert>
          )}
          {initialMessages.length > 0 &&
            initialMessages
              .filter((msg) => msg.content && msg.content.trim() !== "")
              .map((msg) => (
                <div
                  key={msg.id}
                  className={`p-3 rounded-lg max-w-[85%] break-words shadow-sm ${msg.role === "user"
                    ? "bg-primary text-primary-foreground self-end ml-auto"
                    : "bg-card text-card-foreground self-start mr-auto border"
                    }`}
                >
                  {/* Display tool calls inline with content */}
                  {msg.role === "assistant" && msg.tool_calls && msg.tool_calls.length > 0 && (
                    <div className="mb-3 pb-3 border-b border-border">
                      <div className="space-y-2">
                        <span className="text-xs text-muted-foreground">Tool calls:</span>
                        <div className="space-y-2">
                          {msg.tool_calls.map((toolCall, toolIndex) => (
                            <div
                              key={toolCall.id || `${msg.id}-tool-${toolIndex}`}
                              className="rounded-md border bg-muted/40 p-2"
                            >
                              <div className="flex items-center justify-between text-xs">
                                <span className="font-medium">{toolCall.name}</span>
                                <span
                                  className={`text-[10px] uppercase tracking-wide ${toolCall.status === "error"
                                    ? "text-destructive"
                                    : toolCall.status === "result"
                                      ? "text-emerald-600"
                                      : "text-muted-foreground"
                                    }`}
                                >
                                  {toolCall.status}
                                </span>
                              </div>
                              {toolCall.args !== undefined && (
                                <div className="mt-1">
                                  <span className="font-medium">Args:</span>
                                  <pre className="whitespace-pre-wrap text-[11px]">
                                    {formatPayload(toolCall.args)}
                                  </pre>
                                </div>
                              )}
                              {toolCall.result !== undefined && (
                                <div className="mt-1">
                                  <span className="font-medium">Result:</span>
                                  <pre className="whitespace-pre-wrap text-[11px]">
                                    {formatPayload(toolCall.result)}
                                  </pre>
                                </div>
                              )}
                              {toolCall.error && (
                                <p className="mt-1 text-[11px] text-destructive">Error: {toolCall.error}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

                  {/* Display assistant message options */}
                  {msg.role === "assistant" && msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <div className="space-y-2">
                        <span className="text-xs text-muted-foreground">Suggested options:</span>
                        <div className="flex flex-col gap-2">
                          {msg.suggestions.map((suggestion, index) => (
                            <Button
                              key={index}
                              variant="outline"
                              size="sm"
                              onClick={() => handleSuggestionClick(suggestion)}
                              className="text-xs h-8 justify-start"
                            >
                              {suggestion}
                            </Button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  <p
                    className="text-xs text-muted-foreground/80 mt-1.5 text-right"
                    suppressHydrationWarning={true}
                  >
                    {new Date(msg.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              ))}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      {showScrollToBottomButton && (
        <Button
          variant="outline"
          size="icon"
          onClick={scrollToBottom}
          className="fixed bottom-20 right-6 z-50 rounded-full shadow-lg bg-background hover:bg-muted"
          aria-label="Scroll to bottom"
        >
          <ArrowDown className="h-5 w-5" />
        </Button>
      )}
      {gameOver ? (
        <div className="p-3 border-t bg-background flex flex-col items-center justify-center space-y-2">
          <Alert className="w-full max-w-md">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Game over</AlertTitle>
            <AlertDescription>{gameOverMessage}</AlertDescription>
          </Alert>
          <p className="text-sm text-muted-foreground">Chat input has been disabled. Messages cannot be sent anymore.</p>
        </div>
      ) : (
        <div className="p-3 border-t bg-background flex items-center">
          <Input
            type="text"
            placeholder="Type your message..."
            className="flex-1 focus-visible:ring-1 focus-visible:ring-ring"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (inputValue.trim() && !isSending) {
                  handleSend();
                }
              }
            }}
            disabled={isSending || !sessionId}
          />
          <Button
            size="icon"
            className="ml-2"
            onClick={() => {
              if (inputValue.trim() && !isSending) {
                handleSend();
              }
            }}
            disabled={isSending || !inputValue.trim() || !sessionId}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      )}
    </>
  );
}
