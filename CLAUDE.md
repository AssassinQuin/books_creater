# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

百万字网文创作引擎 — AI-powered Chinese web novel writing system. Uses Claude Code skills + MCP (Model Context Protocol) for structured, long-form novel creation with anti-AI-writing patterns, ensemble casts, and dual-track plotting.

## Architecture

Three-layer data architecture:
- **novel-db MCP** (PostgreSQL): Structured data — world-building, characters, chapters, foreshadowing, timelines, dimensions. Server at `/Users/ganjie/skills/novel-db-mcp/server.py`, connects to `postgresql://localhost:5432/fcli`
- **Memory MCP**: Unstructured creative data — inspiration, writing experience, cross-project materials, anti-AI pattern blacklist
- **Git files**: Human-readable content — novel text, setting docs, review reports in `novels/{小说名}/`

### Skill System

Core skill: `.claude/skills/novel-writer/SKILL.md` — the complete writing engine with phase-based workflow (A→B→C→D layers). Reference docs in `.claude/skills/novel-writer/references/`.

## Workflow Phases

| Phase | Purpose | Trigger Keywords |
|-------|---------|-----------------|
| A1 | Project bootstrap | "头脑风暴"/"灵感" |
| A2 | World-building | "建世界观"/"设定" |
| A3 | Character design | "设计人物"/"人物卡" |
| B1 | Volume planning | "规划卷"/"大纲" |
| B2 | Chapter writing | "写第N章"/"继续写" |
| B3 | Review | "审阅"/"检查" |
| C1 | Platform publishing | "上架"/"发布" |
| C2 | Health diagnosis | "诊断"/"卡文" |
| C3 | Cascade updates | "改设定"/"调整" |
| D | Status/materials | "进度"/"加素材" |

Priority on conflict: C3 > B2 > others.

## Key Orchestration Tools

- `writing_start(novel_id, chapter_number)` — one-shot context injection before writing (chapter info + last 3 summaries + active characters + unrecycled foreshadowing + world settings + current volume plan)
- `writing_finish(chapter_id, ...)` — one-shot state update after writing (summary + events + foreshadowing + timeline + dimensions)
- `health_check(novel_id)` — one-shot diagnosis (foreshadowing backlog + side character activity + upgrade pacing + daily scene density + hidden plot progress + volume completion)

## Git Commit Convention

```
A1/A2/A3/B1/B3: {description}    # milestone commits
ch{N}: {标题}                      # chapter commits
更新: {description}                # other changes
```

## Content Output

Novel text goes to `novels/{小说名}/正文/第{NNN}章-{标题}.md`.

## MCP Configuration

Configured in `.mcp.json`. The `novel-db` MCP server is a Python process that must have PostgreSQL running locally on port 5432 with database `fcli`.
