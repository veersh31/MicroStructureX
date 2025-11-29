"use client"

import { Button } from "@/components/ui/button"
import { PlayIcon, PauseIcon } from "lucide-react"
import { useState } from "react"

export function ReplayControls({ isActive, onToggle }: { isActive: boolean; onToggle: () => void }) {
  const [isLoading, setIsLoading] = useState(false)

  const handleStart = async () => {
    setIsLoading(true)
    try {
      await fetch("http://localhost:8000/replay/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration_seconds: 120 }),
      })
      onToggle()
    } catch (error) {
      console.log("[v0] Failed to start replay:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStop = async () => {
    setIsLoading(true)
    try {
      await fetch("http://localhost:8000/replay/stop", { method: "POST" })
      onToggle()
    } catch (error) {
      console.log("[v0] Failed to stop replay:", error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      {!isActive ? (
        <Button onClick={handleStart} disabled={isLoading} size="lg" className="gap-2">
          <PlayIcon className="h-4 w-4" />
          Start Market Replay
        </Button>
      ) : (
        <Button onClick={handleStop} disabled={isLoading} variant="destructive" size="lg" className="gap-2">
          <PauseIcon className="h-4 w-4" />
          Stop Replay
        </Button>
      )}
    </div>
  )
}
