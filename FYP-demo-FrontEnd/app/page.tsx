"use client"

import { BeginScreen } from "@/components/begin-screen"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { buildApiUrl } from "@/lib/api"

interface SessionSummary {
  id: string
  created_at: string
}

export default function Page() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)

  const handleBegin = async () => {
    setIsLoading(true)
    try {
      // First try to get existing sessions
      const sessionsResponse = await fetch(buildApiUrl("/sessions"))
      if (sessionsResponse.ok) {
        const sessions: SessionSummary[] = await sessionsResponse.json()
        // If there are existing sessions, jump to the latest session
        if (sessions && sessions.length > 0) {
          // Sort by creation time to get the latest session
          const sortedSessions = [...sessions].sort((a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )
          const latestSession = sortedSessions[0]
          router.push(`/chat/${latestSession.id}`)
          return
        }
      }

      // If no existing sessions, create a new session
      const response = await fetch(buildApiUrl("/sessions"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: "New Adventure" }),
      })
      if (!response.ok) {
        throw new Error("Failed to create session")
      }
      const session: SessionSummary = await response.json()
      router.push(`/chat/${session.id}`)
    } catch (error) {
      console.error("Error starting adventure:", error)
      // Here you can add user-friendly error prompts, such as using toast
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <BeginScreen onBegin={handleBegin} isLoading={isLoading} />
  )
}
