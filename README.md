# 🎵 Discord Music Bot

Play music together in voice channels with a beautiful control panel UI.

## Setup

### 1. Requirements
- Python 3.10+
- FFmpeg installed and added to PATH

### 2. Install FFmpeg (Windows)
Download from https://ffmpeg.org/download.html → add `bin` folder to PATH

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Discord Bot
1. Go to https://discord.com/developers/applications
2. New Application → Bot → Copy Token
3. Enable: `MESSAGE CONTENT INTENT`, `SERVER MEMBERS INTENT`, `PRESENCE INTENT`
4. Invite bot with scopes: `bot`, `applications.commands`
5. Permissions: `Send Messages`, `Embed Links`, `Connect`, `Speak`, `Use Voice Activity`

### 5. Configure
```bash
cp .env.example .env
# Add your DISCORD_TOKEN to .env
```

### 6. Run locally
```bash
python bot.py
```

### 7. Setup in Discord
In any text channel type:
```
!setup
```
This sends the music control panel. Pin it or use it directly.

## Usage
- Click **➕ Add Song** → type song name, YouTube URL, or playlist URL
- Use buttons to control playback
- Bot auto-joins your voice channel
- Bot auto-leaves when VC is empty

## Deploy to Render + UptimeRobot
1. Push to GitHub
2. New Web Service on Render → connect repo
3. Add `DISCORD_TOKEN` env var
4. Deploy
5. Add UptimeRobot monitor → ping your Render URL every 5 mins
