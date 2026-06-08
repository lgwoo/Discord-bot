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
- `members.json` (repo root) maps Discord usernames → real Korean names. `resolve_name()` in `qa.py` does the lookup. Falls back to raw username if not found.
- Username (`message.author.name`) is used for identity, NOT `display_name` — username is stable even when server nickname changes.

## Bot Persona

The bot is named **이건식** — AI companion/friend of 이건우, pretending to be a real human friend.

- Persona defined entirely in `system_prompt.txt`. Edit that file to change behavior, never the code.
- The bot is deployed in a small group chat (~8 members). All members are listed in `system_prompt.txt` under `## 톡방 멤버 목록`.
- Member username→realname mapping lives in `members.json`.

## Member Mapping (`members.json`)

Discord username → real name:
- `geonu7` → 이건우 (bot's "best friend", 소프트웨어공학과 22학번)
- `swoleyeopo`, `keomdohun` → 김도훈 (훈듀오, 기계공학과, respected senior)
- `moonjeonghoon` → 문정훈 (훈듀오, 한의학과, respected senior)
- `choski7250` → 최영준 (villain character in persona)
- `molayo_hul` → 심민보
- `choidhfhan` → 최용안
- `obae17065367`, `odonghun2922` → 오동훈 (two accounts)
- `seoki_1110` → 유인석

To add/update members: edit `members.json`. No code changes needed.

## Deployment

Deployed on **Railway** (currently on 30-day free trial, started ~2026-06-08).
- GitHub repo is connected to Railway — push to main branch triggers redeploy.
- Railway filesystem is ephemeral: any file written at runtime is lost on restart/redeploy.
- Persistent storage options considered but not yet implemented (Railway Volume needs Hobby plan $5/mo, Supabase free tier is alternative).

## Adding a new cog

1. Create `cogs/newcog.py` with a `setup(bot)` async function.
2. Add `await bot.load_extension("cogs.newcog")` in `bot.py`'s `main()`.

## Discord Developer Portal requirements

- **Message Content Intent** must be enabled (Bot tab → Privileged Gateway Intents).
- Bot invite scopes: `bot` + `applications.commands`.

## Model

Current model: `anthropic/claude-haiku-4.5` (set in `cogs/qa.py` `MODEL` constant). Other available models via Timely GPT: `openai/gpt-4o-mini`, `openai/gpt-4.1-mini`, `google/gemini-2.5-flash-lite`, etc.

## Known Limitations / Future Work

- **Persistent memory**: bot cannot currently learn and persist new info across Railway restarts. Options: Railway Volume (paid), Supabase (free external DB). User has decided to defer this.
- **Image generation**: not implemented. Would require a separate image generation API (Timely GPT support unclear, alternatives: DALL-E, Stability AI).
