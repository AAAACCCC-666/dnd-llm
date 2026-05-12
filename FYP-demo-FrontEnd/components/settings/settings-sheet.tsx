"use client"

import * as React from "react"
import { Settings2, Loader2, AlertTriangle, Eye, EyeOff } from "lucide-react"
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { buildApiUrl } from "@/lib/api"
import { cn } from "@/lib/utils"

type SettingsPayload = {
  OPENAI_API_KEY: string | null
  OPENAI_BASE_URL: string | null
  OPENAI_MODEL: string | null
  RAG_EMBEDDING_API_KEY: string | null
  RAG_EMBEDDING_BASE_URL: string | null
  RAG_EMBEDDING_MODEL: string | null
  SUGGEST_OPTIONS_MODEL: string | null
}

type SettingsSheetProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const FIELD_META: Array<{
  key: keyof SettingsPayload
  label: string
  placeholder?: string
  type?: "text" | "password"
  hint?: string
}> = [
  {
    key: "OPENAI_API_KEY",
    label: "OpenAI API Key",
    placeholder: "sk-...",
    type: "password",
    hint: "Stored in DB only; leave blank to clear",
  },
  {
    key: "OPENAI_BASE_URL",
    label: "OpenAI Base URL",
    placeholder: "https://api.openai.com/v1",
    hint: "Supports OpenAI, DeepSeek, One-API style gateways",
  },
  {
    key: "OPENAI_MODEL",
    label: "OpenAI Model",
    placeholder: "gpt-4o-mini",
  },
  {
    key: "RAG_EMBEDDING_API_KEY",
    label: "Embedding API Key",
    placeholder: "sk-embed...",
    type: "password",
    hint: "Optional; leave blank to clear",
  },
  {
    key: "RAG_EMBEDDING_BASE_URL",
    label: "Embedding Base URL",
    placeholder: "https://api.openai.com/v1",
  },
  {
    key: "RAG_EMBEDDING_MODEL",
  label: "Embedding Model",
    placeholder: "text-embedding-3-large",
  },
  {
    key: "SUGGEST_OPTIONS_MODEL",
  label: "Suggestion Model",
    placeholder: "gpt-4o-mini",
  },
]

export function SettingsSheet({ open, onOpenChange }: SettingsSheetProps) {
  const [settings, setSettings] = React.useState<SettingsPayload | null>(null)
  const [initialSettings, setInitialSettings] = React.useState<SettingsPayload | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [success, setSuccess] = React.useState<string | null>(null)
  const [revealed, setRevealed] = React.useState<Record<keyof SettingsPayload, boolean>>({
    OPENAI_API_KEY: false,
    OPENAI_BASE_URL: false,
    OPENAI_MODEL: false,
    RAG_EMBEDDING_API_KEY: false,
    RAG_EMBEDDING_BASE_URL: false,
    RAG_EMBEDDING_MODEL: false,
    SUGGEST_OPTIONS_MODEL: false,
  })

  const fetchSettings = React.useCallback(async () => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const res = await fetch(buildApiUrl("/settings"))
      if (!res.ok) {
        const detail = await res.text().catch(() => res.statusText)
        throw new Error(`Load failed: ${res.status} ${res.statusText} ${detail}`)
      }
      const data = await res.json()
      setSettings(data)
      setInitialSettings(data)
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error while fetching settings"
      setError(msg)
      console.error("Fetch settings error:", err)
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    if (open) {
      fetchSettings()
    }
  }, [open, fetchSettings])

  const handleChange = (key: keyof SettingsPayload, value: string) => {
    setSettings((prev) => {
      if (!prev) return prev
      return { ...prev, [key]: value }
    })
  }

  const handleReset = () => {
    if (initialSettings) {
      setSettings(initialSettings)
      setSuccess(null)
      setError(null)
    }
  }

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    const payload: Partial<SettingsPayload> = {}
    Object.entries(settings).forEach(([k, v]) => {
      const typedKey = k as keyof SettingsPayload
      // 空字符串视为清空
      payload[typedKey] = v === "" ? null : v
    })
    try {
      const res = await fetch(buildApiUrl("/settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const detail = await res.text().catch(() => res.statusText)
        throw new Error(`Save failed: ${res.status} ${res.statusText} ${detail}`)
      }
      const data = await res.json()
      setSettings(data)
      setInitialSettings(data)
      setSuccess("Saved and refreshed settings")
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error while saving"
      setError(msg)
      console.error("Save settings error:", err)
    } finally {
      setSaving(false)
    }
  }

  const isDirty = React.useMemo(() => {
    if (!settings || !initialSettings) return false
    return Object.keys(settings).some((key) => settings[key as keyof SettingsPayload] !== initialSettings[key as keyof SettingsPayload])
  }, [settings, initialSettings])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-lg">
        <SheetHeader className="pb-0">
          <SheetTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Settings
          </SheetTitle>
          <SheetDescription>Manage runtime config. Empty value will be saved as null.</SheetDescription>
        </SheetHeader>
        <ScrollArea className="flex-1 px-4">
          <div className="space-y-5 py-4">
            {error && (
              <div className="flex items-start gap-2 rounded-md border border-amber-400/60 bg-amber-100/40 px-3 py-2 text-sm text-amber-700 dark:border-amber-300/50 dark:bg-amber-900/40 dark:text-amber-50">
                <AlertTriangle className="mt-0.5 h-4 w-4" />
                <div>
                  <p className="font-medium">Something went wrong</p>
                  <p className="text-xs leading-relaxed">{error}</p>
                </div>
              </div>
            )}

            {success && (
              <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-400/10 dark:text-emerald-50">
                {success}
              </div>
            )}

            <div className="space-y-4">
              {FIELD_META.map(({ key, label, placeholder, type = "text", hint }) => {
                const isSecret = type === "password"
                return (
                  <div key={key} className="space-y-2">
                    <Label htmlFor={key}>{label}</Label>
                    <div className="relative">
                      <Input
                        id={key}
                        type={isSecret && !revealed[key] ? "password" : "text"}
                        placeholder={placeholder}
                        value={settings?.[key] ?? ""}
                        onChange={(e) => handleChange(key, e.target.value)}
                        autoComplete="off"
                        className={cn(isSecret ? "pr-10" : "")}
                      />
                      {isSecret ? (
                        <button
                          type="button"
                          onClick={() => setRevealed((prev) => ({ ...prev, [key]: !prev[key] }))}
                          className="text-muted-foreground hover:text-foreground absolute inset-y-0 right-2 flex items-center"
                          aria-label={revealed[key] ? "Hide secret value" : "Reveal secret value"}
                        >
                          {revealed[key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      ) : null}
                    </div>
                    {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
                  </div>
                )
              })}
            </div>
          </div>
        </ScrollArea>
        <Separator />
        <SheetFooter className="flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
          <div className="flex-1 text-xs text-muted-foreground">
            Saving calls `/api/settings`; untouched fields stay the same, empty strings become null.
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={handleReset} disabled={!isDirty || saving || loading}>
              Reset
            </Button>
            <Button onClick={handleSave} disabled={saving || loading || !settings} className="min-w-[96px]">
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
