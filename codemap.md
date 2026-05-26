# Repository Atlas: books_creater

## Project Responsibility
AI-powered Chinese web novel creation engine — structured, long-form novel writing system using Claude Code skills + MCP. Produces 百万字级 (million-character) web novels with anti-AI writing patterns, ensemble casts, dual-track plotting, and data-driven quality validation.

Current project: **《这次不一样了》** — 14 volumes + epilogue, 玄幻 (fantasy) genre.

## System Entry Points
- `novel-db-mcp/server.py`: MCP server entry point. FastMCP 3.x + SQLite. ~79 registered tools.
- `CLAUDE.md`: Project-level instructions, conventions, and workflow rules. Auto-loaded by Claude Code.
- `NOVEL-CONTEXT.md`: Core terminology definitions. Authoritative source for all domain terms.
- `SENTENCE-PATTERNS.md`: Anti-AI sentence pattern system (6 fingerprint types + solutions).
- `.mcp.json.example`: MCP server configuration template.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Claude Code Agent                  │
│  (loads CLAUDE.md + skills + calls MCP tools)        │
├──────────────┬──────────────────────────────────────┤
│  Skill Layer │  MCP Tool Layer                       │
│  (.claude/   │  (novel-db-mcp/)                      │
│   skills/)   │                                       │
│              │  ┌─────────────────────────────────┐  │
│  17 skills   │  │ FastMCP Server (server.py)      │  │
│  38 engines  │  │ ├── tools_novel (4 tools)       │  │
│  8 phases    │  │ ├── tools_world (10 tools)      │  │
│  5 protocols │  │ ├── tools_volume (4 tools)      │  │
│  6 templates │  │ ├── tools_character (20 tools)  │  │
│              │  │ ├── tools_chapter (14 tools)    │  │
│              │  │ ├── tools_writing (15 tools)    │  │
│              │  │ ├── tools_misc (9 tools)        │  │
│              │  │ └── tools_graph (3 tools)       │  │
│              │  └────────────┬────────────────────┘  │
│              │               │                        │
│              │         ┌─────▼─────┐                  │
│              │         │  SQLite   │  data/novel.db   │
│              │         │  (libsql) │  WAL mode        │
│              │         └─────┬─────┘                  │
│              │               │                        │
│              │     sync_db_to_files() │ sync_files_to_db()│
│              │               │                        │
│              │         ┌─────▼─────┐                  │
│              │         │  novels/  │  Human-readable  │
│              │         │  设定/     │  markdown files  │
│              │         │  正文/     │  (secondary)     │
│              │         └───────────┘                  │
└──────────────┴──────────────────────────────────────┘
```

## Data Architecture

Three-layer data architecture with DB as authority:

| Layer | Technology | Role | Write Rule |
|-------|-----------|------|-----------|
| **Structured Data** | SQLite (libsql) via MCP | Authority source for all entities | MCP tools only |
| **Unstructured Creative** | Memory MCP (16 tools) | Inspirations, writing experience, anti-AI blacklist | Memory skill required |
| **Human-Readable** | Git markdown files | Novel text, settings docs, review reports | Files = secondary copies |

**Data flow**: `skill → MCP tool → DB (direct write) → sync_db_to_files() → files (human-readable copy)`

## Directory Map (Aggregated)

| Directory | Responsibility Summary | Detailed Map |
|-----------|----------------------|--------------|
| `novel-db-mcp/` | FastMCP server providing ~79 tools for novel data management. SQLite backend with WAL mode, thread-local connections, name-based API, hook system, graph traversal, and data-driven validation. | [View Map](novel-db-mcp/codemap.md) |
| `.claude/skills/` | 17 specialized skills for the novel writing workflow (setup → character → planner → chapter-writer → qa → reviser), 38 writing engines, 8 phase definitions, 5 shared protocols, 6 templates. | [View Map](.claude/skills/codemap.md) |
| `novels/这次不一样了/` | Novel content: 28 character profiles, 200+ world settings, 53 foreshadows, 15 volume outlines, 8 creative blueprints, 14 text fragments. Not code — markdown content files. | — |

## Key Workflows

### Chapter Writing Pipeline (v2)
```
novel-chapter-writer (orchestrator)
  │  Step 1: get_chapter_context(MCP) → ~36KB context bundle
  ↓
  Step 2: Creative decisions → blueprint + save
  ↓  🔒 Checkpoint A
  Step 3: resolve_engines(MCP) → engine instructions
  ↓
  Step 4: Scene-by-scene generation + self-check
  ↓  🔒 Checkpoint B
  Step 5: validate_chapter → writing_finish → persist
```

### Writing Finish Pipeline (4 steps)
1. **_wf_validate**: Hard constraint validation + DB rule validation + self-check gate
2. **_wf_save_summary**: Save chapter summary + update status to 'written'
3. **_wf_post_save**: Foreshadow recall + timeline event indexing
4. **_wf_quality**: Quality statistics (punctuation density, negation count, etc.)

### Validation System
- **Static rules**: Parsed from `writing-constraints.md` (hard_pct, hard_abs, banned_patterns, guidelines)
- **Dynamic rules**: Stored in `writing_rules` DB table (6 rule types: keyword_ban, keyword_limit, pattern_match, term_replace, absence_check, co_occurrence)
- **Enrichment**: 3-level escalation when word count is insufficient (L1: engine enrich, L2: scene deepen, L3: add events)

## Cross-Module Integration Points

| From | To | Integration |
|------|----|-------------|
| Skills | MCP tools | Skills call MCP tools for all data operations |
| tools_writing | tools_graph | Post-save hooks trigger edge sync |
| tools_writing | constraints.py | validate_chapter uses both static + dynamic rules |
| tools_chapter | tools_world | get_chapter_context calls world_load_context |
| tools_misc | sync_engine.py | sync_db_to_files / sync_files_to_db |
| tools_graph | hooks.py | Edge auto-sync on entity save |
| engines/*.md | tools_writing | resolve_engines reads engine files by scene type |

## Current Project Status (2026-05-26)
- 15 volumes (含尾声) outlined, Phase3 validated (90/100)
- V1 Ch001-009 deep audit completed
- 28 characters, 200+ world settings, 53 foreshadows in DB
- Next: Chapter writing (B2), starting from V1
