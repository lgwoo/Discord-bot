import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

LONG_BREAK_MIN = 15
TOTAL_ROUNDS = 4


class Session:
    def __init__(self, task: asyncio.Task, channel: discord.TextChannel):
        self.task = task
        self.channel = channel


class Pomodoro(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._sessions: dict[int, Session] = {}  # user_id → Session

    group = app_commands.Group(name="뽀모도로", description="뽀모도로 타이머")

    @group.command(name="시작", description="뽀모도로 타이머 시작")
    @app_commands.describe(공부시간="집중 시간 (분, 기본 25)", 휴식시간="휴식 시간 (분, 기본 5)")
    async def start(
        self,
        interaction: discord.Interaction,
        공부시간: int = 25,
        휴식시간: int = 5,
    ):
        user_id = interaction.user.id
        if user_id in self._sessions:
            await interaction.response.send_message(
                "이미 타이머 돌아가고 있어. `/뽀모도로 종료` 로 먼저 끝내.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🍅 뽀모도로 시작!\n"
            f"집중 {공부시간}분 → 휴식 {휴식시간}분, {TOTAL_ROUNDS}라운드.\n"
            f"끝내고 싶으면 `/뽀모도로 종료`."
        )

        task = asyncio.create_task(
            self._run(interaction.user, interaction.channel, 공부시간, 휴식시간)
        )
        self._sessions[user_id] = Session(task=task, channel=interaction.channel)

    @group.command(name="종료", description="뽀모도로 타이머 종료")
    async def stop(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        session = self._sessions.get(user_id)
        if not session:
            await interaction.response.send_message("돌아가는 타이머 없어.", ephemeral=True)
            return

        session.task.cancel()
        self._sessions.pop(user_id, None)
        await interaction.response.send_message("타이머 종료. 수고했어 👋")

    async def _run(
        self,
        user: discord.Member,
        channel: discord.TextChannel,
        work_min: int,
        break_min: int,
    ):
        try:
            for round_num in range(1, TOTAL_ROUNDS + 1):
                await channel.send(
                    f"{user.mention} 🍅 **{round_num}라운드** 시작! {work_min}분 집중해봐."
                )
                await asyncio.sleep(work_min * 60)

                if round_num < TOTAL_ROUNDS:
                    await channel.send(
                        f"{user.mention} ✅ {round_num}라운드 끝! {break_min}분 쉬어."
                    )
                    await asyncio.sleep(break_min * 60)
                else:
                    await channel.send(
                        f"{user.mention} 🎉 **4라운드 완주!** 오늘 진짜 수고했다.\n"
                        f"{LONG_BREAK_MIN}분 푹 쉬어."
                    )
                    await asyncio.sleep(LONG_BREAK_MIN * 60)
                    await channel.send(
                        f"{user.mention} 긴 휴식 끝! 더 할 거야? `/뽀모도로 시작`"
                    )
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("뽀모도로 _run 오류 (user=%s)", user.id)
        finally:
            self._sessions.pop(user.id, None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Pomodoro(bot))
