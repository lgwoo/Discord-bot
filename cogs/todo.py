import json
import os

import discord
from discord import app_commands
from discord.ext import commands

_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "todos.json")


def _load() -> dict:
    os.makedirs(os.path.dirname(_DATA_FILE), exist_ok=True)
    if not os.path.exists(_DATA_FILE):
        return {}
    with open(_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    os.makedirs(os.path.dirname(_DATA_FILE), exist_ok=True)
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _user_todos(data: dict, user_id: int) -> list:
    return data.setdefault(str(user_id), [])


class Todo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(name="할일", description="할일 목록 관리")

    @group.command(name="추가", description="할일 추가")
    @app_commands.describe(내용="추가할 할일")
    async def add(self, interaction: discord.Interaction, 내용: str):
        data = _load()
        todos = _user_todos(data, interaction.user.id)
        todos.append({"text": 내용, "done": False})
        _save(data)
        await interaction.response.send_message(
            f"✅ 추가했어: **{내용}**", ephemeral=True
        )

    @group.command(name="목록", description="할일 목록 보기")
    async def list_todos(self, interaction: discord.Interaction):
        data = _load()
        todos = _user_todos(data, interaction.user.id)

        if not todos:
            await interaction.response.send_message("할일 없어 👍", ephemeral=True)
            return

        lines = []
        for i, item in enumerate(todos, 1):
            check = "✅" if item["done"] else "⬜"
            lines.append(f"{check} `{i}.` {item['text']}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @group.command(name="완료", description="할일 완료 처리")
    @app_commands.describe(번호="완료할 항목 번호")
    async def done(self, interaction: discord.Interaction, 번호: int):
        data = _load()
        todos = _user_todos(data, interaction.user.id)

        if 번호 < 1 or 번호 > len(todos):
            await interaction.response.send_message("번호 잘못됐어.", ephemeral=True)
            return

        todos[번호 - 1]["done"] = True
        _save(data)
        await interaction.response.send_message(
            f"✅ **{todos[번호 - 1]['text']}** 완료!", ephemeral=True
        )

    @group.command(name="삭제", description="할일 삭제")
    @app_commands.describe(번호="삭제할 항목 번호")
    async def delete(self, interaction: discord.Interaction, 번호: int):
        data = _load()
        todos = _user_todos(data, interaction.user.id)

        if 번호 < 1 or 번호 > len(todos):
            await interaction.response.send_message("번호 잘못됐어.", ephemeral=True)
            return

        removed = todos.pop(번호 - 1)
        _save(data)
        await interaction.response.send_message(
            f"🗑️ **{removed['text']}** 삭제했어.", ephemeral=True
        )

    @group.command(name="초기화", description="완료된 항목 전부 삭제")
    async def clear_done(self, interaction: discord.Interaction):
        data = _load()
        todos = _user_todos(data, interaction.user.id)
        before = len(todos)
        data[str(interaction.user.id)] = [t for t in todos if not t["done"]]
        _save(data)
        removed = before - len(data[str(interaction.user.id)])
        await interaction.response.send_message(
            f"🗑️ 완료된 항목 {removed}개 삭제했어.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Todo(bot))
