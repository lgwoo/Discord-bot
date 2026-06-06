import os
import re

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

TIMELY_BASE_URL = "https://hello.timelygpt.co.kr/api/v2/chat/bridge/openai"
MODEL = "anthropic/claude-haiku-4.5"
MAX_TOKENS = 1024
DISCORD_CHAR_LIMIT = 2000

_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "system_prompt.txt")


def load_system_prompt() -> str:
    with open(_PROMPT_FILE, encoding="utf-8") as f:
        return f.read().strip()

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.environ["TIMELYGPT_API_KEY"],
            base_url=TIMELY_BASE_URL,
        )
    return _client


async def ask_ai(question: str) -> str:
    response = await get_client().chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


async def send_long(target, text: str):
    for i in range(0, len(text), DISCORD_CHAR_LIMIT):
        await target.send(text[i : i + DISCORD_CHAR_LIMIT])


class QA(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        print(f"[on_message] from={message.author} content={message.content!r}")
        if message.author.bot:
            return

        user_mentioned = self.bot.user in message.mentions
        role_mentioned = False
        if message.guild and message.role_mentions:
            bot_member = message.guild.get_member(self.bot.user.id)
            if bot_member:
                bot_role_ids = {r.id for r in bot_member.roles if r.managed}
                role_mentioned = any(r.id in bot_role_ids for r in message.role_mentions)

        if not user_mentioned and not role_mentioned:
            return

        question = re.sub(r"<[@&!]\d+>", "", message.content).strip()
        print(f"[qa] question={question!r}")
        if not question:
            await message.reply("질문을 입력해주세요!")
            return

        try:
            async with message.channel.typing():
                reply = await ask_ai(question)
            print(f"[qa] reply={reply[:100]!r}")
            if len(reply) <= DISCORD_CHAR_LIMIT:
                await message.reply(reply)
            else:
                await message.reply(reply[:DISCORD_CHAR_LIMIT])
                await send_long(message.channel, reply[DISCORD_CHAR_LIMIT:])
        except Exception as e:
            print(f"[qa] ERROR: {e!r}")
            await message.reply(f"오류 발생: {e}")

    @app_commands.command(name="질문", description="AI에게 질문하세요")
    @app_commands.describe(질문내용="AI에게 물어볼 내용")
    async def slash_ask(self, interaction: discord.Interaction, 질문내용: str):
        await interaction.response.defer()
        try:
            reply = await ask_ai(질문내용)
            if len(reply) <= DISCORD_CHAR_LIMIT:
                await interaction.followup.send(reply)
            else:
                await interaction.followup.send(reply[:DISCORD_CHAR_LIMIT])
                await send_long(interaction.channel, reply[DISCORD_CHAR_LIMIT:])
        except Exception as e:
            print(f"[qa] slash ERROR: {e!r}")
            await interaction.followup.send(f"오류 발생: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(QA(bot))
