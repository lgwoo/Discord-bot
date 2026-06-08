import base64
import io
import json
import os
import re
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

TIMELY_BASE_URL = "https://hello.timelygpt.co.kr/api/v2/chat/bridge/openai"
MODEL = "anthropic/claude-haiku-4.5"
IMAGE_MODEL = "google/gemini-2.5-flash-image"
MAX_TOKENS = 1024
DISCORD_CHAR_LIMIT = 2000
HISTORY_LIMIT = 10  # 채널당 최근 대화 유지 개수

_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "system_prompt.txt")
_MEMBERS_FILE = os.path.join(os.path.dirname(__file__), "..", "members.json")

# 채널 ID → deque of {"role": ..., "content": ...}
_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_LIMIT * 2))


def load_system_prompt() -> str:
    with open(_PROMPT_FILE, encoding="utf-8") as f:
        return f.read().strip()


def resolve_name(username: str) -> str:
    try:
        with open(_MEMBERS_FILE, encoding="utf-8") as f:
            members = json.load(f)
        return members.get(username, username)
    except (FileNotFoundError, json.JSONDecodeError):
        return username

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.environ["TIMELYGPT_API_KEY"],
            base_url=TIMELY_BASE_URL,
        )
    return _client


async def ask_ai(question: str, channel_id: int, username: str | None = None) -> str:
    content = f"[{username}]: {question}" if username else question
    history = _history[channel_id]

    messages = [
        {"role": "system", "content": load_system_prompt()},
        *list(history),
        {"role": "user", "content": content},
    ]

    response = await get_client().chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=messages,
    )
    reply = " ".join(response.choices[0].message.content.split("\n")).strip()

    history.append({"role": "user", "content": content})
    history.append({"role": "assistant", "content": reply})

    return reply


async def generate_image(prompt: str) -> discord.File | str:
    """Returns discord.File if image data received, or str URL if URL received."""
    response = await get_client().chat.completions.create(
        model=IMAGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"modalities": ["image", "text"]},
    )
    print(f"[image] raw response={response!r}")

    message = response.choices[0].message
    content = message.content

    # content가 리스트인 경우 (멀티모달 응답)
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "image_url":
                    url = part["image_url"]["url"]
                    if url.startswith("data:"):
                        # base64 data URL
                        header, b64data = url.split(",", 1)
                        mime = header.split(";")[0].split(":")[1]
                        ext = mime.split("/")[-1]
                        img_bytes = base64.b64decode(b64data)
                        return discord.File(io.BytesIO(img_bytes), filename=f"image.{ext}")
                    return url
                elif part.get("type") == "text":
                    continue

    # content가 문자열인 경우
    if isinstance(content, str):
        # base64 data URL 형태
        if content.startswith("data:"):
            header, b64data = content.split(",", 1)
            mime = header.split(";")[0].split(":")[1]
            ext = mime.split("/")[-1]
            img_bytes = base64.b64decode(b64data)
            return discord.File(io.BytesIO(img_bytes), filename=f"image.{ext}")
        # 일반 URL
        if content.startswith("http"):
            return content

    raise ValueError(f"이미지 URL을 응답에서 찾을 수 없음. 원본: {content!r}")


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
                reply = await ask_ai(question, channel_id=message.channel.id, username=resolve_name(message.author.name))
            print(f"[qa] reply={reply[:100]!r}")
            if len(reply) <= DISCORD_CHAR_LIMIT:
                await message.reply(reply)
            else:
                await message.reply(reply[:DISCORD_CHAR_LIMIT])
                await send_long(message.channel, reply[DISCORD_CHAR_LIMIT:])
        except Exception as e:
            print(f"[qa] ERROR: {e!r}")
            await message.reply(f"오류 발생: {e}")

    @app_commands.command(name="이미지", description="AI로 이미지를 생성합니다")
    @app_commands.describe(프롬프트="생성할 이미지 설명")
    async def slash_image(self, interaction: discord.Interaction, 프롬프트: str):
        await interaction.response.defer()
        try:
            result = await generate_image(프롬프트)
            if isinstance(result, discord.File):
                await interaction.followup.send(file=result)
            else:
                await interaction.followup.send(result)
        except Exception as e:
            print(f"[image] ERROR: {e!r}")
            await interaction.followup.send(f"이미지 생성 오류: {e}")

    @app_commands.command(name="질문", description="AI에게 질문하세요")
    @app_commands.describe(질문내용="AI에게 물어볼 내용")
    async def slash_ask(self, interaction: discord.Interaction, 질문내용: str):
        await interaction.response.defer()
        try:
            reply = await ask_ai(질문내용, channel_id=interaction.channel_id, username=resolve_name(interaction.user.name))
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
