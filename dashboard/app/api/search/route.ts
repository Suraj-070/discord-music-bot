import { NextRequest, NextResponse } from "next/server"

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q")
  if (!q) return NextResponse.json({ results: [] })
  try {
    // Proxy search directly to the Python bot
    const BOT_URL = process.env.BOT_URL || "http://localhost:8080"
    const res = await fetch(`${BOT_URL}/search?q=${encodeURIComponent(q)}`)
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ results: [] })
  }
}
