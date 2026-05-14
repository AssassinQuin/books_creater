# 动态加载协议（Dynamic Loading Protocol）

> **用途**: 定义写作时从多个数据源加载上下文的规则，确保数据一致性
> **触发时机**: Step 1 引擎加载上下文时
> **核心原则**: 四级加载 + 冲突检测 + 单源维护

---

## 一、数据源优先级

```
权威层（不可违反）
  └── 锁定设定.md ──────────────────────── 最高优先级
      │
      ├── 真相层（Source of Truth）
      │   ├── 主真相源: novel-db (PostgreSQL)
      │   │   └─ 人物、章节、伏笔、世界观、时间线、维度
      │   └── 辅真相源: lorebook/entries/*.yml
      │       └─ 世界观条目、势力、物品、地点
      │
      └── 深度层（Creative Depth）
          ├── 角色深化.md ─────────────── 人物心理/弧光
          └── 世界观/*.md ─────────────── 完整世界观文档
```

### 优先级规则

| 冲突场景 | 裁决规则 |
|----------|---------|
| 锁定设定 vs 任何源 | **锁定设定优先**，任何源不得违反 |
| DB vs lorebook YAML | 以**最后更新者**为准，记录冲突 |
| 角色深化.md vs DB | **角色深化优先**（深度描写是创作核心） |
| 世界观/*.md vs lorebook | **世界观/*.md优先**（上游源文件） |
| DB vs 大纲/*.md | **DB优先**（结构化数据），大纲作为视图 |

---

## 二、四级加载协议

### Tier 1: DB查询（必须加载）

**调用**: `writing_start(novel_id, chapter_number)`

**加载内容**:
```python
context["tier1_db"] = {
    "novel": novel_get(novel_id),
    "chapter": chapter_get_context(novel_id, chapter_number),
    "volume": volume_get(chapter.volume_id),
    "characters": [character_get(c.id) for c in chapter_characters],
    "relations": relation_list(novel_id),
    "foreshadows": foreshadow_list(novel_id, status="planted"),
    "timeline": timeline_query(from_chapter=N-3, to_chapter=N)
}
```

**用途**: 提供结构化上下文——人物状态、关系、伏笔、时间线

### Tier 2: Lorebook按需加载

**调用**: `load_lorebook_entries(keywords)`

**加载逻辑**:
1. 从 Tier 1 的 DB 上下文中提取关键词（角色名、地点名、势力名、大纲关键词）
2. 扫描 `lorebook/entries/*.yml`，匹配名称/标签/内容关键词
3. 只加载匹配的条目（token高效）

**用途**: 提供世界观细节——环境档案、物品档案、历史层

### Tier 3: 角色深化.md深度补充

**调用**: `load_character_deepening(characters)`

**加载逻辑**:
1. 对 Tier 1 中的每个出场角色
2. 在 `角色深化.md` 中查找对应章节（`### {角色名}`）
3. 提取深度描写（心理、弧光、口头禅、微动作）
4. 提取态度矩阵（`### {角色名} · 态度矩阵`）——当前卷涉及的关系状态
5. 提取能力弧线（`### {角色名} · 能力弧线`）——当前阶段的能力状态

**加载的skill reference**:
- `novel-character/references/ability-system.md` —— 能力体系规范（验证能力描写合规）
- `novel-character/references/relationship-tracking.md` —— 关系追踪规范（验证态度变化合规）

**用途**: 提供人物鲜活化素材——差异化对话、微表情、动作链、态度状态、能力状态

### Tier 4: 锁定设定.md权威校验

**调用**: `load_locked_rules()` + `detect_conflicts(context)`

**加载逻辑**:
1. 加载 `锁定设定.md`
2. 检测 Tier 1-3 的内容是否违反锁定规则
3. 检测 DB vs lorebook vs 角色深化 之间的冲突

**用途**: 确保一致性——防止多源冲突、防止违反不可变更设定

---

## 三、冲突检测规则

### 检测类型

| 检测项 | 严重级别 | 处理方式 |
|--------|---------|---------|
| **违反锁定设定** | 🔴 P0（致命） | 立即停止写作，修复后才能继续 |
| **人物状态矛盾** | 🔴 P0（致命） | DB显示死亡但深化中活着，或反之 |
| **人物能力差异** | 🟡 P1（严重） | DB与lorebook能力等级不一致 |
| **世界观过期** | 🟢 P2（轻微） | lorebook比世界观文件旧，提示同步 |
| **信息缺失** | 🟢 P2（轻微） | 某个源缺少其他源有的信息 |

### 冲突处理流程

```
检测到冲突
    │
    ├── P0（致命）→ 立即停止写作，抛出错误
    │                输出冲突详情，要求人工裁决
    │
    ├── P1（严重）→ 记录冲突，继续写作但标记警告
    │                写作完成后必须修复
    │
    └── P2（轻微）→ 记录冲突，不影响写作
                     定期同步时处理
```

---

## 四、同步机制

### 同步方向

| 方向 | 触发条件 | 脚本 |
|------|---------|------|
| DB → lorebook | world_upsert 触发后 | `scripts/sync_db_to_lorebook.py` |
| lorebook → DB | YAML 文件变更后 | `scripts/sync_lorebook_to_db.py` |
| 角色深化 → DB | 人物描写更新后 | 手动运行 sync 脚本 |
| 世界观 → lorebook | 世界观文件更新后 | 手动运行 sync 脚本 |

### 状态追踪

文件: `设定/.sync_status.json`

```json
{
  "last_sync": "2026-05-14T12:47:38",
  "sources": {
    "db": {"last_run": "...", "status": "synced", "entry_count": 100},
    "lorebook_yaml": {"last_run": "...", "status": "synced", "entry_count": 64},
    "character_deepening": {"last_run": "...", "status": "synced", "hash": "a1b2c3d4"},
    "worldview": {"last_run": "...", "status": "source_of_truth", "file_count": 9},
    "locked_rules": {"last_run": "...", "status": "updated", "hash": "e5f6g7h8"}
  },
  "conflicts": {"total": 0, "resolved": 6, "pending": 0}
}
```

---

## 五、写作时加载流程

```python
def write_chapter(chapter_num):
    # Step 1: 加载上下文
    context = load_writing_context(novel_id=1, chapter_number=chapter_num)
    
    # 检查冲突
    if context["conflicts"]:
        # P0冲突 → 停止
        fatal_conflicts = [c for c in context["conflicts"] if c["severity"] == "high"]
        if fatal_conflicts:
            print(f"发现 {len(fatal_conflicts)} 处致命冲突，停止写作")
            for c in fatal_conflicts:
                print(f"  🔴 [{c['type']}] {c['detail']}")
            return
        
        # P1冲突 → 警告但继续
        serious_conflicts = [c for c in context["conflicts"] if c["severity"] == "medium"]
        if serious_conflicts:
            print(f"警告: 发现 {len(serious_conflicts)} 处严重冲突")
            for c in serious_conflicts:
                print(f"  🟡 [{c['type']}] {c['detail']}")
    
    # Step 2: 写正文（使用加载的上下文）
    # ...
    
    # Step 3: 状态同步（writing_finish）
    # 同步回 DB，更新 sync_status
```

---

## 六、快速参考

### 写作时以哪个为准？

| 问题 | 答案 |
|------|------|
| 人物基础信息（年龄、能力等级） | **DB**（结构化数据） |
| 人物深度描写（心理、弧光） | **角色深化.md** |
| 人物态度/关系状态 | **角色深化.md**（态度矩阵） |
| 人物能力阶段 | **角色深化.md**（能力弧线） |
| 受伤/物品状态 | **engine-status.md** + DB status字段 |
| 世界观细节（地点、物品） | **lorebook YAML**（按需加载） |
| 世界观完整文档 | **世界观/*.md**（上游源文件） |
| 不可变更的设定 | **锁定设定.md**（最高优先级） |
| 章节内容 | **DB**（结构化数据），大纲作为视图 |
| 伏笔/线索 | **DB**（foreshadow表），线索追踪.md作为视图 |
| 能力体系规范 | **ability-system.md**（skill reference） |
| 关系追踪规范 | **relationship-tracking.md**（skill reference） |

### 冲突时怎么办？

1. **先查锁定设定.md** — 是否违反不可变更规则？
2. **再查最后更新时间** — 哪个源最新？
3. **角色相关** — 以角色深化.md为准（创作核心）
4. **世界观相关** — 以世界观/*.md为准（上游源文件）
5. **记录冲突** — 写入 `审阅报告/冲突检测-*.md`

---

> 本协议与 `impl.py` 中的 `load_writing_context()` 函数对应。
> 任何修改需同步更新 SKILL.md、impl.py 和本文件。
