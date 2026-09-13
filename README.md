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

## 1. Add Bot to Server
Use this link to invite the bot:
```
https://discord.com/oauth2/authorize?client_id=1324726475152294022&permissions=36826192&integration_type=0&scope=bot
```

## 2. Discord Developer Portal Setup
Go to https://discord.com/developers/applications → your app

**Bot → Privileged Gateway Intents — enable all three:**
- ✅ Server Members Intent
- ✅ Message Content Intent
- ✅ Presence Intent

**OAuth2 → Redirects — add:**
```
https://your-dashboard.vercel.app/api/auth/callback/discord
```

## 3. Deploy Bot → Render
1. New Web Service → connect `Suraj-070/discord-music-bot`
2. Root directory: `/` (default)
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. Add env vars:
```
DISCORD_TOKEN=        ← Bot → Reset Token
DASHBOARD_URL=        ← your Vercel URL (add after step 4)
PORT=8080
```

## 4. Deploy Dashboard → Vercel
1. Import `Suraj-070/discord-music-bot`
2. Root directory: `dashboard`
3. Add env vars:
```
DISCORD_CLIENT_ID=1324726475152294022
DISCORD_CLIENT_SECRET=        ← OAuth2 → Client Secret
NEXTAUTH_SECRET=              ← any random string (run: openssl rand -base64 32)
NEXTAUTH_URL=                 ← https://your-dashboard.vercel.app
NEXT_PUBLIC_BOT_URL=          ← https://your-bot.onrender.com
BOT_URL=                      ← https://your-bot.onrender.com
```

## 5. Link Both Together
- Go back to Render → add `DASHBOARD_URL` = your Vercel URL
- Go back to Discord dev portal → add Vercel URL as OAuth redirect URI

## 6. UptimeRobot
- New monitor → HTTP(s)
- URL: `https://your-bot.onrender.com`
- Interval: every 5 minutes

## 7. Use the Bot
- Go to your Discord server
- In any text channel type: `!setup`
- Bot sends the music control panel
- Join a voice channel
- Click **➕ Add Song** → type song name or YouTube URL
- Control from Discord buttons or the web dashboard

## Bot Permissions
Permission integer: `36826192`
- Read Messages / View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Add Reactions
- Connect (voice)
- Speak (voice)
- Use Voice Activity
- Manage Messages
