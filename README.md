# 🎵 Discord Music Bot

All-in-one Discord music bot with embedded Socket.io server and Next.js dashboard.

## Structure
```
/
├── bot.py              ← Python bot + Socket.io server
├── requirements.txt    
├── render.yaml         ← Render deployment config
└── dashboard/          ← Next.js dashboard (deploy to Vercel)
    ├── app/
    ├── components/
    ├── hooks/
    └── store/
```

## Deploy

### Bot → Render
1. Connect this repo to Render
2. Root directory: `/` (default)
3. Build: `pip install -r requirements.txt`
4. Start: `python bot.py`
5. Add env vars:
   ```
   DISCORD_TOKEN=...
   DASHBOARD_URL=https://your-dashboard.vercel.app
   PORT=8080
   ```

### Dashboard → Vercel
1. Connect this repo to Vercel
2. Root directory: `dashboard`
3. Add env vars:
   ```
   NEXT_PUBLIC_BOT_URL=https://your-bot.onrender.com
   BOT_URL=https://your-bot.onrender.com
   DISCORD_CLIENT_ID=...
   DISCORD_CLIENT_SECRET=...
   NEXTAUTH_SECRET=any_random_string
   NEXTAUTH_URL=https://your-dashboard.vercel.app
   ```

### UptimeRobot
Ping `https://your-bot.onrender.com` every 5 mins to keep it alive.

## Discord Setup
1. `!setup` in any text channel → pins the music control panel
2. Join a voice channel
3. Click **➕ Add Song** → type song name or YouTube URL
