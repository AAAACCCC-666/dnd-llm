const API_PATH_PREFIX = "/api"

let cachedBrowserOrigin: string | null = null

function resolveBrowserOrigin(): string | null {
  if (cachedBrowserOrigin) return cachedBrowserOrigin

  if (typeof window === "undefined") {
    return null
  }

  const { protocol, host } = window.location
  if (!protocol || !host) {
    return null
  }

  cachedBrowserOrigin = `${protocol}//${host}`.replace(/\/+$/, "")
  return cachedBrowserOrigin
}

function resolveApiBase() {
  const browserOrigin = resolveBrowserOrigin()
  const base = browserOrigin ? `${browserOrigin}${API_PATH_PREFIX}` : API_PATH_PREFIX
  return base.replace(/\/+$/, "") || API_PATH_PREFIX
}

export function buildApiUrl(path: string) {
  const trimmed = path.trim()
  const apiBase = resolveApiBase()
  if (!trimmed) return apiBase

  const [withoutFragment, fragment = ""] = trimmed.split("#", 2)
  const [rawPathname, search = ""] = withoutFragment.split("?", 2)

  const withLeadingSlash = rawPathname.startsWith("/")
    ? rawPathname
    : `/${rawPathname}`
  const collapsed = withLeadingSlash.replace(/\/{2,}/g, "/")
  const pathnameOnly = collapsed === "/" ? "/" : collapsed.replace(/\/+$/, "")
  const normalizedPathname = pathnameOnly === "/" ? "" : pathnameOnly

  const query = search ? `?${search}` : ""
  const hash = fragment ? `#${fragment}` : ""

  const finalUrl = `${apiBase}${normalizedPathname}${query}${hash}`

  // 在开发环境中打印所访问的后端url
  if (process.env.NODE_ENV === "development") {
    console.log(`API Request URL: ${finalUrl}`)
  }

  return finalUrl
}
