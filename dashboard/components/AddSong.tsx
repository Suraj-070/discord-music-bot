"use client"
import { useState } from "react"
import { fmtDuration } from "@/lib/utils"

interface SearchResult {
  title: string
  webpage_url: string
  duration: number
  thumbnail: string
  uploader: string
}

export function AddSong({ emit, onAdded }: { emit: (e: string, d?: object) => void; onAdded: () => void }) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [added, setAdded] = useState<string | null>(null)

  const search = async () => {
    if (!query.trim()) return
    setLoading(true)
    setResults([])
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
      const data = await res.json()
      setResults(data.results || [])
    } catch {
      // fallback: emit directly
      emit("add_song", { query })
      setAdded(query)
      setTimeout(() => { setAdded(null); onAdded() }, 1500)
    }
    setLoading(false)
  }

  const addSong = (url: string, title: string) => {
    emit("add_song", { query: url })
    setAdded(title)
    setResults([])
    setQuery("")
    setTimeout(() => { setAdded(null); onAdded() }, 1500)
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Input */}
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border)",
        borderRadius: "16px", padding: "20px",
      }}>
        <label style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "10px", display: "block" }}>
          Song name, YouTube URL, or playlist URL
        </label>
        <div style={{ display: "flex", gap: "10px" }}>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && search()}
            placeholder="e.g. Blinding Lights or https://youtube.com/..."
            style={{
              flex: 1, padding: "12px 16px",
              background: "var(--bg)", border: "1px solid var(--border)",
              borderRadius: "10px", color: "var(--text)", fontSize: "14px",
              outline: "none",
            }}
            onFocus={e => (e.target as HTMLElement).style.borderColor = "var(--accent)"}
            onBlur={e => (e.target as HTMLElement).style.borderColor = "var(--border)"}
          />
          <button
            onClick={search}
            disabled={loading || !query.trim()}
            style={{
              padding: "12px 24px", background: "var(--accent)", color: "white",
              border: "none", borderRadius: "10px", fontWeight: "600",
              fontSize: "14px", cursor: "pointer", opacity: loading || !query.trim() ? 0.5 : 1,
              transition: "opacity 0.15s",
            }}
          >
            {loading ? "..." : "Search"}
          </button>
        </div>
      </div>

      {/* Success */}
      {added && (
        <div style={{
          background: "var(--green-soft)", border: "1px solid rgba(29,185,84,0.3)",
          borderRadius: "12px", padding: "14px 20px", color: "var(--green)",
          fontSize: "14px", fontWeight: "500",
        }}>
          ✅ Added: {added}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div style={{
          background: "var(--bg-card)", border: "1px solid var(--border)",
          borderRadius: "16px", overflow: "hidden",
        }}>
          {results.map((r, i) => (
            <div
              key={i}
              style={{
                display: "flex", alignItems: "center", gap: "14px",
                padding: "12px 16px",
                borderBottom: i < results.length - 1 ? "1px solid var(--border)" : "none",
                cursor: "pointer", transition: "background 0.1s",
              }}
              onClick={() => addSong(r.webpage_url, r.title)}
              onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"}
              onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
            >
              {r.thumbnail ? (
                <img src={r.thumbnail} alt="" style={{ width: "48px", height: "48px", borderRadius: "6px", objectFit: "cover" }} />
              ) : (
                <div style={{ width: "48px", height: "48px", borderRadius: "6px", background: "var(--accent-soft)", display: "flex", alignItems: "center", justifyContent: "center" }}>🎵</div>
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: "14px", fontWeight: "500", color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {r.title}
                </p>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>{r.uploader} • {fmtDuration(r.duration)}</p>
              </div>
              <span style={{ fontSize: "12px", color: "var(--accent)", fontWeight: "500", flexShrink: 0 }}>+ Add</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
