# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the bot

```bash
python bot.py
```

Requires a `.env` file (copy `.env.example`):
```
DISCORD_TOKEN=...
TIMELYGPT_API_KEY=...
```

## Architecture

Single-cog Discord bot. Entry point is `bot.py`; all Q&A logic lives in `cogs/qa.py`.

**Flow:** user mentions bot (user mention or role mention) or uses `/질문` slash command → `cogs/qa.py` strips the mention tag → calls Timely GPT API (OpenAI-compatible, `https://hello.timelygpt.co.kr/api/v2/chat/bridge/openai`) via `openai.AsyncOpenAI` → replies. Responses over 2000 chars are split.

**Key design decisions:**
- `AsyncOpenAI` client is lazily initialized (`get_client()`) to avoid creating it outside the asyncio event loop.
- `system_prompt.txt` (repo root) is read on every request — edit it to change the bot's persona without touching code.
- Role mention detection handles Discord bots that get mentioned via their managed role instead of their user ID.
- Slash command uses `await interaction.response.defer()` to avoid the 3-second Discord timeout.

## Adding a new cog

1. Create `cogs/newcog.py` with a `setup(bot)` async function.
2. Add `await bot.load_extension("cogs.newcog")` in `bot.py`'s `main()`.

## Discord Developer Portal requirements

- **Message Content Intent** must be enabled (Bot tab → Privileged Gateway Intents).
- Bot invite scopes: `bot` + `applications.commands`.

## Model

Current model: `anthropic/claude-haiku-4.5` (set in `cogs/qa.py` `MODEL` constant). Other available models via Timely GPT: `openai/gpt-4o-mini`, `openai/gpt-4.1-mini`, `google/gemini-2.5-flash-lite`, etc.
