"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Home } from "lucide-react"

export function HomeButton() {
  const router = useRouter()

  const handleHomeClick = () => {
    router.push("/")
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleHomeClick}
      className="flex items-center gap-2"
    >
      <Home className="h-4 w-4" />
      <span>Home</span>
    </Button>
  )
}