import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Loaded cogs: {[c for c in bot.cogs]}")


async def main():
    async with bot:
        await bot.load_extension("cogs.qa")
        await bot.load_extension("cogs.greeting")
        await bot.start(os.environ["DISCORD_TOKEN"])


asyncio.run(main())
