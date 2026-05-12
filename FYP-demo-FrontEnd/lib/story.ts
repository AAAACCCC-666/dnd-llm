import { buildApiUrl } from "@/lib/api"

const STORAGE_PREFIX = "session_story_id:"

export function saveStoryIdForSession(sessionId: string, storyId: number | string) {
  if (typeof window === "undefined") return
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${sessionId}`, String(storyId))
  } catch {
    // ignore storage errors
  }
}

export function getStoryIdForSession(sessionId: string): string | null {
  if (typeof window === "undefined") return null
  try {
    return localStorage.getItem(`${STORAGE_PREFIX}${sessionId}`)
  } catch {
    return null
  }
}

interface CreateStoryRequestBody {
  title: string
  theme?: string
  N: number
  style?: string
  created_by?: string
  session_id?: string
}

interface CreateStoryResponse {
  story_id?: number | string
  id?: number | string
}

export async function createStoryForSession(sessionId: string) {
  const body: CreateStoryRequestBody = {
    title: "New Adventure",
    theme: "",
    N: 5,
    style: "tabletop rpg",
    created_by: sessionId,
    session_id: sessionId,
  }

  const res = await fetch(buildApiUrl("/stories"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`Failed to create story: ${res.status} ${res.statusText} ${text}`)
  }

  const data: CreateStoryResponse = await res.json()
  const storyId = data.story_id ?? data.id
  if (!storyId) {
    throw new Error("Story API did not return story_id")
  }

  saveStoryIdForSession(sessionId, storyId)
  return String(storyId)
}
