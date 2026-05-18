-- Novel DB Schema for libSQL/SQLite
-- Run: sqlite3 data/novel.db < 003_libsql_schema.sql
-- Or via Python: conn.executescript(open('003_libsql_schema.sql').read())

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ─── Core ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS novels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    genre TEXT DEFAULT '',
    target_platform TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    status TEXT DEFAULT 'brainstorming',
    current_chapter INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Volumes ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title TEXT DEFAULT '',
    main_plotlines TEXT DEFAULT '[]',  -- JSON stored as TEXT
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(novel_id, number)
);

-- ─── Chapters ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title TEXT DEFAULT '',
    outline TEXT DEFAULT '',
    chapter_type TEXT DEFAULT 'normal',
    volume_id INTEGER REFERENCES volumes(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(novel_id, number)
);

-- ─── Characters ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'npc',
    faction_id INTEGER DEFAULT NULL,
    race TEXT DEFAULT '',
    ability_level TEXT DEFAULT '',
    status TEXT DEFAULT '{}',
    appearance TEXT DEFAULT '',
    personality TEXT DEFAULT '',
    background TEXT DEFAULT '',
    goals TEXT DEFAULT '',
    weaknesses TEXT DEFAULT '',
    speech_style TEXT DEFAULT '',
    catchphrase TEXT DEFAULT '',
    arc_notes TEXT DEFAULT '',
    first_appearance_chapter INTEGER DEFAULT NULL,
    is_active INTEGER DEFAULT 1,  -- BOOLEAN as INTEGER
    appearance_detail TEXT DEFAULT '{}',
    decision_engine TEXT DEFAULT '{}',
    voice_fingerprint TEXT DEFAULT '{}',
    ability_system TEXT DEFAULT '{}',
    behavior_pattern TEXT DEFAULT '{}',
    current_snapshot TEXT DEFAULT '{}',
    growth_trajectory TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Character Relations ───────────────────────────────
CREATE TABLE IF NOT EXISTS character_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    from_character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    to_character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    chapter_established INTEGER DEFAULT NULL,
    intensity INTEGER DEFAULT 5,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Character State Snapshots ─────────────────────────
CREATE TABLE IF NOT EXISTS character_state_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    snapshot_data TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(character_id, chapter_id)
);

-- ─── Character Distillation Evolution ──────────────────
CREATE TABLE IF NOT EXISTS character_distillation_evolution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    decision_delta TEXT DEFAULT '[]',
    new_knowledge TEXT DEFAULT '[]',
    changed_beliefs TEXT DEFAULT '[]',
    relation_shifts TEXT DEFAULT '[]',
    voice_changes TEXT DEFAULT '{}',
    ability_changes TEXT DEFAULT '{}',
    arc_transition TEXT DEFAULT '{}',
    key_decision TEXT DEFAULT '{}',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── World Settings ────────────────────────────────────
CREATE TABLE IF NOT EXISTS world_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    data TEXT DEFAULT '{}',
    keys TEXT DEFAULT '[]',
    secondary_keys TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    related_ids TEXT DEFAULT '[]',
    volume_range TEXT DEFAULT '',
    region TEXT DEFAULT '全域',
    faction_id INTEGER DEFAULT NULL,
    writing_guide TEXT DEFAULT '',
    lorebook_id TEXT DEFAULT '',
    priority INTEGER DEFAULT 30,
    is_constant INTEGER DEFAULT 0,  -- BOOLEAN as INTEGER
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(novel_id, category, name)
);

-- ─── Chapter Summaries ─────────────────────────────────
CREATE TABLE IF NOT EXISTS chapter_summaries (
    chapter_id INTEGER PRIMARY KEY REFERENCES chapters(id) ON DELETE CASCADE,
    summary TEXT DEFAULT '',
    key_events TEXT DEFAULT '[]',
    characters_involved TEXT DEFAULT '[]',
    new_foreshadows TEXT DEFAULT '[]',
    resolved_foreshadows TEXT DEFAULT '[]',
    dimension_snapshot TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Foreshadows ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS foreshadows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    planted_chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    planned_recall_chapter INTEGER DEFAULT NULL,
    actual_recall_chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    importance TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'planted',
    related_characters TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clue_type TEXT DEFAULT 'foreshadow',
    reveal_strategy TEXT DEFAULT 'gradual',
    related_foreshadows TEXT DEFAULT '[]'
);

-- ─── Timeline ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    event_time TEXT DEFAULT '',
    event_order INTEGER DEFAULT 0,
    event_description TEXT NOT NULL,
    characters_involved TEXT DEFAULT '[]',
    location_id INTEGER DEFAULT NULL,
    significance TEXT DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Scene Outlines ────────────────────────────────────
CREATE TABLE IF NOT EXISTS scene_outlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    scene_number INTEGER NOT NULL,
    location TEXT DEFAULT '',
    characters_involved TEXT DEFAULT '[]',
    conflict TEXT DEFAULT '',
    emotion_type TEXT DEFAULT '',
    key_beats TEXT DEFAULT '[]',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chapter_id, scene_number)
);

-- ─── Dimension Changes ─────────────────────────────────
CREATE TABLE IF NOT EXISTS dimension_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,
    change_type TEXT DEFAULT '',
    entity_name TEXT DEFAULT '',
    before_value TEXT DEFAULT '{}',
    after_value TEXT DEFAULT '{}',
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════
-- Chapter Quality (Phase 1)
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS chapter_quality (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    em_dash_count INTEGER DEFAULT 0,
    ellipsis_count INTEGER DEFAULT 0,
    semicolon_count INTEGER DEFAULT 0,
    exclamation_count INTEGER DEFAULT 0,
    wave_count INTEGER DEFAULT 0,
    negation_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    long_paragraphs INTEGER DEFAULT 0,
    avg_punct_types_per_para REAL DEFAULT 0.0,
    dialogue_breaks INTEGER DEFAULT 0,
    banned_patterns TEXT DEFAULT '[]',
    violations TEXT DEFAULT '[]',
    passed INTEGER DEFAULT 0,  -- BOOLEAN as INTEGER
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chapter_id)
);

-- ─── Indexes ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_volumes_novel ON volumes(novel_id);
CREATE INDEX IF NOT EXISTS idx_chapters_novel ON chapters(novel_id);
CREATE INDEX IF NOT EXISTS idx_chapters_volume ON chapters(volume_id);
CREATE INDEX IF NOT EXISTS idx_characters_novel ON characters(novel_id);
CREATE INDEX IF NOT EXISTS idx_relations_novel ON character_relations(novel_id);
CREATE INDEX IF NOT EXISTS idx_world_novel ON world_settings(novel_id);
CREATE INDEX IF NOT EXISTS idx_foreshadows_novel ON foreshadows(novel_id);
CREATE INDEX IF NOT EXISTS idx_timeline_novel ON timeline_events(novel_id);
CREATE INDEX IF NOT EXISTS idx_scene_chapter ON scene_outlines(chapter_id);
CREATE INDEX IF NOT EXISTS idx_dimension_novel ON dimension_changes(novel_id);
CREATE INDEX IF NOT EXISTS idx_quality_novel ON chapter_quality(novel_id);
CREATE INDEX IF NOT EXISTS idx_quality_chapter ON chapter_quality(chapter_id);
CREATE INDEX IF NOT EXISTS idx_distillation_novel ON character_distillation_evolution(novel_id);
CREATE INDEX IF NOT EXISTS idx_distillation_character ON character_distillation_evolution(character_id);
CREATE INDEX IF NOT EXISTS idx_distillation_chapter ON character_distillation_evolution(chapter_id);
CREATE INDEX IF NOT EXISTS idx_char_snap_novel ON character_state_snapshots(character_id);
-- ─── Layered Loading Indexes ──────────────────────────────
CREATE INDEX IF NOT EXISTS idx_world_region ON world_settings(region);
CREATE INDEX IF NOT EXISTS idx_world_faction ON world_settings(faction_id);
CREATE INDEX IF NOT EXISTS idx_world_volume_range ON world_settings(volume_range);
CREATE INDEX IF NOT EXISTS idx_world_category_region ON world_settings(category, region);
CREATE INDEX IF NOT EXISTS idx_world_status ON world_settings(status);
