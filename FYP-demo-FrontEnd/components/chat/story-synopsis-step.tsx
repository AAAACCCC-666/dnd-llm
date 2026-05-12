"use client"

import * as React from "react"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Loader2, AlertCircle, RefreshCw, Check } from "lucide-react"
import { buildApiUrl } from "@/lib/api"

interface StorySynopsisStepProps {
  storyId: string
  sessionId: string
  onConfirm: () => void | Promise<void>
}

interface StoryDetailResponse {
  story?: {
    id: number | string
    title?: string
    theme?: string
  } | null
  synopsis?: {
    id: number
    story_id: number
    outline_version: number
    content: string
    is_active: boolean
    created_at: string
  } | null
}

interface SynopsisStreamDonePayload {
  synopsis_id?: number
  outline_version?: number
}

interface FeedbackStreamDonePayload {
  feedback_id?: number
  outline_version?: number
  synopsis_id?: number
}

type SynopsisStepStatus = "initial_loading" | "generating" | "ready" | "updating" | "error"

export function StorySynopsisStep({
  storyId,
  sessionId,
  onConfirm,
}: StorySynopsisStepProps) {
  const [status, setStatus] = useState<SynopsisStepStatus>("initial_loading")
  const [synopsisText, setSynopsisText] = useState("")
  const [storyTitle, setStoryTitle] = useState<string | undefined>(undefined)
  const [storyTheme, setStoryTheme] = useState<string | undefined>(undefined)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [feedbackText, setFeedbackText] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const [lastSynopsisMeta, setLastSynopsisMeta] =
    useState<SynopsisStreamDonePayload | FeedbackStreamDonePayload | null>(
      null,
    )

  useEffect(() => {
    let cancelled = false

    const startInitialLoad = async () => {
      if (!storyId) return
      setStatus("initial_loading")
      setErrorMessage(null)

      try {
        const response = await fetch(buildApiUrl(`/stories/${storyId}`))
        if (!response.ok) {
          const errorText = await response
            .text()
            .catch(() => "Failed to read error body")
          throw new Error(
            `Failed to load story: ${response.status} ${response.statusText}. ${errorText}`,
          )
        }

        const data: StoryDetailResponse = await response.json()
        if (cancelled) return

        if (data.story) {
          setStoryTitle(data.story.title)
          setStoryTheme(data.story.theme)
        }

        if (data.synopsis && data.synopsis.content) {
          setSynopsisText(data.synopsis.content)
          setStatus("ready")
        } else {
          await startSynopsisStream()
        }
      } catch (err) {
        if (cancelled) return
        const message =
          err instanceof Error ? err.message : "Unknown error loading story."
        setErrorMessage(message)
        setStatus("error")
      }
    }

    startInitialLoad()

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyId])

  const parseSseStream = async <TDonePayload,>(
    response: Response,
    onDelta: (delta: string) => void,
    onDone: (payload: TDonePayload | null) => void,
  ) => {
    if (!response.body) {
      throw new Error("No response body for SSE stream.")
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let donePayload: TDonePayload | null = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      let eolIndex: number
      while ((eolIndex = buffer.indexOf("\n\n")) >= 0) {
        const eventString = buffer.substring(0, eolIndex)
        buffer = buffer.substring(eolIndex + 2)


        if (!eventString.startsWith("data: ")) continue
        const jsonData = eventString.substring("data: ".length)
        try {
          const parsed = JSON.parse(jsonData) as {
            event?: string
            text?: string
            message?: string
          } & TDonePayload
          if (process.env.NODE_ENV !== "production") {
            console.debug("[StorySynopsisStep] SSE event parsed", parsed)
          }

          if (parsed.event === "delta" && typeof parsed.text === "string") {
            onDelta(parsed.text)
          } else if (parsed.event === "error") {
            throw new Error(parsed.message || "Synopsis stream error")
          } else if (parsed.event === "done") {
            donePayload = parsed
          }
        } catch (err) {
          if (process.env.NODE_ENV !== "production") {
            console.error("[StorySynopsisStep] SSE parse error", err)
          }
          const errorMsg =
            err instanceof Error ? err.message : "Error parsing SSE event."
          throw new Error(errorMsg)
        }
      }
    }

    onDone(donePayload)
  }

  const startSynopsisStream = async () => {
    if (!storyId) return

    setStatus("generating")
    setErrorMessage(null)
    setIsStreaming(true)
    setSynopsisText("")
    setLastSynopsisMeta(null)

    try {
      const url = buildApiUrl(`/stories/${storyId}/synopsis?stream=true`)
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      })

      if (!response.ok) {
        const errorText = await response
          .text()
          .catch(() => "Failed to read error body.")
        throw new Error(
          `Failed to generate synopsis: ${response.status} ${response.statusText}. ${errorText}`,
        )
      }

      await parseSseStream<SynopsisStreamDonePayload>(
        response,
        (delta) => {
          setSynopsisText((prev) => prev + delta)
        },
        (payload) => {
          setLastSynopsisMeta(payload ?? null)
        },
      )

      setStatus("ready")
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unknown error generating synopsis."
      setErrorMessage(message)
      setStatus("error")
    } finally {
      setIsStreaming(false)
    }
  }

  const startFeedbackStream = async (type: "ModifyExisting" | "CreateNew") => {
    if (!storyId) return
    if (!feedbackText.trim()) {
      setErrorMessage("Please enter your feedback on the storyline first.")
      return
    }

    setErrorMessage(null)
    setIsStreaming(true)
    setStatus("updating")
    setSynopsisText("")
    setLastSynopsisMeta(null)

    try {
      const url = buildApiUrl(`/stories/${storyId}/feedback?stream=true`)
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback_text: feedbackText.trim(),
          type,
        }),
      })

      if (!response.ok) {
        const errorText = await response
          .text()
          .catch(() => "Failed to read error body.")
        throw new Error(
          `Failed to update synopsis: ${response.status} ${response.statusText}. ${errorText}`,
        )
      }

      await parseSseStream<FeedbackStreamDonePayload>(
        response,
        (delta) => {
          setSynopsisText((prev) => prev + delta)
        },
        (payload) => {
          setLastSynopsisMeta(payload ?? null)
        },
      )

      setStatus("ready")
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unknown error updating synopsis."
      setErrorMessage(message)
      setStatus("error")
    } finally {
      setIsStreaming(false)
    }
  }

  const handleRegenerate = async () => {
    setFeedbackText("")
    await startSynopsisStream()
  }

  const handleUpdateWithFeedback = async () => {
    await startFeedbackStream("ModifyExisting")
  }

  const handleRecreateWithFeedback = async () => {
    await startFeedbackStream("CreateNew")
  }

  const isReadyForConfirm = status === "ready" && !!synopsisText.trim()

  return (
    <div className="h-full flex flex-col">
      <div className="flex-none border-b px-6 py-4 flex items-center justify-between bg-background/80">
        <div>
          <h2 className="text-lg font-semibold">
            Story Synopsis Confirmation
            {storyTitle ? `: ${storyTitle}` : ""}
          </h2>
          {storyTheme && (
            <p className="text-sm text-muted-foreground mt-1">
              Theme: {storyTheme}
            </p>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            Current Session: {sessionId}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRegenerate}
            disabled={isStreaming}
            className="flex items-center gap-1"
          >
            <RefreshCw className="h-4 w-4" />
            Regenerate Synopsis
          </Button>
          <Button
            size="sm"
            onClick={() => {
              void onConfirm()
            }}
            disabled={!isReadyForConfirm || isStreaming}
            className="flex items-center gap-1"
          >
            <Check className="h-4 w-4" />
            Start Game
          </Button>
        </div>
      </div>

      <div className="flex-1 grid grid-rows-2 gap-4 p-6 overflow-hidden">
        <div className="relative border rounded-md p-4 bg-muted/40 overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium">Auto-generated Story Synopsis</h3>
            {isStreaming && (
              <div className="flex items-center text-xs text-muted-foreground gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Generating...
              </div>
            )}
          </div>
          <div className="absolute inset-x-4 bottom-2 text-[10px] text-muted-foreground">
            {lastSynopsisMeta &&
              ("outline_version" in lastSynopsisMeta ||
                "synopsis_id" in lastSynopsisMeta) && (
                <span>
                  outline v{(lastSynopsisMeta as any).outline_version ?? "-"} ·
                  synopsis #{(lastSynopsisMeta as any).synopsis_id ?? "-"}
                </span>
              )}
          </div>
          <div className="mt-2 h-full overflow-y-auto pr-2 text-sm whitespace-pre-wrap">
            {status === "initial_loading" && (
              <div className="flex items-center text-muted-foreground text-sm">
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Loading story and synopsis...
              </div>
            )}
            {synopsisText && status !== "initial_loading" && (
              <p>{synopsisText}</p>
            )}
            {!synopsisText &&
              status !== "initial_loading" &&
              !isStreaming &&
              !errorMessage && (
                <p className="text-muted-foreground text-sm">
                  No synopsis available. Click "Regenerate Synopsis" to start generating.
                </p>
              )}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">If not satisfied, you can provide feedback to the DM</h3>
          </div>
          <Textarea
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="Example: Hope the story is darker overall; or change the ending to a tragedy; or add some light-hearted humorous scenes..."
            className="flex-1 resize-none"
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleUpdateWithFeedback}
              disabled={isStreaming || !feedbackText.trim()}
            >
              Fine-tune Synopsis Based on Feedback
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRecreateWithFeedback}
              disabled={isStreaming || !feedbackText.trim()}
            >
              Regenerate Based on Feedback
            </Button>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="px-6 pb-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Story Synopsis Generation Error</AlertTitle>
            <AlertDescription className="text-sm">
              {errorMessage}
            </AlertDescription>
          </Alert>
        </div>
      )}
    </div>
  )
}
