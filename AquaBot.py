import discord
from discord.ext import tasks
from discord import app_commands
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_ID = 'UC1opHUrw8rvnsadT-iGp7Cg'
GUILD_ID = 1275721677782913035  # Must be an integer
ROLE_ID = 1275982267898138657    # Must be an integer
CHECK_INTERVAL = 3600  # Time in seconds between checks

intents = discord.Intents.default()
intents.message_content = True  # Enable the message_content intent

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        self.last_live_stream_id = None

    async def setup_hook(self):
        self.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.check_live_status.start()  # Start the periodic live status check

    async def get_live_status(self):
        try:
            request = self.youtube.search().list(
                part='snippet',
                channelId=CHANNEL_ID,
                eventType='live',
                type='video'
            )
            response = request.execute()
            items = response.get('items', [])
            
            if items:
                live_video_id = items[0]['id']['videoId']
                if live_video_id != self.last_live_stream_id:
                    self.last_live_stream_id = live_video_id
                    return live_video_id
        except Exception as e:
            print(f"Error checking live status: {e}")
        return None

    async def get_next_stream_time(self):
        try:
            request = self.youtube.search().list(
                part='snippet',
                channelId=CHANNEL_ID,
                type='video',
                order='date'
            )
            response = request.execute()
            items = response.get('items', [])
            
            for item in items:
                if item['snippet'].get('liveBroadcastContent') == 'upcoming':
                    return item['snippet']['publishedAt'], item['snippet']['title']
        except Exception as e:
            print(f"Error getting next stream time: {e}")
        return None, None

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_live_status(self):
        live_video_id = await self.get_live_status()
        if live_video_id:
            guild = self.get_guild(GUILD_ID)
            if guild:
                role = guild.get_role(ROLE_ID)
                channel = discord.utils.get(guild.text_channels, name='MinatoAqua')
                if role and channel:
                    await channel.send(
                        f'{role.mention} The channel is live now! Check it out: https://www.youtube.com/watch?v={live_video_id}'
                    )

def format_datetime(iso_string):
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%B %d, %Y at %I:%M %p')
    except ValueError:
        return iso_string

bot = MyBot()

@bot.tree.command(name='nextstream', description="Get the time of Minato Aqua's next stream.")
async def nextstream(interaction: discord.Interaction):
    next_stream_time, next_stream_title = await bot.get_next_stream_time()
    if next_stream_time:
        formatted_time = format_datetime(next_stream_time)
        await interaction.response.send_message(
            f'**Stream Title:** {next_stream_title}\n'
            f'**Stream Time:** {formatted_time}'
        )
    else:
        await interaction.response.send_message('No upcoming streams scheduled.')

@bot.tree.command(name='status', description="Get the current live status of Minato Aqua's channel.")
async def status(interaction: discord.Interaction):
    live_video_id = await bot.get_live_status()
    if live_video_id:
        await interaction.response.send_message(
            f'The channel is currently live! Check it out: https://www.youtube.com/watch?v={live_video_id}'
        )
    else:
        await interaction.response.send_message('The channel is currently not live.')

bot.run(DISCORD_TOKEN)