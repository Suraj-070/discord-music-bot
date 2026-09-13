"use client"
import { useMusicStore } from "@/store/musicStore"

const Btn = ({ onClick, children, active = false, danger = false, size = "md" }: {
  onClick: () => void
  children: React.ReactNode
  active?: boolean
  danger?: boolean
  size?: "sm" | "md" | "lg"
}) => {
  const sz = size === "lg" ? "52px" : size === "sm" ? "36px" : "44px"
  const fs = size === "lg" ? "22px" : size === "sm" ? "14px" : "18px"
  return (
    <button
      onClick={onClick}
      style={{
        width: sz, height: sz, borderRadius: "50%", border: "none",
        background: active ? "var(--accent)" : danger ? "rgba(239,68,68,0.12)" : "var(--bg-hover)",
        color: active ? "white" : danger ? "#ef4444" : "var(--text)",
        fontSize: fs, cursor: "pointer", display: "flex",
        alignItems: "center", justifyContent: "center",
        transition: "all 0.15s", flexShrink: 0,
        boxShadow: active ? "0 0 16px var(--accent-glow)" : "none",
      }}
      onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "var(--border)" }}
      onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = danger ? "rgba(239,68,68,0.12)" : "var(--bg-hover)" }}
    >
      {children}
    </button>
  )
}

export function Controls({ emit }: { emit: (e: string, d?: object) => void }) {
  const { paused, loop, loop_queue, volume, setVolume } = useMusicStore()

  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border)",
      borderRadius: "16px",
      padding: "20px 24px",
      marginTop: "12px",
    }}>
      {/* Main controls */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "12px", marginBottom: "20px" }}>
        <Btn onClick={() => emit("prev")} size="sm">⏮</Btn>
        <Btn onClick={() => emit(paused ? "resume" : "pause")} size="lg" active={!paused}>
          {paused ? "▶" : "⏸"}
        </Btn>
        <Btn onClick={() => emit("next")} size="sm">⏭</Btn>
      </div>

      {/* Secondary controls + volume */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <Btn onClick={() => emit("toggle_loop")} active={loop} size="sm">🔂</Btn>
        <Btn onClick={() => emit("toggle_loop_queue")} active={loop_queue} size="sm">🔁</Btn>
        <Btn onClick={() => emit("shuffle")} size="sm">🔀</Btn>
        <Btn onClick={() => emit("stop")} danger size="sm">⏹</Btn>

        {/* Volume */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>
            {volume < 20 ? "🔇" : volume < 60 ? "🔉" : "🔊"}
          </span>
          <input
            type="range"
            min={0}
            max={100}
            value={volume}
            onChange={e => {
              const v = Number(e.target.value)
              setVolume(v)
              emit("volume", { volume: v / 100 })
            }}
            style={{
              width: "90px",
              accentColor: "var(--accent)",
              cursor: "pointer",
            }}
          />
          <span style={{ fontSize: "12px", color: "var(--text-muted)", minWidth: "30px" }}>
            {volume}%
          </span>
        </div>
      </div>
    </div>
  )
}
