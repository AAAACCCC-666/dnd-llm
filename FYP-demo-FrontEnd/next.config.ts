import type { NextConfig } from "next"

const DEV_BACKEND_ORIGIN = (process.env.DEV_BACKEND_ORIGIN || "http://localhost:8080").replace(/\/+$/, "")

if (process.env.NODE_ENV === "development") {
  console.info(`[dev] 后端代理地址: ${DEV_BACKEND_ORIGIN}/api`)
}

const nextConfig: NextConfig = {
  compress: false, // 确保通过 rewrites 代理的 SSE 流不会被压缩，避免前端延迟
  output: "standalone",
  allowedDevOrigins: ['localhost', '192.168.20.51'],
  async rewrites() {
    if (process.env.NODE_ENV !== "development") {
      return []
    }

    return [
      {
        source: "/api/:path*",
        destination: `${DEV_BACKEND_ORIGIN}/api/:path*`,
      },
    ]
  },
  experimental: {
    proxyTimeout: 180000, // 增加代理超时时间到3分钟，支持长时间运行的RevisionAgent调用
  },
}

export default nextConfig
