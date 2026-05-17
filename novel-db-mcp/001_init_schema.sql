-- Novel DB Schema + Chapter Quality Table
-- Run: psql -d fcli -f 001_init_schema.sql

-- ─── Core ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS novels (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    genre TEXT DEFAULT '',
    target_platform TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    status TEXT DEFAULT 'brainstorming',
    current_chapter INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ─── Volumes ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS volumes (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title TEXT DEFAULT '',
    main_plotlines JSONB DEFAULT '[]',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(novel_id, number)
);

-- ─── Chapters ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chapters (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title TEXT DEFAULT '',
    outline TEXT DEFAULT '',
    chapter_type TEXT DEFAULT 'normal',
    volume_id INTEGER REFERENCES volumes(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(novel_id, number)
);

-- ─── Characters ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS characters (
    id SERIAL PRIMARY KEY,
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
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ─── Character Relations ───────────────────────────────
CREATE TABLE IF NOT EXISTS character_relations (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    from_character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    to_character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    chapter_established INTEGER DEFAULT NULL,
    intensity INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ─── World Settings ────────────────────────────────────
CREATE TABLE IF NOT EXISTS world_settings (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(novel_id, category, name)
);

-- ─── Chapter Summaries ─────────────────────────────────
CREATE TABLE IF NOT EXISTS chapter_summaries (
    chapter_id INTEGER PRIMARY KEY REFERENCES chapters(id) ON DELETE CASCADE,
    summary TEXT DEFAULT '',
    key_events JSONB DEFAULT '[]',
    characters_involved JSONB DEFAULT '[]',
    new_foreshadows JSONB DEFAULT '[]',
    resolved_foreshadows JSONB DEFAULT '[]',
    dimension_snapshot JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ─── Foreshadows ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS foreshadows (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    planted_chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    planned_recall_chapter INTEGER DEFAULT NULL,
    actual_recall_chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    importance TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'planted',
    related_characters JSONB DEFAULT '[]',
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ─── Timeline ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS timeline_events (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    event_time TEXT DEFAULT '',
    event_order INTEGER DEFAULT 0,
    event_description TEXT NOT NULL,
    characters_involved JSONB DEFAULT '[]',
    location_id INTEGER DEFAULT NULL,
    significance TEXT DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ─── Scene Outlines ────────────────────────────────────
CREATE TABLE IF NOT EXISTS scene_outlines (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    scene_number INTEGER NOT NULL,
    location TEXT DEFAULT '',
    characters_involved JSONB DEFAULT '[]',
    conflict TEXT DEFAULT '',
    emotion_type TEXT DEFAULT '',
    key_beats JSONB DEFAULT '[]',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chapter_id, scene_number)
);

-- ─── Dimension Changes ─────────────────────────────────
CREATE TABLE IF NOT EXISTS dimension_changes (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,
    change_type TEXT DEFAULT '',
    entity_name TEXT DEFAULT '',
    before_value JSONB DEFAULT '{}',
    after_value JSONB DEFAULT '{}',
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════
-- NEW: Chapter Quality (Phase 1)
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS chapter_quality (
    id SERIAL PRIMARY KEY,
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
    avg_punct_types_per_para FLOAT DEFAULT 0.0,
    dialogue_breaks INTEGER DEFAULT 0,
    banned_patterns TEXT[] DEFAULT '{}',
    violations JSONB DEFAULT '[]',
    passed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
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
