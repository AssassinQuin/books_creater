# Codemap: novel-db-mcp

## Responsibility

FastMCP 3.x server providing ~79 MCP tools for structured novel data management. SQLite (libsql) backend with WAL mode, thread-local connections, and automatic schema initialization. Serves as the authoritative data layer for the "百万字网文创作引擎" (million-word web novel writing engine).

## Directory Structure

```
novel-db-mcp/
├── server.py                      # Entry point. Imports all tool modules, runs mcp.run()
├── 001_init_schema.sql            # Original schema migration
├── 002_distillation_evolution.sql # Distillation table migration
├── 003_libsql_schema.sql          # Current canonical schema (all tables + indexes)
├── requirements.txt               # fastmcp, pyyaml, sentence-transformers
├── _explain_queries.py            # Query analysis utility
├── migrate_characters_from_files.py  # One-shot: file→DB character migration
├── migrate_volumes_from_files.py     # One-shot: file→DB volume migration
├── novel_db/
│   ├── __init__.py
│   ├── db.py                      # Core infrastructure (FastMCP instance, connection pool, query())
│   ├── resolvers.py               # Name→ID resolution layer
│   ├── errors.py                  # Exception hierarchy + mcp_tool decorator
│   ├── constraints.py             # Chapter validation engine (markdown + DB rules)
│   ├── hooks.py                   # Post-save hook system (edge sync, cache invalidation)
│   ├── sync.py                    # Hash-based DB↔file change detection
│   ├── sync_engine.py             # Template-driven bidirectional sync engine
│   ├── md_parser.py               # Markdown file parser for lorebook sync
│   ├── embedding.py               # TF-IDF / sentence-transformers semantic search
│   ├── prompts.py                 # Writing prompt builder + quality history extractor
│   ├── sql_utils.py               # SQL helper functions (build_update_sql, build_upsert_sql)
│   ├── tools_novel.py             # 4 tools — novel CRUD
│   ├── tools_world.py             # 10 tools — world settings + lorebook + engine loading
│   ├── tools_volume.py            # 4 tools — volume CRUD
│   ├── tools_character.py         # 20 tools — character lifecycle + relations + distillation
│   ├── tools_chapter.py           # 14 tools — chapter planning + context + scenes + timeline
│   ├── tools_writing.py           # 15 tools — writing pipeline + foreshadow + echo + rules
│   ├── tools_misc.py              # 9 tools — health + search + sync + skill loading
│   └── tools_graph.py             # 3 tools — graph traversal + cascade analysis
└── scripts/
    ├── migrate_clean_data.py      # Data cleanup migration
    ├── migrate_edges.py           # Entity edge migration
    └── migrate_embedding.py       # Embedding data migration
```

## Architecture

### Entry Point — [server.py](server.py)

Imports all `@mcp.tool`-decorated functions from the 8 tool modules and registers them with the FastMCP instance. Runs `mcp.run()` on `__main__`. No business logic — pure registration.

### Core Infrastructure — [novel_db/db.py](novel_db/db.py)

- **`mcp`**: `FastMCP("novel-db")` singleton — all tool modules import this and use `@mcp.tool`
- **`PROJECT_ROOT`**: Resolved from `NOVEL_PROJECT_ROOT` env var, defaults to 3 levels up from `db.py`
- **`LIBSQL_DB_PATH`**: Resolved from `LIBSQL_DB_PATH` env var, defaults to `{PROJECT_ROOT}/data/novel.db`
- **`_local`**: `threading.local()` for thread-local SQLite connections
- **`_init_db_schema(conn)`**: Auto-creates all tables by executing `003_libsql_schema.sql` on first connection (guarded by `_db_initialized` flag)
- **`get_conn()`**: Returns thread-local connection with `WAL` mode, `busy_timeout=5000ms`, `foreign_keys=ON`
- **`query(sql, params, fetch)`**: Unified query function with 5 fetch modes:
  - `"all"` → list of `sqlite3.Row`
  - `"one"` → single `sqlite3.Row` or `None`
  - `"val"` → single scalar value
  - `"insert"` → dict with `{"id": lastrowid}`
  - `"none"` → no return (for UPDATE/DELETE)
- **`transaction()`**: Context manager wrapping `BEGIN`/`COMMIT`/`ROLLBACK`
- **`get_novel_config(novel_id, config_type, name)`**: JSON config lookup from `novel_config` table

### Name Resolution — [novel_db/resolvers.py](novel_db/resolvers.py)

Converts human-readable names to DB IDs so all MCP tools accept names instead of IDs:

- **`_resolve_novel_id(novel_name_or_id)`**: Accepts `int`, numeric string, or novel name → queries `novels` table → returns `int`. Raises `NotFoundError` on miss.
- **`_resolve_chapter_id(novel_name, chapter_number)`**: Resolves novel first, then queries `chapters` by `(novel_id, number)`. Raises `NotFoundError`.
- **`_get_novel_name(novel_id)`**: Reverse lookup for edge sync display.

### Error Handling — [novel_db/errors.py](novel_db/errors.py)

- **`NovelDBError`** → base exception
  - **`NotFoundError`** → entity not found (novel/chapter/character)
  - **`ValidationError`** → constraint violation
  - **`ConflictError`** → state conflict (e.g., duplicate)
- **`mcp_tool(func)`**: Decorator that catches `NovelDBError` subclasses and returns `json.dumps({"error": ...})` instead of raising. Preserves `__name__` and `__doc__`.

### Validation Engine — [novel_db/constraints.py](novel_db/constraints.py)

Two-layer validation system:

1. **Markdown constraints** (`writing-constraints.md`): Parsed by `_parse_constraints_md()` into:
   - `hard_pct` — percentage density rules (e.g., negation ≤ 0.3%)
   - `hard_abs` — absolute count rules (e.g., em-dash ≥ 8/chapter)
   - `banned_patterns` — regex patterns that must not appear
   - `guidelines` — soft rules with descriptions

2. **DB-stored rules** (`writing_rules` table): Data-driven rule engine with 6 rule types:
   - `keyword_ban` — forbidden words/phrases
   - `keyword_limit` — count thresholds (min/max)
   - `pattern_match` — regex pattern detection
   - `term_replace` — incorrect→correct term mapping
   - `absence_check` — required elements that must be present
   - `co_occurrence` — proximity-based co-occurrence checks

- **`validate_chapter_text(text)`**: Runs markdown-based checks, returns violations + stats
- **`validate_with_db_rules(text, novel_id)`**: Runs DB-stored rules, returns `db_violations`
- **`_enrichment_level(word_count, target)`**: Returns L1/L2/L3 enrichment directives when word count is insufficient

### Post-Save Hooks — [novel_db/hooks.py](novel_db/hooks.py)

Fires after every entity save operation:

1. **`_sync_edges_hook`**: Calls `tools_graph._sync_edges()` to update `entity_edges` table
2. **`_invalidate_embedding_hook`**: Calls `embedding.invalidate_cache()` to clear TF-IDF cache for the novel

- **`fire_post_save(novel_id, entity_type, entity_id)`**: Iterates `_HOOKS` list, collects failures, logs errors but does not abort

### Sync System — [novel_db/sync.py](novel_db/sync.py) + [novel_db/sync_engine.py](novel_db/sync_engine.py)

**sync.py** — Hash-based change detection:
- **`_compute_hash(data)`**: SHA-256 hashing for DB rows and file contents
- **`data_hashes` table**: Tracks `(novel_id, data_type, data_key, db_hash, file_hash)` for incremental sync
- **`_record_db_hash()` / `_record_file_hash()`**: Update hash records after sync operations
- **`_db_row_to_hashable()`**: Converts `sqlite3.Row` to deterministic hash input

**sync_engine.py** — Template-driven bidirectional sync:
- Entity types: `world`, `character`, `foreshadow`, `volume`, `echo`
- **`engine.db_to_files(novel_name, entity_type, entity_key?)`**: DB→file sync using templates
- **`engine.files_to_db(novel_name, entity_type)`**: File→DB sync using `md_parser`
- **`engine.diff(novel_name, entity_type)`**: Bidirectional comparison report
- **`engine.load_manifests(directory)`**: YAML manifest auto-registration for zero-code entity type extension
- **`engine.register(template)`**: Manual template registration

### Markdown Parser — [novel_db/md_parser.py](novel_db/md_parser.py)

Reverse operation of sync_engine's renderer. Parses Markdown files back into structured data for File→DB sync:
- **`split_sections(md_text)`**: Splits by `##` headings (H2 level only; H3 treated as sub-structure)
- Section-type-specific parsers for each entity type
- Lenient parsing: extracts usable data even from non-strict template formats
- Round-trip safe: JSONB fields maintain nested structure after DB→File→DB cycle

### Semantic Search — [novel_db/embedding.py](novel_db/embedding.py)

Dual-mode search with graceful fallback:
- **Primary**: `sentence-transformers` model (`paraphrase-multilingual-MiniLM-L12-v2`, overridable via `EMBEDDING_MODEL` env var)
- **Fallback**: TF-IDF based search (zero external dependency) — used when `sentence-transformers` is not installed
- **`get_engine_for_novel(novel_id)`**: Returns search engine instance for the novel
- **`invalidate_cache(novel_id)`**: Clears cached vectors/indexes (called by post-save hook)
- Lazy imports: `numpy`/`sentence-transformers` loaded only on first use; MCP starts regardless

### Prompt Builder — [novel_db/prompts.py](novel_db/prompts.py)

- **`_build_event_checklist(chapter)`**: Parses chapter outline into numbered checklist items (splits on `→`, `|`, `；`)
- **`_build_character_detail_card(char, relations)`**: Generates compact character card for context loading
- Quality history extraction for chapter context aggregation

### SQL Utilities — [novel_db/sql_utils.py](novel_db/sql_utils.py)

- **`build_update_sql(table, fields_dict, where_clause, where_params)`**: Generates `UPDATE ... SET col=? ... WHERE ...` with auto `updated_at`
- **`build_upsert_sql(table, insert_cols, update_cols, insert_params, update_params)`**: Generates `INSERT ... ON CONFLICT(...) DO UPDATE SET ...` with auto `updated_at`

## Tool Modules

### tools_novel.py — 4 tools

| Tool | Purpose |
|------|---------|
| `novel_create` | Create new novel project |
| `novel_list` | List all novels |
| `novel_get` | Get novel details by name |
| `novel_update` | Update novel metadata |

### tools_world.py — 10 tools

| Tool | Purpose |
|------|---------|
| `world_upsert` | Insert or update world setting entry (upsert by `novel_id+category+name`) |
| `world_query` | Query world settings with filters (category/name/region/volume/faction/tags) |
| `world_load_context` | Layered context loading with volume/region/faction/category filters |
| `world_batch_update_meta` | Bulk update metadata (region/volume_range/faction_id/priority/is_constant) |
| `world_delete` | Delete world setting entry |
| `world_deactivate` | Irreversible deactivation (location destroyed, faction dissolved, etc.) |
| `sync_lorebook` | Sync from `设定/世界观/` MD files to DB |
| `engine_detail` | Load writing engine reference from `world_settings` |
| `author_voice` | Load author voice dimensions from `world_settings(category='author_voice')` |
| `writing_spec` | Load writing execution spec from `world_settings(category='writing_spec')` |

Key helpers: `_parse_volume_number()`, `_volume_in_range()` for volume-range matching in layered context loading.

### tools_volume.py — 4 tools

| Tool | Purpose |
|------|---------|
| `volume_create` | Create volume with rich narrative structure fields |
| `volume_list` | List volumes for a novel |
| `volume_get` | Get volume details (causal_chain, four-act structure, character_arcs, etc.) |
| `volume_update` | Update volume fields |

Volume data fields: `causal_chain`, `act_intro/rise/twist/resolution` (起承转合), `character_arcs`, `interaction_matrix`, `boundaries`, `suspense_anchors`, `key_dialogues`, `writing_priorities`, `hard_constraints`, `info_pacing`, `rhythm_allocation`, `world_state`.

### tools_character.py — 20 tools

| Tool | Purpose |
|------|---------|
| `character_create` | Create character with full profile fields |
| `character_list` | List characters (optional role filter) |
| `character_get` | Get character by name |
| `character_detail` | Get distillation card by name (with optional chapter_number) |
| `character_update` | Update character fields by name |
| `character_snapshot` | Save character state snapshot at chapter |
| `character_get_latest` | Get latest state snapshot by name |
| `character_increment` | Increment numeric fields (chapter_appearances, etc.) |
| `relation_create` | Create character relation by names |
| `relation_list` | List all relations |
| `relation_update` | Update relation by names |
| `relation_snapshot` | Save relation state snapshot at chapter |
| `plot_thread_create` | Create plot thread (mainline/subplot/hidden) |
| `plot_thread_list` | List plot threads (optional type filter) |
| `plot_thread_update` | Update plot thread status |
| `character_batch_detail` | Batch fetch multiple character profiles (avoids N calls) |
| `distillation_evolve` | Record character distillation evolution at chapter |
| `distillation_get` | Get distillation record (specific chapter or all) |
| `distillation_timeline` | Get distillation timeline for a dimension |
| `distillation_compare` | Compare distillation between two chapters |

Internal helpers: `_character_update_by_id()`, `_character_get_by_id()`, `_character_detail_by_id()`, `_relation_create_by_id()`, `_character_snapshot_by_id()`, `_relation_snapshot_by_id()`.

### tools_chapter.py — 14 tools

| Tool | Purpose |
|------|---------|
| `chapter_plan` | Plan chapter (upsert by `novel_id+number`) |
| `chapter_list` | List chapters (optional status filter) |
| `chapter_save_summary` | Save chapter summary (upsert) |
| `get_chapter_context` | **v2 aggregated context** with 4 load modes (smart/volume/targeted/full) |
| `scene_create` | Create scene outline |
| `scene_list` | List scenes for chapter |
| `scene_update` | Update scene outline |
| `scene_delete` | Delete scene outline |
| `dimension_log` | Log dimension change |
| `dimension_query` | Query dimension changes by range |
| `timeline_add` | Add timeline event |
| `timeline_query` | Query timeline events by chapter range |
| `timeline_update` | Update timeline event |
| `timeline_delete` | Delete timeline event |

**`get_chapter_context`** is the primary context aggregation tool. Load modes:
- `smart` — auto-selects based on chapter position (early=full, mid=volume, late=targeted)
- `volume` — loads current volume's world settings
- `targeted` — loads only specified regions/factions/categories
- `full` — loads everything

Returns: chapter info + volume outline + prev 3 chapter summaries + character cards + foreshadows + world settings + timeline + quality history + writing prompt + event checklist.

Internal helpers: `_save_chapter_summary_internal()` (shared by `chapter_save_summary` and `writing_finish`), `_extract_decay_state()`, `_load_volume_context_map()`, `_load_world_context()`.

### tools_writing.py — 15 tools

| Tool | Purpose |
|------|---------|
| `writing_finish` | **4-step pipeline**: validate → save summary → post-save (foreshadow recall + timeline) → quality stats |
| `validate_chapter` | Run all constraint checks (markdown + DB rules), return violations + stats + enrichment |
| `rule_detail` | Get writing rule full description from `writing-constraints.md` |
| `record_new_content` | Record new entity (setting/item/location/npc/faction) discovered during writing |
| `event_checklist` | Generate chapter event checklist from outline |
| `foreshadow_plant` | Plant a foreshadow (clue_type: foreshadow/echo/callback) |
| `foreshadow_recall` | Recall/resolve a foreshadow |
| `foreshadow_list` | List foreshadows (status filter: planted/recalled/abandoned) |
| `foreshadow_update` | Update foreshadow fields |
| `echo_create` | Create echo record (event aftermath callback) |
| `echo_list` | List echoes (filter by volume/chapter) |
| `echo_density_check` | Check echo density per volume (normal≤2/vol, strong unlimited, cross-vol≤1/interval) |
| `resolve_engines` | Map scene AES types to engine file contents (hardcoded `ENGINE_MATRIX`) |
| `writing_rule_upsert` | Create/update DB-stored writing rule |
| `writing_rule_list` | List DB-stored writing rules (category filter) |

**`writing_finish`** pipeline (4 steps):
1. `_wf_validate()` — hard constraint validation + DB rule validation + self_check gate
2. `_wf_save_summary()` — upsert chapter summary with events/characters/foreshadows
3. `_wf_post_save()` — foreshadow recall processing + timeline event creation
4. `_wf_quality()` — save quality stats to `chapter_quality` table

**`resolve_engines`** uses `ENGINE_MATRIX` mapping: scene AES types → lists of engine filenames from `.claude/skills/engines/`.

### tools_misc.py — 9 tools

| Tool | Purpose |
|------|---------|
| `health_check` | Diagnostic: foreshadow backlog, side-character activity, upgrade pacing, daily density, hidden-line progress, volume completion |
| `skill_loader` | 3-level priority loading: project overrides > skill-specific > global shared |
| `db_search` | Keyword search across world/character/chapter/foreshadow tables |
| `engine_list` | List available writing engine files with title + summary |
| `sync_startup` | Startup bidirectional DB↔file diff, returns conflict report |
| `sync_db_to_files` | DB→file sync (optional data_type filter, overwrite flag) |
| `sync_files_to_db` | File→DB sync (structured parsing via md_parser) |
| `sync_roundtrip` | Bidirectional round-trip verification (File→DB→File) |
| `semantic_search` | TF-IDF / sentence-transformers semantic search |

### tools_graph.py — 3 tools

| Tool | Purpose |
|------|---------|
| `graph_query` | Recursive CTE traversal from seed entity, configurable depth and edge_type filter |
| `graph_neighbors` | Single-hop neighbors for an entity |
| `graph_cascade` | Impact analysis: what entities are affected by a change to the seed |

Entity edge auto-sync: `_sync_edges(novel_id, entity_type, entity_id)` is called by the post-save hook system. Maintains `entity_edges` table with `(from_type, from_id, to_type, to_id, edge_type, weight)` tuples.

Entity type map: `world_setting` → `world_settings`, `character` → `characters`, `chapter` → `chapters`, `foreshadow` → `foreshadows`, `echo` → `echoes`.

## Database Schema

17 tables defined in [003_libsql_schema.sql](003_libsql_schema.sql):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `novels` | Novel projects | name, genre, status, current_chapter |
| `volumes` | Volume outlines | 4-act structure (起承转合), character_arcs, interaction_matrix, world_state |
| `chapters` | Chapter metadata | number, title, outline, chapter_type, status |
| `characters` | Character profiles | 20+ fields including appearance_detail, decision_engine, voice_fingerprint, ability_system, behavior_pattern, growth_trajectory |
| `character_relations` | Character relationships | from/to IDs, relation_type, intensity, dialogue_adjustment, micro_expressions, subtext_design |
| `character_state_snapshots` | Per-chapter character state | location, arc_phase, emotional/physical_state, ability/inventory/knowledge snapshots |
| `relation_state_snapshots` | Per-chapter relation state | intensity, status, notes |
| `character_distillation_evolution` | Distillation records | decision_delta, new_knowledge, changed_beliefs, relation_shifts, voice/ability/arc changes |
| `world_settings` | World building entries | category, name, data (JSONB), volume_range, region, faction_id, priority, is_constant |
| `chapter_summaries` | Chapter summaries | summary, key_events, characters_involved, foreshadow tracking |
| `foreshadows` | Foreshadowing | planted/recall chapter IDs, importance, clue_type, reveal_strategy |
| `echoes` | Event echoes | source/echo chapter IDs, echo_type, strong_related flag |
| `timeline_events` | Timeline tracking | event_time, event_order, significance |
| `scene_outlines` | Scene outlines | scene_number, location, conflict, emotion_type, key_beats |
| `dimension_changes` | State change log | dimension, change_type, before/after values |
| `chapter_quality` | Quality metrics | punctuation counts, negation count, word count, violations, passed flag |
| `novel_config` | JSON config storage | config_type, name, data |
| `writing_rules` | Data-driven rules | rule_type (6 types), category, pattern, thresholds, scope, severity |
| `entity_edges` | Relationship graph | from/to type+id, edge_type, weight |
| `data_hashes` | Sync tracking | data_type, data_key, db_hash, file_hash |

## Data Flow

### Read Path

```
MCP tool call
  → resolver (name→ID)
  → query(sql, params, fetch_mode)
  → SQLite (WAL mode, thread-local connection)
  → return JSON
```

### Write Path

```
MCP tool call
  → resolver (name→ID)
  → query() or transaction()
  → SQLite write
  → fire_post_save(novel_id, entity_type, entity_id)
    → _sync_edges_hook: update entity_edges graph
    → _invalidate_embedding_hook: clear TF-IDF/vector cache
  → return JSON
```

### Chapter Writing Pipeline (writing_finish)

```
writing_finish(novel_name, chapter_number, summary, chapter_text, ...)
  │
  ├─ Step 1: _wf_validate()
  │   ├─ validate_chapter_text() — markdown constraints
  │   ├─ validate_with_db_rules() — DB-stored rules
  │   └─ self_check gate — 'passed' required
  │
  ├─ Step 2: _wf_save_summary()
  │   └─ Upsert chapter_summaries + update chapter status
  │
  ├─ Step 3: _wf_post_save()
  │   ├─ Process resolved_foreshadows → foreshadow_recall
  │   └─ Process timeline_events → timeline_add
  │
  └─ Step 4: _wf_quality()
      └─ Insert chapter_quality record with validation stats
```

### Context Aggregation (get_chapter_context)

```
get_chapter_context(novel_name, chapter_number, load_mode)
  │
  ├─ Chapter info (chapters table)
  ├─ Volume outline (volumes table)
  ├─ Previous 3 chapter summaries
  ├─ Character detail cards (characters + relations + snapshots)
  ├─ Active foreshadows (foreshadows table)
  ├─ World settings (layered by volume/region/faction/category)
  ├─ Timeline events (chapter range)
  ├─ Quality history (chapter_quality table)
  ├─ Writing prompt (from prompts.py)
  └─ Event checklist (from prompts.py)
```

## Design Patterns

| Pattern | Implementation |
|---------|---------------|
| **Name-based API** | All tools accept `novel_name` + entity names; `_resolve_novel_id()` / `_resolve_chapter_id()` convert to IDs internally |
| **Upsert** | `INSERT ... ON CONFLICT DO UPDATE` for idempotent operations (chapters, summaries, world settings, writing rules) |
| **Post-save hooks** | `fire_post_save()` runs registered hooks after entity writes — decouples cross-cutting concerns |
| **Layered loading** | `get_chapter_context` smart mode auto-selects context depth; `world_load_context` supports volume/region/faction/category filters |
| **Data-driven validation** | `writing_rules` DB table stores rule definitions; `constraints.py` parses markdown + DB rules; zero code changes to add new rules |
| **Template-driven sync** | `sync_engine.py` uses entity-type templates; YAML manifests enable zero-code extension |
| **Lazy imports** | `embedding.py` defers numpy/sentence-transformers import; MCP starts even without ML dependencies |
| **Thread-local connections** | Each thread gets its own SQLite connection via `threading.local()` |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastmcp` | ≥0.1.0 | MCP server framework |
| `pyyaml` | ≥6.0 | YAML manifest parsing for sync engine |
| `sentence-transformers` | ≥2.2.0 | Semantic search (optional, graceful fallback to TF-IDF) |
| `sqlite3` | stdlib | Database backend (WAL mode, busy_timeout=5000ms) |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NOVEL_PROJECT_ROOT` | 3 levels up from `db.py` | Project root directory |
| `LIBSQL_DB_PATH` | `{ROOT}/data/novel.db` | SQLite database file path |
| `CONSTRAINTS_FILE` | `{ROOT}/.claude/skills/engines/writing-constraints.md` | Markdown constraint rules file |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence-transformers model name |
