# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

百万字网文创作引擎 — AI-powered Chinese web novel writing system. Uses Claude Code skills + MCP (Model Context Protocol) for structured, long-form novel creation with anti-AI-writing patterns, ensemble casts, and dual-track plotting.

Current project: **《这次不一样了》** — 14卷+尾声, 百万字级玄幻网文. Novel DB id: 1.

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

## File Organization Rules

- **大纲 (`设定/大纲/`)**: 卷级写作指导, 1-2行场景梗概. 不写详情(心理描写/对话/关系磨合细节)
- **设定文件**: 详情内容写在 `角色深化.md` / `世界观.md` / `地图.md` / `线索追踪.md` 等
- **大纲中使用指针**: 引用详情时写 `→见角色深化·关系成长路径` 而不是复制内容
- **灵感库 (`设定/灵感库/`)**: 只放调研、头脑风暴、可复用方法论. 不放审计报告
- **审阅报告 (`审阅报告/`)**: 审计发现、问题清单、修复方案
- **单源维护**: 同一内容(伏笔/线索/关系/设定)只在主文件描述完整, 其他文件用指针引用

## Current Project Status (2026-05-10)

- 14卷+尾声大纲完成, Phase3验证通过(综合90/100)
- 10维度达尔文评估→R1-R5女娲修复→Phase3验证全流程完成
- 审阅报告存于 `审阅报告/大纲审查-Phase2修复-2026-05-09/`
- novel-db数据库已同步(15卷/15章/21伏笔/4时间线事件)
- 残留4条P3轻微问题(不影响正文): 鸦成长中间节点/F8伏笔/V3爽感/V4练习场
- 下一步: 正文生成(B2), 从V1开始

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
