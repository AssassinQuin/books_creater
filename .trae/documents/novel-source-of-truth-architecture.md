# 小说项目「单源维护」与「动态加载」架构方案

> 状态：Plan Phase 4 — 决策完成待执行
> 目标：解决DB/lorebook/角色深化.md等多源冲突，设计动态加载协议

---

## 一、当前状态分析

### 1.1 数据源现状

| 数据源 | 格式 | 用途 | 当前问题 |
|--------|------|------|----------|
| **novel-db (PostgreSQL)** | 结构化数据 | 章节、人物、伏笔、世界观查询 | 与lorebook/YAML不同步 |
| **lorebook/entries/*.yml** | YAML | 写作时按需注入的世界知识 | 从世界观/*.md拆分，可能已过期 |
| **世界观/*.md** | Markdown | 完整世界观文档 | 上游源文件，但更新后未同步到lorebook |
| **角色深化.md** | Markdown | 人物深度描写 | 与DB中character表、lorebook人物条目可能冲突 |
| **人物/{角色}.md** | Markdown | 单人物档案 | 与角色深化.md中的描述可能不一致 |
| **锁定设定.md** | Markdown | 不可变更的设定 | 权威最高，但其他文件可能无意中违反 |
| **大纲/*.md** | Markdown | 卷级大纲 | 与DB中volume/chapter表不同步 |
| **novel-chapter-writer impl.py** | Python | 写作执行代码 | 当前为stub，未实现完整MCP调用 |

### 1.2 核心痛点

1. **多源冲突**：同一设定（如沈念病情）可能在DB、lorebook、角色深化.md中有不同描述
2. **过期信息**：世界观/*.md更新后，lorebook/entries/*.yml未同步
3. **加载混乱**：写作时不知道以哪个为准——是查DB？读YAML？还是读markdown？
4. **缺乏检测**：没有自动化工具检测多源之间的冲突

---

## 二、架构设计：双源同步 + 冲突检测

### 2.1 核心原则

```
┌─────────────────────────────────────────────────────────────┐
│                    真相层（Source of Truth）                  │
├─────────────────────────────────────────────────────────────┤
│  主真相源：novel-db (PostgreSQL)                              │
│  ├─ 优势：结构化查询、版本控制、事务一致性                      │
│  └─ 存储：人物、章节、伏笔、世界观、时间线、维度               │
│                                                              │
│  辅真相源：lorebook/entries/*.yml                            │
│  ├─ 优势：写作时按需加载、token高效、关键词触发               │
│  └─ 存储：世界观条目、势力、物品、地点                        │
│                                                              │
│  权威层：锁定设定.md + 角色深化.md                            │
│  ├─ 锁定设定.md：最高优先级，任何源不得违反                   │
│  └─ 角色深化.md：人物深度描写，与DB互补                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    同步层（Sync Layer）                       │
├─────────────────────────────────────────────────────────────┤
│  同步方向：                                                   │
│  1. DB → lorebook：world_upsert触发时，同步更新对应YAML       │
│  2. lorebook → DB：YAML变更后，通过脚本同步到world_query      │
│  3. 角色深化.md → DB：人物描写更新后，同步到character_update  │
│                                                              │
│  冲突检测：                                                   │
│  - 哈希校验：每个源文件记录内容哈希                           │
│  - 定时扫描：每24小时检测一次多源一致性                       │
│  - 冲突报告：生成冲突清单，人工裁决                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    消费层（Consumer Layer）                   │
├─────────────────────────────────────────────────────────────┤
│  novel-chapter-writer 写作时动态加载协议：                     │
│  1. 优先查DB：writing_start() → 获取结构化上下文              │
│  2. 按需加载YAML：Lorebook机制 → 关键词触发条目               │
│  3. 深度补充：角色深化.md → 人物心理/弧光                     │
│  4. 权威校验：锁定设定.md → 最终一致性检查                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据分类与归属

| 数据类型 | 主真相源 | 辅真相源 | 权威层 | 同步策略 |
|----------|---------|---------|--------|----------|
| **人物基础信息** | DB (character表) | lorebook人物条目 | 角色深化.md | DB↔YAML双向同步 |
| **人物深度描写** | 角色深化.md | — | 角色深化.md | 单向→DB摘要 |
| **世界观条目** | lorebook YAML | DB (world_query) | 世界观/*.md | YAML↔DB双向同步 |
| **势力/地点/物品** | lorebook YAML | DB (world_query) | 锁定设定.md | YAML↔DB双向同步 |
| **章节内容** | DB (chapter表) | 大纲/*.md | 大纲/*.md | DB→大纲单向同步 |
| **伏笔/线索** | DB (foreshadow表) | 线索追踪.md | 线索追踪.md | DB↔markdown双向同步 |
| **时间线/维度** | DB (timeline表) | — | — | DB唯一源 |
| **锁定设定** | 锁定设定.md | — | 锁定设定.md | 单向校验 |

### 2.3 动态加载协议（写作时）

```python
# novel-chapter-writer 写作时加载流程

def load_writing_context(novel_id, chapter_number):
    """
    三级加载协议 + 动态加载
    """
    context = {}
    
    # Tier 1: 必须加载（DB查询）
    context['novel'] = novel_get(novel_id)
    context['chapter'] = chapter_get_context(novel_id, chapter_number)
    context['volume'] = volume_get(context['chapter'].volume_id)
    context['characters'] = [character_get(c.id) for c in chapter_characters]
    context['relations'] = relation_list(novel_id)
    
    # Tier 2: 按需加载（Lorebook机制）
    lorebook_entries = lorebook_load(
        scan_text=chapter_outline + character_names + location_names,
        volume_range=f"V{context['volume'].number}"
    )
    context['worldbuilding'] = lorebook_entries
    
    # Tier 3: 深度补充（Markdown文件）
    for char in context['characters']:
        deepening_file = f"设定/人物/{char.name}.md"
        if file_exists(deepening_file):
            context['character_deepening'][char.name] = read_file(deepening_file)
    
    # Tier 4: 权威校验
    context['locked_rules'] = read_file("设定/锁定设定.md")
    
    # 冲突检测
    conflicts = detect_conflicts(context)
    if conflicts:
        raise ConflictError(f"发现{len(conflicts)}处冲突：{conflicts}")
    
    return context
```

### 2.4 冲突检测机制

```python
def detect_conflicts(context):
    """
    检测多源之间的冲突
    """
    conflicts = []
    
    # 检测1: DB人物 vs lorebook人物
    for char in context['characters']:
        db_ability = char.ability_level  # 来自DB
        lorebook_ability = context['worldbuilding'].get(f"LB-{char.id}-能力")
        if db_ability != lorebook_ability:
            conflicts.append({
                'type': '人物能力冲突',
                'source1': f"DB:character#{char.id}",
                'source2': f"lorebook:LB-{char.id}",
                'diff': f"DB={db_ability}, lorebook={lorebook_ability}"
            })
    
    # 检测2: 锁定设定 vs 其他源
    locked_rules = parse_locked_rules(context['locked_rules'])
    for entry in context['worldbuilding']:
        for rule in locked_rules:
            if violates_rule(entry, rule):
                conflicts.append({
                    'type': '违反锁定设定',
                    'source': f"lorebook:{entry.id}",
                    'rule': rule.description
                })
    
    # 检测3: 角色深化 vs DB状态
    for name, deepening in context['character_deepening'].items():
        db_status = context['characters'][name].status
        if not consistent_with_deepening(db_status, deepening):
            conflicts.append({
                'type': '角色状态冲突',
                'source1': f"DB:character#{name}",
                'source2': f"角色深化:{name}",
                'diff': f"DB状态与深化描写不一致"
            })
    
    return conflicts
```

---

## 三、实施计划

### Phase 1: 基础设施（1-2天）

1. **创建同步脚本**
   - `scripts/sync_db_to_lorebook.py`: DB → YAML同步
   - `scripts/sync_lorebook_to_db.py`: YAML → DB同步
   - `scripts/detect_conflicts.py`: 冲突检测
   - `scripts/validate_locked_rules.py`: 锁定设定校验

2. **创建状态追踪文件**
   - `设定/lorebook/state.yml`: 记录各源最后同步时间、内容哈希
   - `设定/.sync_status.json`: 同步状态记录

### Phase 2: 当前项目清理（2-3天）

1. **运行冲突检测**
   - 检测DB vs lorebook vs 角色深化.md之间的冲突
   - 生成冲突报告

2. **人工裁决冲突**
   - 以锁定设定.md为最高优先级
   - DB和YAML之间的冲突，以"最后更新者"为准
   - 角色深化.md与DB冲突，以角色深化.md为准（深度描写优先）

3. **同步所有源**
   - 将裁决后的结果同步到所有源
   - 更新state.yml和.sync_status.json

### Phase 3: 写作流程集成（2-3天）

1. **更新novel-chapter-writer**
   - 实现完整的`load_writing_context()`函数
   - 集成Lorebook加载机制
   - 集成冲突检测

2. **更新SKILL.md**
   - 在novel-chapter-writer/SKILL.md中明确加载协议
   - 在novel-qa/SKILL.md中增加冲突检测审计项

3. **创建CI检查**
   - 每次提交前自动运行冲突检测
   - 冲突未解决禁止提交

### Phase 4: 持续维护（长期）

1. **定时同步**
   - 每天自动运行同步脚本
   - 冲突报告发送到审阅报告目录

2. **版本控制**
   - 所有设定文件纳入git版本控制
   - 冲突裁决记录为ADR

---

## 四、文件变更清单

### 新增文件

| 文件 | 用途 |
|------|------|
| `scripts/sync_db_to_lorebook.py` | DB→YAML同步脚本 |
| `scripts/sync_lorebook_to_db.py` | YAML→DB同步脚本 |
| `scripts/detect_conflicts.py` | 冲突检测脚本 |
| `scripts/validate_locked_rules.py` | 锁定设定校验脚本 |
| `设定/lorebook/state.yml` | 同步状态追踪 |
| `设定/.sync_status.json` | 内容哈希记录 |
| `审阅报告/冲突检测-{日期}.md` | 冲突检测报告 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `novel-chapter-writer/impl.py` | 实现完整的动态加载协议 |
| `novel-chapter-writer/SKILL.md` | 明确三级加载协议 + 冲突检测 |
| `novel-qa/SKILL.md` | 增加冲突检测审计项 |
| `novel-planner/SKILL.md` | 规划时标注数据来源 |
| `CLAUDE.md` | 更新架构说明 |

---

## 五、验证步骤

1. **冲突检测验证**
   - 运行`detect_conflicts.py`
   - 确认能检测出已知的冲突（如沈念病情在DB和角色深化.md中的差异）

2. **同步验证**
   - 修改DB中的一个世界观条目
   - 运行`sync_db_to_lorebook.py`
   - 确认对应YAML文件已更新

3. **写作流程验证**
   - 运行`load_writing_context(1, 1)`
   - 确认返回的context包含所有必要信息
   - 确认无冲突时正常返回，有冲突时抛出错误

4. **锁定设定校验**
   - 在lorebook中创建一个违反锁定设定的条目
   - 运行`validate_locked_rules.py`
   - 确认能检测出违规

---

## 六、决策记录

| 决策 | 理由 |
|------|------|
| **双源同步**（DB+YAML） | DB适合结构化查询，YAML适合写作时按需加载，两者互补 |
| **锁定设定.md最高优先级** | 明确不可变更的设定，防止多源修改导致底层矛盾 |
| **角色深化.md优先于DB** | 人物深度描写是创作核心，DB只存储结构化摘要 |
| **冲突检测自动化** | 人工检查64个YAML文件+20+markdown文件不现实 |
| **定时同步而非实时同步** | 写作时不需要毫秒级同步，每天一次足够 |

---

> 本方案待用户确认后执行。
