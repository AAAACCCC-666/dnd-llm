"use client"

import * as React from "react"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { buildApiUrl } from "@/lib/api"
import { Plus } from "lucide-react"

export function NewAdventureButton() {
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleStartAdventure = async () => {
    setIsLoading(true)
    try {
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
      const session = await response.json()
      router.push(`/chat/${session.id}`)
    } catch (error) {
      console.error("Error starting new adventure:", error)
      // Here you can add user-friendly error prompts, such as using toast
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleStartAdventure}
      disabled={isLoading}
      className="flex items-center gap-2"
    >
      <Plus className="h-4 w-4" />
      {isLoading ? "Creating..." : "New Adventure"}
    </Button>
  )
}
