"use client"

import { Button } from "@/components/ui/button"

interface BeginScreenProps {
  onBegin: () => void
  isLoading?: boolean
}

export function BeginScreen({ onBegin, isLoading = false }: BeginScreenProps) {
  const handleBeginClick = () => {
    onBegin()
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-8 relative overflow-hidden">
      {/* Grid background */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-black to-gray-900">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:64px_64px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,black,transparent)]" />
      </div>
      
      {/* Scan line effect */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-500/10 to-transparent animate-pulse" />
      
      <div className="text-center space-y-16 relative z-10">
        {/* Title - Tech style */}
        <div className="space-y-4">
          <h1 className="text-6xl font-mono font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 tracking-wider">
            LLM_D&D
          </h1>
          <div className="w-48 h-1 bg-gradient-to-r from-cyan-400 to-blue-500 mx-auto rounded-full" />
        </div>

        {/* Start button - Tech style */}
        <Button
          onClick={handleBeginClick}
          disabled={isLoading}
          size="lg"
          className="bg-gradient-to-r from-cyan-600 to-blue-700 hover:from-cyan-500 hover:to-blue-600 text-white font-mono font-bold text-xl px-16 py-8 rounded-lg border border-cyan-400/30 shadow-lg shadow-cyan-500/20 transform transition-all duration-300 hover:scale-105 hover:shadow-cyan-500/40"
        >
          {isLoading ? (
            <div className="flex items-center space-x-3">
              <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-lg tracking-wider">INITIALIZING...</span>
            </div>
          ) : (
            <span className="text-2xl tracking-wider">BEGIN</span>
          )}
        </Button>
      </div>
    </div>
  )
}