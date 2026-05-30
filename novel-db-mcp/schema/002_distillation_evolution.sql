-- 002_distillation_evolution.sql
-- 人物蒸馏模型演化追踪表
-- 记录人物决策引擎、声音指纹、行为模式随剧情的增量变化
-- Run: psql -d fcli -f 002_distillation_evolution.sql

-- ─── Character Distillation Evolution ──────────────────
-- 每章写完后记录人物蒸馏模型的变化增量
CREATE TABLE IF NOT EXISTS character_distillation_evolution (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    
    -- 决策引擎变化：面对同一情境，决策倾向如何改变
    -- [{"trigger": "得知焱的计划", "rule_name": "保护城镇", "before": "默默观察", "after": "主动警告"}]
    decision_delta JSONB DEFAULT '[]',
    
    -- 信息获取：本章新知道的信息
    -- ["焱的真实目的", "教会与异灵的秘密协议"]
    new_knowledge JSONB DEFAULT '[]',
    
    -- 信念/认知变化：世界观、价值观的转变
    -- [{"belief": "人类值得保护", "before": true, "after": false, "reason": "被保护的人杀死了它"}]
    changed_beliefs JSONB DEFAULT '[]',
    
    -- 关系变化：对其他角色态度/信任度的演变
    -- [{"target": "沈野", "aspect": "信任", "before": 5, "after": 8, "reason": "共同战斗"}]
    relation_shifts JSONB DEFAULT '[]',
    
    -- 声音指纹变化：说话方式的微妙演变
    -- {"pace_change": "从沉默变急促", "new_habits": ["开始反问", "用人类谚语"], "lost_habits": []}
    voice_changes JSONB DEFAULT '{}',
    
    -- 能力/限制变化：新能力解锁、旧限制突破或新增限制
    -- {"unlocked": ["情绪共鸣"], "weakened": ["拟态稳定性"], "reason": "V8兽潮中暴露身份"}
    ability_changes JSONB DEFAULT '{}',
    
    -- 弧线阶段推进：从哪个阶段进入哪个阶段
    -- {"from": "渗透潜伏", "to": "身份暴露", "trigger": "兽潮中被迫使用真身"}
    arc_transition JSONB DEFAULT '{}',
    
    -- 本章关键抉择：面对什么情境，做出了什么选择
    -- {"situation": "是否暴露身份救城镇", "choice": "暴露", "alternatives": ["继续隐藏"], "consequence": "被人类杀死"}
    key_decision JSONB DEFAULT '{}',
    
    -- 写作备注：作者对人物变化的注释
    notes TEXT DEFAULT '',
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- ─── Indexes ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_distillation_novel ON character_distillation_evolution(novel_id);
CREATE INDEX IF NOT EXISTS idx_distillation_character ON character_distillation_evolution(character_id);
CREATE INDEX IF NOT EXISTS idx_distillation_chapter ON character_distillation_evolution(chapter_id);
CREATE INDEX IF NOT EXISTS idx_distillation_created ON character_distillation_evolution(created_at);

-- ─── Character State Snapshots 补充索引 ─────────────────
-- 现有表已存在，确保索引完备
CREATE INDEX IF NOT EXISTS idx_char_snap_novel ON character_state_snapshots(character_id);
