import datetime

import discord
from discord.ext import commands, tasks

from cogs.qa import ask_ai

# KST = UTC+9
KST = datetime.timezone(datetime.timedelta(hours=9))

MORNING_TIME = datetime.time(hour=8, minute=0, tzinfo=KST)
NIGHT_TIME = datetime.time(hour=22, minute=0, tzinfo=KST)


class Greeting(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.morning_greeting.start()
        self.night_greeting.start()

    def cog_unload(self):
        self.morning_greeting.cancel()
        self.night_greeting.cancel()

    def get_channel(self) -> discord.TextChannel | None:
        import os
        channel_id = os.environ.get("GREETING_CHANNEL_ID")
        if not channel_id:
            return None
        return self.bot.get_channel(int(channel_id))

    @tasks.loop(time=MORNING_TIME)
    async def morning_greeting(self):
        channel = self.get_channel()
        if not channel:
            return
        msg = await ask_ai(
            "아침이야. 건우한테 아침 인사 해줘. "
            "오늘 하루 시작하는 느낌으로, 따뜻하게. "
            "중간에 오늘 하루를 살아갈 힘이 되는 짧은 명언이나 글귀 하나 자연스럽게 녹여줘. "
            "출처도 포함하고, 전체적으로 좀 길어도 괜찮아."
        )
        await channel.send(msg)

    @tasks.loop(time=NIGHT_TIME)
    async def night_greeting(self):
        channel = self.get_channel()
        if not channel:
            return
        msg = await ask_ai(
            "밤이야. 건우한테 잘자 인사 해줘. "
            "하루 마무리하는 느낌으로, 마지막에 오늘 하루를 돌아볼 수 있는 명언이나 글귀 하나 붙여줘. "
            "명언은 출처 포함해서, 짧은 설명도 살짝 덧붙여줘. 전체적으로 좀 길어도 괜찮아."
        )
        await channel.send(msg)

    @morning_greeting.before_loop
    @night_greeting.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Greeting(bot))
