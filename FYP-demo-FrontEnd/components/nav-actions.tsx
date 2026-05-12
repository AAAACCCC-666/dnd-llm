"use client"

import * as React from "react"
import {
  MoreHorizontal,
  Moon,
  Settings2,
  Sun,
  Trash2,
} from "lucide-react"
import { useParams, useRouter } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useTheme } from "./theme-provider"
import { buildApiUrl } from "@/lib/api"
import { SettingsSheet } from "@/components/settings/settings-sheet"


export function NavActions() {
  const [isOpen, setIsOpen] = React.useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false)
  const [isDeleting, setIsDeleting] = React.useState(false)
  const [showSettings, setShowSettings] = React.useState(false)
  const { theme, setTheme } = useTheme()
  const params = useParams()
  const router = useRouter()
  const sessionId = params?.session_id as string | undefined

  const handleSettingsClick = () => {
    setIsOpen(false)
    setShowSettings(true)
  }

  const handleThemeChange = (newTheme: "light" | "dark") => {
    setTheme(newTheme)
  }

  const handleDeleteSession = async () => {
    if (!sessionId) {
      alert("Unable to get session ID")
      return
    }

    setIsDeleting(true)
    try {
      const response = await fetch(buildApiUrl(`/sessions/${sessionId}`), {
        method: "DELETE",
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to delete session" }))
        throw new Error(errorData.detail || `Failed to delete session: ${response.statusText}`)
      }

      // Redirect to home page after successful deletion
      router.push('/')
    } catch (err) {
      const errMessage = err instanceof Error ? err.message : "Unknown error occurred while deleting session"
      alert(errMessage)
      console.error("Error deleting session:", err)
    } finally {
      setIsDeleting(false)
      setShowDeleteDialog(false)
    }
  }

  const handleDeleteClick = () => {
    setIsOpen(false)
    setShowDeleteDialog(true)
  }

  const getThemeIcon = (themeName: string) => {
    switch (themeName) {
      case "light": return <Sun className="h-4 w-4" />
      case "dark": return <Moon className="h-4 w-4" />
      default: return <Sun className="h-4 w-4" />
    }
  }

  return (
    <>
      <div className="flex items-center gap-2 text-sm">
        <Popover open={isOpen} onOpenChange={setIsOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
            className="data-[state=open]:bg-accent h-7 w-7"
          >
            <MoreHorizontal />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-56 overflow-hidden rounded-lg p-0"
          align="end"
        >
          <div className="bg-transparent">
            <div className="flex flex-col gap-0">
              {/* Settings Section */}
              <div className="border-b">
                <div className="gap-0">
                  <div className="flex flex-col gap-0">
                    <div className="relative">
                      <button
                        onClick={handleSettingsClick}
                        className="flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                      >
                        <Settings2 className="h-4 w-4" /> <span>Settings</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Delete Session Section */}
              <div className="border-b">
                <div className="gap-0">
                  <div className="flex flex-col gap-0">
                    <div className="relative">
                      <button
                        onClick={handleDeleteClick}
                        className="flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-950/50 dark:hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4" /> <span>Delete Session</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Theme Section */}
              <div>
                <div className="px-3 py-2 text-xs font-medium text-muted-foreground">
                  Theme
                </div>
                <div className="gap-0">
                  <div className="flex flex-col gap-0">
                    <div className="relative">
                      <button
                        onClick={() => handleThemeChange("light")}
                        className={`flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm hover:bg-accent hover:text-accent-foreground ${theme === "light" ? "bg-accent" : ""}`}
                      >
                        {getThemeIcon("light")} <span>Light</span>
                      </button>
                    </div>
                    <div className="relative">
                      <button
                        onClick={() => handleThemeChange("dark")}
                        className={`flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm hover:bg-accent hover:text-accent-foreground ${theme === "dark" ? "bg-accent" : ""}`}
                      >
                        {getThemeIcon("dark")} <span>Dark</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>

      {/* Delete Session Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Session</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove all chat history, characters, and inventory in this session. It cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteSession}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      </div>

      <SettingsSheet
        open={showSettings}
        onOpenChange={(next) => {
          setShowSettings(next)
          if (!next) setIsOpen(false)
        }}
      />
    </>
  )
}
