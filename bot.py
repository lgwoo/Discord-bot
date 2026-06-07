import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(f"Loaded cogs: {[c for c in bot.cogs]}")


async def main():
    async with bot:
        await bot.load_extension("cogs.qa")
        await bot.load_extension("cogs.greeting")
        await bot.load_extension("cogs.pomodoro")
        await bot.load_extension("cogs.todo")
        await bot.start(os.environ["DISCORD_TOKEN"])


asyncio.run(main())
