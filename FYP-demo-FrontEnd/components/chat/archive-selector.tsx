"use client"

import * as React from "react"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Archive, MoreHorizontal, Trash2 } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { buildApiUrl } from "@/lib/api"

interface Session {
  id: string
  name: string | null
  created_at: string
}

interface ArchiveItem {
  session_id: string
  name: string
  url: string
  emoji: string
}

export function ArchiveSelector() {
  const [sessions, setSessions] = useState<ArchiveItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const router = useRouter()

  useEffect(() => {
    const fetchSessions = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const response = await fetch(buildApiUrl("/sessions"))
        if (!response.ok) {
          throw new Error(`Failed to fetch sessions: ${response.statusText}`)
        }
        const data: Session[] = await response.json()
        const formattedSessions: ArchiveItem[] = data.map((session) => ({
          session_id: session.id,
          name: session.name || `Session ${session.id.substring(0, 8)}`,
          url: `/chat/${session.id}`,
          emoji: "💬",
        }))
        setSessions(formattedSessions)
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message)
        } else {
          setError("An unknown error occurred")
        }
        console.error("Error fetching sessions:", err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchSessions()
  }, [])

  const handleSessionSelect = (sessionId: string) => {
    setIsOpen(false)
    router.push(`/chat/${sessionId}`)
  }

  const handleDeleteSession = async (sessionId: string) => {
    try {
      const response = await fetch(buildApiUrl(`/sessions/${sessionId}`), {
        method: "DELETE",
      })

      if (!response.ok) {
        throw new Error(`Failed to delete session: ${response.statusText}`)
      }

      // Remove the session from the list
      setSessions(prev => prev.filter(session => session.session_id !== sessionId))
    } catch (err) {
      console.error("Error deleting session:", err)
      alert("Failed to delete session. Please try again.")
    }
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="flex items-center gap-2"
        >
          <Archive className="h-4 w-4" />
          <span>Archive</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex flex-col">
          <div className="p-4 border-b">
            <h3 className="font-semibold text-sm">Select Archive</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Select an archive to continue the game
            </p>
          </div>

          <ScrollArea className="h-64">
            {isLoading && (
              <div className="p-4 text-center text-sm text-muted-foreground">
                Loading...
              </div>
            )}

            {error && (
              <div className="p-4 text-center text-sm text-destructive">
                Error: {error}
              </div>
            )}

            {!isLoading && !error && sessions.length === 0 && (
              <div className="p-4 text-center text-sm text-muted-foreground">
                No archives available
              </div>
            )}

            {!isLoading && !error && sessions.length > 0 && (
              <div className="p-2">
                {sessions.map((item) => (
                  <div
                    key={item.session_id}
                    className="group relative flex items-center gap-3 rounded-md p-2 text-sm hover:bg-accent hover:text-accent-foreground cursor-pointer"
                    onClick={() => handleSessionSelect(item.session_id)}
                  >
                    <span className="text-base">{item.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{item.name}</div>
                      <div className="text-xs text-muted-foreground truncate">
                        ID: {item.session_id.substring(0, 8)}...
                      </div>
                    </div>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 opacity-0 group-hover:opacity-100"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="h-3 w-3" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteSession(item.session_id)
                          }}
                          className="text-destructive"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete Archive
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      </PopoverContent>
    </Popover>
  )
}
