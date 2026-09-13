"use client"
import { useEffect, useRef } from "react"
import { io, Socket } from "socket.io-client"
import { useMusicStore } from "@/store/musicStore"

export function useSocket(guildId: string | null) {
  const socketRef = useRef<Socket | null>(null)
  const store = useMusicStore()

  useEffect(() => {
    if (!guildId) return

    // Points directly to the Python bot on Render
    const BOT_URL = process.env.NEXT_PUBLIC_BOT_URL || "http://localhost:8080"
    const socket = io(BOT_URL, { query: { guildId } })
    socketRef.current = socket

    socket.on("connect", () => {
      socket.emit("join_guild", { guildId })
    })

    socket.on("full_state", (data) => {
      store.setCurrent(data.current)
      store.setQueue(data.queue || [])
      store.setPaused(data.paused)
      store.setLoop(data.loop)
      store.setLoopQueue(data.loop_queue)
      store.setVolume(Math.round(data.volume * 100))
      store.setElapsed(data.elapsed || 0)
    })

    socket.on("now_playing", (data) => {
      store.setCurrent(data.song)
      store.setPaused(data.paused || false)
      store.setElapsed(0)
    })

    socket.on("queue_update", (data) => store.setQueue(data.queue || []))
    socket.on("paused", () => store.setPaused(true))
    socket.on("resumed", () => store.setPaused(false))
    socket.on("stopped", () => {
      store.setCurrent(null)
      store.setQueue([])
      store.setPaused(false)
    })
    socket.on("volume_update", (data) => store.setVolume(Math.round(data.volume * 100)))
    socket.on("loop_update", (data) => {
      store.setLoop(data.loop)
      store.setLoopQueue(data.loop_queue)
    })
    socket.on("elapsed", (data) => store.setElapsed(data.elapsed))

    return () => { socket.disconnect() }
  }, [guildId])

  const emit = (event: string, data?: object) => {
    socketRef.current?.emit(event, { guildId, ...data })
  }

  return { emit }
}
