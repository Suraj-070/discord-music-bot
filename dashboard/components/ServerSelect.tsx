"use client"
import { useEffect, useState } from "react"
import { useMusicStore } from "@/store/musicStore"

interface Guild {
  id: string
  name: string
  icon: string | null
}

export function ServerSelect({ session }: { session: any }) {
  const [guilds, setGuilds] = useState<Guild[]>([])
  const [loading, setLoading] = useState(true)
  const { setGuild } = useMusicStore()

  useEffect(() => {
    fetch("https://discord.com/api/users/@me/guilds", {
      headers: { Authorization: `Bearer ${session.accessToken}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setGuilds(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [session])

  const guildIcon = (g: Guild) =>
    g.icon ? `https://cdn.discordapp.com/icons/${g.id}/${g.icon}.png` : null

  return (
    <div style={{ minHeight: "100vh", padding: "40px 24px" }}>
      <div style={{ maxWidth: "600px", margin: "0 auto" }}>
        <div style={{ marginBottom: "40px" }}>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "var(--text)", marginBottom: "6px" }}>
            🎵 Your Servers
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Pick a server to control music
          </p>
        </div>

        {loading ? (
          <div style={{ display: "flex", gap: "12px", flexDirection: "column" }}>
            {[1,2,3].map(i => (
              <div key={i} style={{ height: "72px", background: "var(--bg-card)", borderRadius: "12px", animation: "pulse 1.5s ease-in-out infinite" }} />
            ))}
            <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }`}</style>
          </div>
        ) : guilds.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px", color: "var(--text-muted)" }}>
            No servers found. Make sure the bot is added to your server.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {guilds.map((g) => (
              <button
                key={g.id}
                onClick={() => setGuild(g.id, g.name, guildIcon(g) || "")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "16px",
                  padding: "16px 20px",
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: "12px",
                  cursor: "pointer",
                  transition: "all 0.15s",
                  textAlign: "left",
                  width: "100%",
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"
                  ;(e.currentTarget as HTMLElement).style.borderColor = "var(--accent)"
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.background = "var(--bg-card)"
                  ;(e.currentTarget as HTMLElement).style.borderColor = "var(--border)"
                }}
              >
                {guildIcon(g) ? (
                  <img src={guildIcon(g)!} alt="" style={{ width: "40px", height: "40px", borderRadius: "50%", objectFit: "cover" }} />
                ) : (
                  <div style={{
                    width: "40px", height: "40px", borderRadius: "50%",
                    background: "var(--accent-soft)", display: "flex",
                    alignItems: "center", justifyContent: "center",
                    color: "var(--accent)", fontWeight: "700", fontSize: "14px"
                  }}>
                    {g.name[0]}
                  </div>
                )}
                <span style={{ color: "var(--text)", fontWeight: "500", fontSize: "15px" }}>{g.name}</span>
                <span style={{ marginLeft: "auto", color: "var(--text-dim)", fontSize: "18px" }}>›</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
