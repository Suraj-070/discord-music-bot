"use client"
import { useMusicStore } from "@/store/musicStore"
import { fmtDuration } from "@/lib/utils"

export function Queue({ emit }: { emit: (e: string, d?: object) => void }) {
  const { queue } = useMusicStore()

  if (!queue.length) {
    return (
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border)",
        borderRadius: "16px", padding: "48px", textAlign: "center",
        color: "var(--text-muted)",
      }}>
        <div style={{ fontSize: "36px", marginBottom: "10px" }}>📋</div>
        <p style={{ fontSize: "14px" }}>Queue is empty</p>
      </div>
    )
  }

  return (
    <div style={{
      background: "var(--bg-card)", border: "1px solid var(--border)",
      borderRadius: "16px", overflow: "hidden",
    }}>
      {queue.map((song, i) => (
        <div
          key={i}
          style={{
            display: "flex", alignItems: "center", gap: "14px",
            padding: "12px 16px",
            borderBottom: i < queue.length - 1 ? "1px solid var(--border)" : "none",
            transition: "background 0.1s",
          }}
          onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"}
          onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
        >
          <span style={{ fontSize: "12px", color: "var(--text-dim)", minWidth: "20px", textAlign: "center" }}>
            {i + 1}
          </span>

          {song.thumbnail ? (
            <img src={song.thumbnail} alt="" style={{ width: "40px", height: "40px", borderRadius: "6px", objectFit: "cover" }} />
          ) : (
            <div style={{
              width: "40px", height: "40px", borderRadius: "6px",
              background: "var(--accent-soft)", display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: "16px",
            }}>🎵</div>
          )}

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{
              fontSize: "14px", fontWeight: "500", color: "var(--text)",
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            }}>
              {song.title}
            </p>
            <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>{song.uploader}</p>
          </div>

          <span style={{ fontSize: "12px", color: "var(--text-muted)", flexShrink: 0 }}>
            {fmtDuration(song.duration)}
          </span>

          <button
            onClick={() => emit("remove_from_queue", { index: i })}
            style={{
              background: "none", border: "none", color: "var(--text-dim)",
              cursor: "pointer", fontSize: "16px", padding: "4px",
              lineHeight: 1, borderRadius: "4px",
            }}
            onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "#ef4444"}
            onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "var(--text-dim)"}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
