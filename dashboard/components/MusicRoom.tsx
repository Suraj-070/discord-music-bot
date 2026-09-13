"use client"
import { useEffect, useState } from "react"
import { useMusicStore } from "@/store/musicStore"
import { useSocket } from "@/hooks/useSocket"
import { NowPlaying } from "./NowPlaying"
import { Controls } from "./Controls"
import { Queue } from "./Queue"
import { AddSong } from "./AddSong"

export function MusicRoom() {
  const { guildId, guildName, guildIcon, setGuild, current, queue } = useMusicStore()
  const { emit } = useSocket(guildId)
  const [tab, setTab] = useState<"queue" | "add">("queue")

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <header style={{
        padding: "16px 24px",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        gap: "12px",
        background: "var(--bg-card)",
      }}>
        <button
          onClick={() => setGuild("", "", "")}
          style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "20px", lineHeight: 1, padding: "4px" }}
        >
          ‹
        </button>
        {guildIcon && <img src={guildIcon} alt="" style={{ width: "28px", height: "28px", borderRadius: "50%" }} />}
        <span style={{ fontWeight: "600", color: "var(--text)", fontSize: "15px" }}>{guildName}</span>
        <div style={{
          marginLeft: "auto",
          fontSize: "12px",
          color: "var(--accent)",
          background: "var(--accent-soft)",
          padding: "4px 10px",
          borderRadius: "20px",
          fontWeight: "500",
        }}>
          {current ? "● Live" : "Idle"}
        </div>
      </header>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", maxWidth: "900px", margin: "0 auto", width: "100%", padding: "24px" }}>
        {/* Now Playing + Controls */}
        <NowPlaying emit={emit} />
        <Controls emit={emit} />

        {/* Tabs */}
        <div style={{ display: "flex", gap: "4px", marginTop: "32px", marginBottom: "16px", background: "var(--bg-card)", padding: "4px", borderRadius: "10px", width: "fit-content" }}>
          {(["queue", "add"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: "8px 20px",
                borderRadius: "7px",
                border: "none",
                cursor: "pointer",
                fontWeight: "500",
                fontSize: "14px",
                background: tab === t ? "var(--accent)" : "transparent",
                color: tab === t ? "white" : "var(--text-muted)",
                transition: "all 0.15s",
              }}
            >
              {t === "queue" ? `Queue (${queue.length})` : "Add Song"}
            </button>
          ))}
        </div>

        {tab === "queue" ? <Queue emit={emit} /> : <AddSong emit={emit} onAdded={() => setTab("queue")} />}
      </div>
    </div>
  )
}
