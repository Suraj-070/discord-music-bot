import discord
from discord.ext import commands
import asyncio
import yt_dlp
import aiohttp
from aiohttp import web
import socketio
import os
import random
import subprocess
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
print(f"🔑 Token loaded: {'YES (length=' + str(len(TOKEN)) + ')' if TOKEN else 'NO - DISCORD_TOKEN not set!'}", flush=True)
PORT = int(os.getenv("PORT", 8080))

# Auto update yt-dlp
subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], capture_output=True)

# ─── Audio Config ─────────────────────────────────────────────────────────────
COOKIES_FILE = '/etc/secrets/cookies.txt'
import os as _os

YDL_OPTS = {
    'format': 'bestaudio/best',
    'audioquality': 0,
    'noplaylist': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'remote_components': 'ejs:github',
    'cookiefile': COOKIES_FILE if _os.path.exists(COOKIES_FILE) else None,
    'extractor_args': {
        'youtube': {
            'player_client': ['web_creator', 'ios', 'mweb'],
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
    },
}

FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 256k'
}

# ─── Bot Setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Socket.io Server ─────────────────────────────────────────────────────────
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False,
)

# ─── Guild State ──────────────────────────────────────────────────────────────
guild_states = {}

def get_state(guild_id):
    gid = str(guild_id)
    if gid not in guild_states:
        guild_states[gid] = {
            "queue": [],
            "history": [],
            "current": None,
            "loop": False,
            "loop_queue": False,
            "volume": 0.8,
            "panel_message": None,
            "panel_channel": None,
            "paused": False,
            "elapsed": 0,
        }
    return guild_states[gid]

# ─── YouTube Helpers ──────────────────────────────────────────────────────────
async def fetch_song(query: str):
    opts = {**YDL_OPTS, 'noplaylist': True}
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            if not query.startswith("http"):
                query = f"ytsearch:{query}"
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
            if 'entries' in info:
                info = info['entries'][0]
            return {
                "url": info['url'],
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', 0),
                "thumbnail": info.get('thumbnail', ''),
                "webpage_url": info.get('webpage_url', ''),
                "uploader": info.get('uploader', 'Unknown'),
            }
        except Exception as e:
            print(f"Fetch error: {e}")
            return None

async def fetch_playlist(url: str):
    opts = {**YDL_OPTS, 'noplaylist': False, 'extract_flat': True}
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            songs = []
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        songs.append({
                            "url": f"https://youtube.com/watch?v={entry.get('id', '')}",
                            "title": entry.get('title', 'Unknown'),
                            "duration": entry.get('duration', 0),
                            "thumbnail": entry.get('thumbnail', ''),
                            "webpage_url": f"https://youtube.com/watch?v={entry.get('id', '')}",
                            "uploader": entry.get('uploader', 'Unknown'),
                            "lazy": True,
                        })
            return songs, info.get('title', 'Playlist')
        except Exception as e:
            print(f"Playlist error: {e}")
            return [], "Playlist"

async def search_songs(query: str, limit=5):
    opts = {**YDL_OPTS, 'noplaylist': True, 'extract_flat': True}
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"scsearch{limit}:{query}", download=False))
            results = []
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        results.append({
                            "url": entry.get('url', entry.get('webpage_url', '')),
                            "title": entry.get('title', 'Unknown'),
                            "duration": entry.get('duration', 0),
                            "thumbnail": entry.get('thumbnail', ''),
                            "webpage_url": entry.get('webpage_url', entry.get('url', '')),
                            "uploader": entry.get('uploader', entry.get('artist', 'Unknown')),
                        })
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt_duration(seconds):
    if not seconds: return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def progress_bar(current, total, length=14):
    if not total: return "▬" * length
    filled = int((current / total) * length)
    return "▬" * filled + "○" + "▬" * (length - filled - 1)

def song_to_dict(song):
    if not song: return None
    return {k: v for k, v in song.items() if k != 'url'}  # don't expose stream url

# ─── Socket.io Emit Helpers ───────────────────────────────────────────────────
async def emit_now_playing(guild_id):
    state = get_state(guild_id)
    await sio.emit('now_playing', {
        'song': song_to_dict(state['current']),
        'paused': state['paused'],
    }, room=str(guild_id))

async def emit_queue_update(guild_id):
    state = get_state(guild_id)
    await sio.emit('queue_update', {
        'queue': [song_to_dict(s) for s in state['queue']]
    }, room=str(guild_id))

async def emit_state(guild_id):
    state = get_state(guild_id)
    await sio.emit('full_state', {
        'current': song_to_dict(state['current']),
        'queue': [song_to_dict(s) for s in state['queue']],
        'paused': state['paused'],
        'loop': state['loop'],
        'loop_queue': state['loop_queue'],
        'volume': state['volume'],
        'elapsed': state['elapsed'],
    }, room=str(guild_id))

# ─── Socket.io Events ─────────────────────────────────────────────────────────
@sio.event
async def connect(sid, environ, auth):
    print(f"Dashboard connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Dashboard disconnected: {sid}")

@sio.event
async def join_guild(sid, data):
    guild_id = str(data.get('guildId', ''))
    await sio.enter_room(sid, guild_id)
    await emit_state(guild_id)

@sio.event
async def pause(sid, data):
    guild_id = data.get('guildId')
    guild = bot.get_guild(int(guild_id))
    if guild and guild.voice_client:
        guild.voice_client.pause()
        get_state(guild_id)['paused'] = True
        await sio.emit('paused', room=guild_id)
        await update_panel(guild)

@sio.event
async def resume(sid, data):
    guild_id = data.get('guildId')
    guild = bot.get_guild(int(guild_id))
    if guild and guild.voice_client:
        guild.voice_client.resume()
        get_state(guild_id)['paused'] = False
        await sio.emit('resumed', room=guild_id)
        await update_panel(guild)

@sio.event
async def next(sid, data):
    guild_id = data.get('guildId')
    guild = bot.get_guild(int(guild_id))
    if guild and guild.voice_client:
        guild.voice_client.stop()

@sio.event
async def prev(sid, data):
    guild_id = data.get('guildId')
    guild = bot.get_guild(int(guild_id))
    if not guild: return
    state = get_state(guild_id)
    if state['history']:
        song = state['history'].pop()
        if state['current']:
            state['queue'].insert(0, state['current'])
        state['queue'].insert(0, song)
        if guild.voice_client:
            guild.voice_client.stop()

@sio.event
async def stop(sid, data):
    guild_id = data.get('guildId')
    guild = bot.get_guild(int(guild_id))
    if not guild: return
    state = get_state(guild_id)
    state['queue'].clear()
    state['current'] = None
    if guild.voice_client:
        guild.voice_client.stop()
        await guild.voice_client.disconnect()
    await sio.emit('stopped', room=guild_id)
    await update_panel(guild)

@sio.event
async def shuffle(sid, data):
    guild_id = data.get('guildId')
    state = get_state(guild_id)
    random.shuffle(state['queue'])
    await emit_queue_update(guild_id)
    guild = bot.get_guild(int(guild_id))
    if guild: await update_panel(guild)

@sio.event
async def toggle_loop(sid, data):
    guild_id = data.get('guildId')
    state = get_state(guild_id)
    if not state['loop'] and not state['loop_queue']:
        state['loop'] = True
    elif state['loop']:
        state['loop'] = False
        state['loop_queue'] = True
    else:
        state['loop_queue'] = False
    await sio.emit('loop_update', {'loop': state['loop'], 'loop_queue': state['loop_queue']}, room=guild_id)
    guild = bot.get_guild(int(guild_id))
    if guild: await update_panel(guild)

@sio.event
async def volume(sid, data):
    guild_id = data.get('guildId')
    vol = float(data.get('volume', 0.8))
    state = get_state(guild_id)
    state['volume'] = vol
    guild = bot.get_guild(int(guild_id))
    if guild and guild.voice_client and guild.voice_client.source:
        guild.voice_client.source.volume = vol
    await sio.emit('volume_update', {'volume': vol}, room=guild_id)

@sio.event
async def add_song(sid, data):
    guild_id = data.get('guildId')
    query = data.get('query', '')
    state = get_state(guild_id)

    if 'playlist' in query or 'list=' in query:
        songs, title = await fetch_playlist(query)
        state['queue'].extend(songs)
        await sio.emit('toast', {'msg': f'Added {len(songs)} songs from {title}'}, room=guild_id)
    else:
        song = await fetch_song(query)
        if song:
            state['queue'].append(song)
            await sio.emit('toast', {'msg': f'Added: {song["title"]}'}, room=guild_id)

    await emit_queue_update(guild_id)

    guild = bot.get_guild(int(guild_id))
    if guild and (not guild.voice_client or not guild.voice_client.is_playing()):
        # Find a VC with members
        for vc in guild.voice_channels:
            members = [m for m in vc.members if not m.bot]
            if members:
                if not guild.voice_client:
                    await vc.connect()
                await play_next(guild)
                break

    if guild: await update_panel(guild)

@sio.event
async def search(sid, data):
    query = data.get('query', '')
    results = await search_songs(query)
    await sio.emit('search_results', {'results': results}, to=sid)

@sio.event
async def remove_from_queue(sid, data):
    guild_id = data.get('guildId')
    index = data.get('index', 0)
    state = get_state(guild_id)
    if 0 <= index < len(state['queue']):
        state['queue'].pop(index)
    await emit_queue_update(guild_id)
    guild = bot.get_guild(int(guild_id))
    if guild: await update_panel(guild)

# ─── Discord UI ───────────────────────────────────────────────────────────────
class AddSongModal(discord.ui.Modal, title="Add Song or Playlist"):
    query = discord.ui.TextInput(
        label="Song name, YouTube URL, or Playlist URL",
        placeholder="e.g. Blinding Lights or https://youtube.com/...",
        required=True, max_length=500,
    )

    def __init__(self, state):
        super().__init__()
        self.state = state

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = self.query.value.strip()

        if "playlist" in query or "list=" in query:
            await interaction.followup.send("⏳ Loading playlist...", ephemeral=True)
            songs, title = await fetch_playlist(query)
            if songs:
                self.state["queue"].extend(songs)
                await interaction.followup.send(f"✅ Added **{len(songs)} songs** from *{title}*", ephemeral=True)
            else:
                await interaction.followup.send("❌ Couldn't load playlist", ephemeral=True)
                return
        elif not query.startswith("http"):
            results = await search_songs(query, limit=5)
            if not results:
                await interaction.followup.send("❌ No results", ephemeral=True)
                return
            view = SearchResultsView(results, self.state)
            embed = discord.Embed(title="🔍 Search Results", color=0x7c6af7)
            for i, r in enumerate(results):
                embed.add_field(name=f"{i+1}. {r['title'][:50]}", value=f"⏱ {fmt_duration(r['duration'])} • {r['uploader']}", inline=False)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        else:
            song = await fetch_song(query)
            if not song:
                await interaction.followup.send("❌ Couldn't fetch song", ephemeral=True)
                return
            self.state["queue"].append(song)
            await interaction.followup.send(f"✅ Added **{song['title']}**", ephemeral=True)

        guild = interaction.guild
        if guild.voice_client is None or not guild.voice_client.is_playing():
            if interaction.user.voice:
                if not guild.voice_client:
                    await interaction.user.voice.channel.connect()
                await play_next(guild)
            else:
                await interaction.followup.send("❌ Join a voice channel first", ephemeral=True)
                return

        await update_panel(guild)
        await emit_queue_update(str(guild.id))


class SearchResultsView(discord.ui.View):
    def __init__(self, results, state):
        super().__init__(timeout=60)
        self.state = state
        self.results = results
        options = [
            discord.SelectOption(
                label=r['title'][:100],
                description=f"{fmt_duration(r['duration'])} • {r['uploader'][:50]}",
                value=str(i)
            ) for i, r in enumerate(results)
        ]
        select = discord.ui.Select(placeholder="Pick a song...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        idx = int(interaction.data['values'][0])
        await interaction.response.defer(ephemeral=True)
        song = await fetch_song(self.results[idx]['webpage_url'])
        if song:
            self.state["queue"].append(song)
            await interaction.followup.send(f"✅ Added **{song['title']}**", ephemeral=True)
            guild = interaction.guild
            if guild.voice_client is None or not guild.voice_client.is_playing():
                if interaction.user.voice:
                    if not guild.voice_client:
                        await interaction.user.voice.channel.connect()
                    await play_next(guild)
            await update_panel(guild)
            await emit_queue_update(str(guild.id))


class QueueView(discord.ui.View):
    def __init__(self, state, page=0):
        super().__init__(timeout=60)
        self.state = state
        self.page = page

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button):
        if self.page > 0: self.page -= 1
        await interaction.response.edit_message(embed=build_queue_embed(self.state, self.page), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button):
        max_p = max(0, (len(self.state["queue"]) - 1) // 10)
        if self.page < max_p: self.page += 1
        await interaction.response.edit_message(embed=build_queue_embed(self.state, self.page), view=self)


def build_queue_embed(state, page=0):
    queue = state["queue"]
    embed = discord.Embed(title="📋 Queue", color=0x7c6af7)
    if not queue:
        embed.description = "Queue is empty"
        return embed
    start, end = page * 10, min(page * 10 + 10, len(queue))
    for i in range(start, end):
        s = queue[i]
        embed.add_field(name=f"{i+1}. {s['title'][:50]}", value=f"⏱ {fmt_duration(s['duration'])}", inline=False)
    embed.set_footer(text=f"Page {page+1} • {len(queue)} songs")
    return embed


class MusicControlView(discord.ui.View):
    def __init__(self, state):
        super().__init__(timeout=None)
        self.state = state

    @discord.ui.button(emoji="⏮", style=discord.ButtonStyle.secondary, row=0)
    async def prev(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        if state["history"]:
            song = state["history"].pop()
            if state["current"]: state["queue"].insert(0, state["current"])
            state["queue"].insert(0, song)
            vc = interaction.guild.voice_client
            if vc and vc.is_playing(): vc.stop()
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="⏸", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause(); state["paused"] = True
                await sio.emit('paused', room=str(interaction.guild.id))
            elif vc.is_paused():
                vc.resume(); state["paused"] = False
                await sio.emit('resumed', room=str(interaction.guild.id))
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="⏭", style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()): vc.stop()

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=0)
    async def loop(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        if not state["loop"] and not state["loop_queue"]:
            state["loop"] = True
        elif state["loop"]:
            state["loop"] = False; state["loop_queue"] = True
        else:
            state["loop_queue"] = False
        await sio.emit('loop_update', {'loop': state['loop'], 'loop_queue': state['loop_queue']}, room=str(interaction.guild.id))
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        random.shuffle(state["queue"])
        await emit_queue_update(str(interaction.guild.id))
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="⏹", style=discord.ButtonStyle.danger, row=1)
    async def stop(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        state["queue"].clear(); state["current"] = None
        vc = interaction.guild.voice_client
        if vc: vc.stop(); await vc.disconnect()
        await sio.emit('stopped', room=str(interaction.guild.id))
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=2)
    async def vol_down(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        state["volume"] = max(0.0, state["volume"] - 0.1)
        vc = interaction.guild.voice_client
        if vc and vc.source: vc.source.volume = state["volume"]
        await sio.emit('volume_update', {'volume': state['volume']}, room=str(interaction.guild.id))
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=2)
    async def vol_up(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        state["volume"] = min(2.0, state["volume"] + 0.1)
        vc = interaction.guild.voice_client
        if vc and vc.source: vc.source.volume = state["volume"]
        await sio.emit('volume_update', {'volume': state['volume']}, room=str(interaction.guild.id))
        await update_panel(interaction.guild)

    @discord.ui.button(label="➕ Add Song", style=discord.ButtonStyle.success, row=2)
    async def add_song(self, interaction: discord.Interaction, button):
        state = get_state(interaction.guild.id)
        await interaction.response.send_modal(AddSongModal(state))

    @discord.ui.button(label="📋 Queue", style=discord.ButtonStyle.secondary, row=2)
    async def queue(self, interaction: discord.Interaction, button):
        state = get_state(interaction.guild.id)
        await interaction.response.send_message(embed=build_queue_embed(state), view=QueueView(state), ephemeral=True)


# ─── Panel ────────────────────────────────────────────────────────────────────
def build_panel_embed(state):
    current = state.get("current")
    paused = state.get("paused", False)
    loop = state.get("loop", False)
    loop_queue = state.get("loop_queue", False)
    volume = int(state.get("volume", 0.8) * 100)
    queue_len = len(state.get("queue", []))

    embed = discord.Embed(color=0x7c6af7)

    if current:
        embed.title = "🎵 Now Playing"
        embed.description = f"**[{current['title']}]({current.get('webpage_url', '')})**\n{current.get('uploader', '')}"
        duration = current.get('duration', 0)
        bar = progress_bar(0, duration)
        embed.add_field(name="Duration", value=f"`{bar}` {fmt_duration(duration)}", inline=False)
        if current.get('thumbnail'):
            embed.set_thumbnail(url=current['thumbnail'])
    else:
        embed.title = "🎵 Music Bot"
        embed.description = "No song playing. Click **➕ Add Song** to start!"

    status = []
    status.append("⏸ Paused" if paused else "▶️ Playing")
    if loop: status.append("🔂 Loop: Song")
    elif loop_queue: status.append("🔁 Loop: Queue")
    status.append(f"🔊 {volume}%")
    status.append(f"📋 {queue_len} in queue")
    embed.add_field(name="Status", value=" • ".join(status), inline=False)
    embed.set_footer(text="Use buttons below • Dashboard: " + os.getenv("DASHBOARD_URL", ""))

    return embed


async def update_panel(guild):
    state = get_state(guild.id)
    msg = state.get("panel_message")
    if not msg: return
    try:
        embed = build_panel_embed(state)
        view = MusicControlView(state)
        await msg.edit(embed=embed, view=view)
    except Exception as e:
        print(f"Panel error: {e}")


# ─── Playback ─────────────────────────────────────────────────────────────────
async def play_next(guild):
    state = get_state(guild.id)
    vc = guild.voice_client
    if not vc: return

    if state["loop"] and state["current"]:
        song = state["current"]
    elif state["queue"]:
        if state["current"]:
            state["history"].append(state["current"])
            if len(state["history"]) > 50: state["history"].pop(0)
        song = state["queue"].pop(0)
        state["current"] = song
    else:
        state["current"] = None
        await update_panel(guild)
        await emit_now_playing(str(guild.id))
        await emit_queue_update(str(guild.id))
        return

    # Fetch real stream URL if lazy (playlist track)
    if song.get("lazy"):
        # Use sc_query if available (YouTube playlist converted to SC search)
        search_query = song.get("sc_query") or song.get("title", "")
        fetched = await fetch_song(search_query)
        if fetched:
            song.update(fetched)
            song["lazy"] = False
        else:
            await play_next(guild)
            return

    try:
        source = discord.FFmpegPCMAudio(song["url"], **FFMPEG_OPTS)
        source = discord.PCMVolumeTransformer(source, volume=state["volume"])

        def after_play(error):
            if error: print(f"Playback error: {error}")
            if state["loop_queue"] and not state["loop"] and state["current"]:
                state["queue"].append(state["current"])
            asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)

        vc.play(source, after=after_play)
        state["paused"] = False
        state["elapsed"] = 0

        await emit_now_playing(str(guild.id))
        await emit_queue_update(str(guild.id))
        await update_panel(guild)

    except Exception as e:
        print(f"Play error: {e}")
        await play_next(guild)


# ─── Commands ─────────────────────────────────────────────────────────────────
@bot.command(name="music")
async def setup(ctx):
    state = get_state(ctx.guild.id)
    embed = build_panel_embed(state)
    view = MusicControlView(state)
    msg = await ctx.send(embed=embed, view=view)
    state["panel_message"] = msg
    state["panel_channel"] = ctx.channel
    try:
        await ctx.message.delete()
    except:
        pass


@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot: return
    guild = member.guild
    vc = guild.voice_client
    if vc and len([m for m in vc.channel.members if not m.bot]) == 0:
        await asyncio.sleep(30)
        if vc and len([m for m in vc.channel.members if not m.bot]) == 0:
            state = get_state(guild.id)
            state["queue"].clear(); state["current"] = None
            await vc.disconnect()
            await update_panel(guild)
            await emit_state(str(guild.id))


@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user}")



@bot.event
async def on_message(message):
    print(f"📨 Message: {message.content!r} from {message.author}", flush=True)
    if message.content.startswith("!"):
        print(f"🎯 Command detected: {message.content}", flush=True)
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    print(f"❌ Command error: {error}", flush=True)

@bot.event  
async def on_command(ctx):
    print(f"✅ Command invoked: {ctx.command}", flush=True)

# ─── aiohttp + Socket.io App ──────────────────────────────────────────────────
async def make_app():
    app = web.Application()
    sio.attach(app)

    async def index(request):
        return web.Response(
            text="🎵 Music bot is alive!",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    async def search_handler(request):
        q = request.rel_url.query.get('q', '')
        if not q:
            return web.json_response({'results': []}, headers={"Access-Control-Allow-Origin": "*"})
        results = await search_songs(q)
        return web.json_response({'results': results}, headers={"Access-Control-Allow-Origin": "*"})

    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == 'OPTIONS':
            return web.Response(headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            })
        response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    app = web.Application(middlewares=[cors_middleware])
    sio.attach(app)

    app.router.add_get('/', index)
    app.router.add_get('/search', search_handler)

    return app


async def main():
    app = await make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ Server running on :{PORT}", flush=True)
    print(f"🤖 Starting bot with token length: {len(TOKEN) if TOKEN else 0}", flush=True)
    try:
        await bot.start(TOKEN)
    except discord.LoginFailure as e:
        print(f"❌ Login failed: {e}", flush=True)
        raise
    except Exception as e:
        print(f"❌ Bot error: {type(e).__name__}: {e}", flush=True)
        raise


asyncio.run(main())
