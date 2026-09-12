import discord
from discord.ext import commands
import asyncio
import yt_dlp
import aiohttp
from aiohttp import web
import os
from dotenv import load_dotenv
import random
import subprocess
import sys

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Auto update yt-dlp on startup
subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], capture_output=True)

# ─── Audio Config (Best Quality) ────────────────────────────────────────────
YDL_OPTS = {
    'format': 'bestaudio/best',
    'audioquality': 0,
    'noplaylist': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 256k'
}

# ─── Bot Setup ───────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Guild State ─────────────────────────────────────────────────────────────
guild_states = {}

def get_state(guild_id):
    if guild_id not in guild_states:
        guild_states[guild_id] = {
            "queue": [],
            "history": [],
            "current": None,
            "loop": False,       # loop current song
            "loop_queue": False, # loop whole queue
            "volume": 0.8,
            "panel_message": None,
            "panel_channel": None,
            "paused": False,
        }
    return guild_states[guild_id]

# ─── YouTube Fetcher ─────────────────────────────────────────────────────────
async def fetch_song(query: str):
    """Fetch single song info"""
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
            print(f"Error fetching song: {e}")
            return None

async def fetch_playlist(url: str):
    """Fetch all songs from a YouTube playlist"""
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
                            "lazy": True,  # will fetch stream url when needed
                        })
            return songs, info.get('title', 'Playlist')
        except Exception as e:
            print(f"Error fetching playlist: {e}")
            return [], "Playlist"

async def search_songs(query: str, limit=5):
    """Search YouTube and return multiple results"""
    opts = {**YDL_OPTS, 'noplaylist': True, 'extract_flat': True}
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch{limit}:{query}", download=False))
            results = []
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        results.append({
                            "url": f"https://youtube.com/watch?v={entry.get('id', '')}",
                            "title": entry.get('title', 'Unknown'),
                            "duration": entry.get('duration', 0),
                            "thumbnail": entry.get('thumbnail', ''),
                            "webpage_url": f"https://youtube.com/watch?v={entry.get('id', '')}",
                            "uploader": entry.get('uploader', 'Unknown'),
                        })
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

# ─── Helpers ─────────────────────────────────────────────────────────────────
def fmt_duration(seconds):
    if not seconds:
        return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def progress_bar(current, total, length=14):
    if not total:
        return "▬" * length
    filled = int((current / total) * length)
    return "▬" * filled + "○" + "▬" * (length - filled - 1)

# ─── UI Components ───────────────────────────────────────────────────────────
class AddSongModal(discord.ui.Modal, title="Add Song or Playlist"):
    query = discord.ui.TextInput(
        label="Song name, YouTube URL, or Playlist URL",
        placeholder="e.g. Blinding Lights or https://youtube.com/...",
        required=True,
        max_length=500,
    )

    def __init__(self, state):
        super().__init__()
        self.state = state

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = self.query.value.strip()

        # Check if playlist
        if "playlist" in query or "list=" in query:
            await interaction.followup.send("⏳ Loading playlist...", ephemeral=True)
            songs, playlist_title = await fetch_playlist(query)
            if songs:
                self.state["queue"].extend(songs)
                await interaction.followup.send(f"✅ Added **{len(songs)} songs** from *{playlist_title}* to queue", ephemeral=True)
            else:
                await interaction.followup.send("❌ Couldn't load playlist", ephemeral=True)
                return
        else:
            # Search and show results if not a direct URL
            if not query.startswith("http"):
                results = await search_songs(query, limit=5)
                if not results:
                    await interaction.followup.send("❌ No results found", ephemeral=True)
                    return
                view = SearchResultsView(results, self.state)
                embed = discord.Embed(title="🔍 Search Results", color=0x1DB954)
                for i, r in enumerate(results):
                    embed.add_field(
                        name=f"{i+1}. {r['title'][:50]}",
                        value=f"⏱ {fmt_duration(r['duration'])} • {r['uploader']}",
                        inline=False
                    )
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                return
            else:
                song = await fetch_song(query)
                if not song:
                    await interaction.followup.send("❌ Couldn't fetch song", ephemeral=True)
                    return
                self.state["queue"].append(song)
                await interaction.followup.send(f"✅ Added **{song['title']}** to queue", ephemeral=True)

        # Auto play if not playing
        guild = interaction.guild
        if guild.voice_client is None or not guild.voice_client.is_playing():
            # Join VC
            if interaction.user.voice:
                vc = await interaction.user.voice.channel.connect()
            else:
                await interaction.followup.send("❌ Join a voice channel first", ephemeral=True)
                return
            await play_next(guild)

        await update_panel(interaction.guild)


class SearchResultsView(discord.ui.View):
    def __init__(self, results, state):
        super().__init__(timeout=60)
        self.state = state
        options = [
            discord.SelectOption(
                label=r['title'][:100],
                description=f"{fmt_duration(r['duration'])} • {r['uploader'][:50]}",
                value=str(i)
            )
            for i, r in enumerate(results)
        ]
        select = discord.ui.Select(placeholder="Pick a song...", options=options)
        select.callback = self.select_callback
        self.results = results
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        idx = int(interaction.data['values'][0])
        song_stub = self.results[idx]
        await interaction.response.defer(ephemeral=True)
        song = await fetch_song(song_stub['webpage_url'])
        if song:
            self.state["queue"].append(song)
            await interaction.followup.send(f"✅ Added **{song['title']}** to queue", ephemeral=True)

            guild = interaction.guild
            if guild.voice_client is None or not guild.voice_client.is_playing():
                if interaction.user.voice:
                    if guild.voice_client is None:
                        await interaction.user.voice.channel.connect()
                    await play_next(guild)
                else:
                    await interaction.followup.send("❌ Join a voice channel first", ephemeral=True)

            await update_panel(interaction.guild)


class QueueView(discord.ui.View):
    def __init__(self, state, page=0):
        super().__init__(timeout=60)
        self.state = state
        self.page = page

    @discord.ui.button(label="◀ Prev Page", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=build_queue_embed(self.state, self.page), view=self)

    @discord.ui.button(label="Next Page ▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        max_page = (len(self.state["queue"]) - 1) // 10
        if self.page < max_page:
            self.page += 1
        await interaction.response.edit_message(embed=build_queue_embed(self.state, self.page), view=self)


def build_queue_embed(state, page=0):
    queue = state["queue"]
    embed = discord.Embed(title="📋 Queue", color=0x1DB954)
    if not queue:
        embed.description = "Queue is empty"
        return embed

    start = page * 10
    end = min(start + 10, len(queue))
    for i in range(start, end):
        song = queue[i]
        embed.add_field(
            name=f"{i+1}. {song['title'][:50]}",
            value=f"⏱ {fmt_duration(song['duration'])}",
            inline=False
        )
    embed.set_footer(text=f"Page {page+1} • {len(queue)} songs total")
    return embed


class MusicControlView(discord.ui.View):
    def __init__(self, state):
        super().__init__(timeout=None)
        self.state = state

    @discord.ui.button(emoji="⏮", style=discord.ButtonStyle.secondary, row=0)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        if state["history"]:
            song = state["history"].pop()
            if state["current"]:
                state["queue"].insert(0, state["current"])
            state["queue"].insert(0, song)
            vc = interaction.guild.voice_client
            if vc and vc.is_playing():
                vc.stop()
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="⏸", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                state["paused"] = True
            elif vc.is_paused():
                vc.resume()
                state["paused"] = False
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="⏭", style=discord.ButtonStyle.secondary, row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=0)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        if not state["loop"] and not state["loop_queue"]:
            state["loop"] = True
            button.style = discord.ButtonStyle.success
        elif state["loop"]:
            state["loop"] = False
            state["loop_queue"] = True
        else:
            state["loop_queue"] = False
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        random.shuffle(state["queue"])
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="⏹", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        state["queue"].clear()
        state["current"] = None
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=1)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        state["volume"] = max(0.0, state["volume"] - 0.1)
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = state["volume"]
        await update_panel(interaction.guild)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        state = get_state(interaction.guild.id)
        state["volume"] = min(2.0, state["volume"] + 0.1)
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = state["volume"]
        await update_panel(interaction.guild)

    @discord.ui.button(label="➕ Add Song", style=discord.ButtonStyle.success, row=1)
    async def add_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(interaction.guild.id)
        await interaction.response.send_modal(AddSongModal(state))

    @discord.ui.button(label="📋 Queue", style=discord.ButtonStyle.secondary, row=1)
    async def queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(interaction.guild.id)
        embed = build_queue_embed(state)
        await interaction.response.send_message(embed=embed, view=QueueView(state), ephemeral=True)


# ─── Panel Builder ────────────────────────────────────────────────────────────
def build_panel_embed(state):
    current = state.get("current")
    paused = state.get("paused", False)
    loop = state.get("loop", False)
    loop_queue = state.get("loop_queue", False)
    volume = int(state.get("volume", 0.8) * 100)
    queue_len = len(state.get("queue", []))

    embed = discord.Embed(color=0x1DB954)

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
        embed.description = "No song playing. Click **➕ Add Song** to get started!"

    # Status row
    status = []
    status.append("⏸ Paused" if paused else "▶️ Playing")
    if loop:
        status.append("🔁 Loop: Song")
    elif loop_queue:
        status.append("🔁 Loop: Queue")
    status.append(f"🔊 {volume}%")
    status.append(f"📋 {queue_len} in queue")

    embed.add_field(name="Status", value=" • ".join(status), inline=False)
    embed.set_footer(text="Use buttons below to control music")

    return embed


async def update_panel(guild):
    state = get_state(guild.id)
    panel_msg = state.get("panel_message")
    if not panel_msg:
        return
    try:
        embed = build_panel_embed(state)
        view = MusicControlView(state)
        await panel_msg.edit(embed=embed, view=view)
    except Exception as e:
        print(f"Panel update error: {e}")


# ─── Playback ─────────────────────────────────────────────────────────────────
async def play_next(guild):
    state = get_state(guild.id)
    vc = guild.voice_client

    if not vc:
        return

    # Loop current song
    if state["loop"] and state["current"]:
        song = state["current"]
    elif state["queue"]:
        if state["current"]:
            state["history"].append(state["current"])
            if len(state["history"]) > 50:
                state["history"].pop(0)
        song = state["queue"].pop(0)
        state["current"] = song
    else:
        state["current"] = None
        await update_panel(guild)
        return

    # Fetch stream URL if lazy (from playlist)
    if song.get("lazy"):
        fetched = await fetch_song(song["webpage_url"])
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
            if error:
                print(f"Playback error: {error}")
            # loop queue
            if state["loop_queue"] and not state["loop"]:
                if state["current"]:
                    state["queue"].append(state["current"])
            asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)

        vc.play(source, after=after_play)
        await update_panel(guild)

    except Exception as e:
        print(f"Play error: {e}")
        await play_next(guild)


# ─── Commands ─────────────────────────────────────────────────────────────────
@bot.command(name="setup")
@commands.has_permissions(manage_guild=True)
async def setup(ctx):
    """Send the music control panel to this channel"""
    state = get_state(ctx.guild.id)
    embed = build_panel_embed(state)
    view = MusicControlView(state)
    msg = await ctx.send(embed=embed, view=view)
    state["panel_message"] = msg
    state["panel_channel"] = ctx.channel
    await ctx.message.delete()


@bot.event
async def on_voice_state_update(member, before, after):
    """Auto-leave when VC is empty"""
    if member.bot:
        return
    guild = member.guild
    vc = guild.voice_client
    if vc and len(vc.channel.members) == 1:
        await asyncio.sleep(30)
        if vc and len(vc.channel.members) == 1:
            state = get_state(guild.id)
            state["queue"].clear()
            state["current"] = None
            await vc.disconnect()
            await update_panel(guild)


@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user}")


# ─── Keep Alive (UptimeRobot) ─────────────────────────────────────────────────
async def keep_alive():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is alive!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()
    print("✅ Keep-alive server running")


async def main():
    await keep_alive()
    await bot.start(TOKEN)

asyncio.run(main())
