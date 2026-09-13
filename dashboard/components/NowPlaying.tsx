"use client"
import { useMusicStore } from "@/store/musicStore"
import { fmtDuration } from "@/lib/utils"
import { useEffect, useState } from "react"

export function NowPlaying({ emit }: { emit: (e: string, d?: object) => void }) {
  const { current, paused, elapsed } = useMusicStore()
  const [localElapsed, setLocalElapsed] = useState(0)

  useEffect(() => {
    setLocalElapsed(elapsed)
  }, [elapsed])

  useEffect(() => {
    if (!current || paused) return
    const t = setInterval(() => setLocalElapsed((p) => Math.min(p + 1, current.duration)), 1000)
    return () => clearInterval(t)
  }, [current, paused])

  const progress = current ? (localElapsed / current.duration) * 100 : 0

  if (!current) {
    return (
      <div style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "16px",
        padding: "40px",
        textAlign: "center",
        color: "var(--text-muted)",
      }}>
        <div style={{ fontSize: "48px", marginBottom: "12px" }}>🎵</div>
        <p style={{ fontSize: "15px" }}>Nothing playing right now</p>
        <p style={{ fontSize: "13px", marginTop: "6px", color: "var(--text-dim)" }}>Add a song to get started</p>
      </div>
    )
  }

  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border)",
      borderRadius: "16px",
      padding: "24px",
      display: "flex",
      gap: "24px",
      alignItems: "center",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Glow */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: "2px",
        background: "linear-gradient(90deg, var(--accent), var(--green))",
      }} />

      {/* Thumbnail */}
      {current.thumbnail ? (
        <img
          src={current.thumbnail}
          alt=""
          style={{ width: "88px", height: "88px", borderRadius: "10px", objectFit: "cover", flexShrink: 0 }}
        />
      ) : (
        <div style={{
          width: "88px", height: "88px", borderRadius: "10px",
          background: "var(--accent-soft)", display: "flex",
          alignItems: "center", justifyContent: "center", fontSize: "32px", flexShrink: 0
        }}>🎵</div>
      )}

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
          <span style={{
            fontSize: "10px", fontWeight: "600", letterSpacing: "0.08em",
            color: paused ? "var(--text-muted)" : "var(--green)",
            background: paused ? "transparent" : "var(--green-soft)",
            padding: "2px 8px", borderRadius: "20px",
          }}>
            {paused ? "PAUSED" : "▶ PLAYING"}
          </span>
        </div>

        <h2 style={{
          fontSize: "17px", fontWeight: "600", color: "var(--text)",
          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          marginBottom: "2px",
        }}>
          {current.title}
        </h2>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "14px" }}>
          {current.uploader}
        </p>

        {/* Progress */}
        <div>
          <div style={{
            height: "4px", background: "var(--border)", borderRadius: "2px", marginBottom: "6px",
            cursor: "pointer", position: "relative",
          }}>
            <div style={{
              height: "100%", width: `${progress}%`,
              background: "linear-gradient(90deg, var(--accent), var(--green))",
              borderRadius: "2px", transition: "width 1s linear",
            }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-muted)" }}>
            <span>{fmtDuration(localElapsed)}</span>
            <span>{fmtDuration(current.duration)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
