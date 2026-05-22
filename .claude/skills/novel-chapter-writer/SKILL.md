---
name: novel-chapter-writer
description: 逐章写作编排器，直接调 MCP + 模型完成章节。触发词：写第N章/继续写/写一章
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__get_chapter_context, mcp__novel-db__validate_chapter, mcp__novel-db__writing_finish, mcp__novel-db__resolve_engines, mcp__novel-db__skill_loader, mcp__novel-db__character_update, mcp__novel-db__character_increment, mcp__novel-db__character_snapshot, mcp__novel-db__relation_snapshot, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_recall, mcp__novel-db__world_upsert, mcp__novel-db__character_create, mcp__novel-db__relation_create, mcp__novel-db__consistency_guard, mcp__novel-db__distillation_evolve, mcp__novel-db__volume_get, mcp__memory__memory_store, mcp__memory__memory_search
depends_on: novel-planner, engines/anti-ai-quickref, engines/author-voice
lifecycle: core
version: "2.0.0"
---

# 逐章写作编排器（v2 — 无子 Agent）

> **v2 架构原则**：编排器直接调 MCP 获取精简上下文 + 做创意决策 + 生成正文。无子 Agent，无中间文件传递，无信息损耗。

<what-to-do>

## 流水线总览

```
Step 0 断点检测 + 一致性校验
  ↓
Step 1 get_chapter_context (MCP) → 精简上下文包
  ↓
Step 2 创意决策 → 创意蓝图（含新实体创建）+ 存档
  ↓  🔒 检查点 A: 确认创意蓝图
Step 3 resolve_engines (MCP) → 引擎指令
  ↓
Step 4 逐场面生成正文 + 自检
  ↓  🔒 检查点 B: 确认正文完整性
Step 5 🔒 validate_chapter + writing_finish + 存盘
```

### v1→v2 变更摘要

| 变更 | v1 | v2 |
|------|----|----|
| Agent 数量 | 4 个子 Agent | 0（编排器直接执行） |
| 文件加载 | 27+ 个文件 | MCP 聚合查询（get_chapter_context + resolve_engines） |
| 上下文体积 | ~80KB（完整档案+全量世界观） | ~36KB（蒸馏卡片+分层世界观+世界状态） |
| 中间文件 | 4 个 .tmp 文件 | 0（创意蓝图直接存档） |
| 约束检查 | Agent 3 手动加载引擎文件 | resolve_engines MCP + writing_rules 自动注入 |
| 信息损耗 | Agent 间传递有压缩损耗 | 无传递，零损耗 |

## Step 0: 断点检测 + 一致性校验

检查 `novels/{小说名}/正文/第{NNN}章-{标题}.md` 是否已存在：
- **文件存在且完整** → 提示「第 N 章已完成，是否写第 N+1 章？」
- **文件不存在** → 进入 Step 1
- **断点续传**：Memory 搜索 `flow-state` 恢复中断位置

**一致性校验**：`consistency_guard(novel_name="NOVEL_NAME", auto_sync=True)`

## Step 1: 获取精简上下文包

### 1.1 一次 MCP 调用获取全部上下文

```
ctx = get_chapter_context(novel_name="NOVEL_NAME", chapter_number={N}, load_mode="smart")
```

**v2 返回精简上下文包**（~36KB）：
- `chapter` — 章节信息
- `volume` — 卷级大纲（含 world_state 字段）
- `prev_summaries` — 前3章摘要
- `character_cards` — 角色蒸馏卡片（name/role/核心特质/说话风格/目标/弧线/关系摘要/快照）
- `unresolved_foreshadows` — 本章相关伏笔（按卷范围过滤）
- `active_threads` — 活跃线索
- `world_settings` — 分层世界观（smart 模式：宽范围条目只返回索引，卷级特定返回完整数据）
- `world_state` — 当前卷世界状态（衰退曲线锚点+外围/中域/内城描述）
- `tone_prompts` — 底色提示（从 writing_rules world_tone 类别提取）
- `timeline` — 时间线
- `quality_history` — 质量历史
- `writing_prompt` — 写作提示词（含规则+作者DNA）

**无需再单独调用**：`volume_get` / `foreshadow_list` / `character_detail` / `relation_list` / `world_query` / `timeline_query`

### 1.2 补充基调指令

如卷级大纲中本章条目包含基调字段（基调向量/世界秩序锚/特写配额），提取备用。如缺失，标注 ⚠️。

加载基调词典（仅此一个文件需手动读取）：
```
Read("novels/{小说名}/设定/写作/tone-primer.md")
```

### 1.3 回退策略

如 `world_settings` 某分类为空，说明未同步到 DB，回退读设定文件。

## Step 2: 创意决策 → 创意蓝图

编排器直接做创意决策，不启动子 Agent。

### 2.1 场面设计

基于上下文包，设计本章场面：
- 常规章 2-4 个场面，转折章 5-6 个
- 每个场面标注 AES 类型标签（供 Step 3 resolve_engines 使用）
- 每个场面填写基调字段（基调调性/写透或粗放/克制约束/微动作分配）
- 确认因果链完整性（前因→后果→角色选择）
- 场面分配到起承转合（起10-15%/承40-50%/转20-25%/合10-15%）

### 2.2 角色弧线 + 伏笔操作

- 设计角色行为弧线（含失控时刻）
- 设计伏笔操作（种/推进/回收）
- 设计微事件和弹性事件（2-3个，覆盖800-1500字余量）

### 2.3 创建新实体

识别需新建的人物/地点/物品/势力/伏笔，直接调 MCP 创建：
- `character_create` / `world_upsert` / `foreshadow_plant` / `relation_create`

### 2.4 存档创意蓝图

```
Write("novels/{小说名}/创意决策/Ch{N}-创意蓝图.md", blueprint_content)
```

🔒 **检查点 A**：确认创意蓝图包含场面设计 + 因果链 + 角色行为弧线 + AES 标签。

## Step 3: 加载引擎指令

```
engines = resolve_engines(AES_tags=[从创意蓝图提取的场面类型标签])
```

MCP 自动从 `ENGINE_MATRIX` 匹配引擎文件并加载内容。始终注入 `author-voice`。

**反AI指令**：从 `get_chapter_context` 返回的 `writing_prompt` 中获取（已由规则引擎注入）。

**术语规范**：从 `writing_prompt` 中的 `term_map` 规则获取。

**硬约束**：从 `writing_prompt` 中的 `hard_constraint` 规则获取。

无需手动读取 `engines/anti-ai-quickref.md` / `engines/writing-style.md` / `term-map.md` — 全部已通过 MCP 聚合注入。

## Step 4: 逐场面生成正文 + 自检

编排器直接生成正文，不启动子 Agent。

### 4.1 写前确认

确认信息就绪度：角色矩阵 ✓ / 感官分配 ✓ / 反AI指令 ✓ / 硬约束 ✓ / 微事件 ✓ / 伏笔 ✓

### 4.2 逐场面生成

按起承转合四段逐场面生成：
- 每段完成后反AI自检（F1-F6）
- 全文通读后硬约束自检 + 术语合规检查

### 4.3 自检报告

产出正文 + 自检报告（反AI逐项结果 + 硬约束逐条结果）

🔒 **检查点 B**：确认正文完整性 — 字数达标（卷均80-120%，关键转折章120-180%）+ 场面覆盖完整 + 反AI自检通过。

**字数不足时**：先展开蓝图的全部弹性事件。如仍不足，补充世界呼吸/人物互动微场景，**不循环重跑**。

## Step 5: 🔒 存盘 + 移交审计

> **生成与审计分离**：本章只生成正文，审计由 novel-qa 独立进行。

### 5.1 validate_chapter

```
validate_chapter(chapter_text={正文})
```

有 violations 必须修复后才能存盘。

### 5.2 writing_finish

```
writing_finish(novel_name, chapter_number, chapter_text, summary, key_events,
  characters_involved, new_foreshadows, resolved_foreshadows, self_check='passed')
```

### 5.3 更新角色与关系快照

对每个出场角色：
- `character_increment` — 增量更新状态（identity/ability/goal/knows/relationships）
- `character_snapshot` — 保存快照到独立表
- 对有显著变化的关系：`relation_snapshot`
- 对有显著演化的角色：`distillation_evolve`（主角色每次都调，配角仅显著变化时调）

### 5.4 存盘

正文写入 `novels/{小说名}/正文/第{NNN}章-{标题}.md`。纯净化：只写正文，不含注释/统计/审计备注。

### 5.5 一致性同步

```
consistency_guard(novel_name="NOVEL_NAME", auto_sync=True)
```

🔒 **不可跳过**。

### 5.6 移交审计

```
第{NNN}章生成完成。是否进行独立审计？
- 输入"审计" → 触发 novel-qa
- 输入"继续" → 进入下一章
```

</what-to-do>

<supporting-info>

## 创意蓝图格式

```markdown
# Ch{N} 创意蓝图

## 场面设计
### 场面 1: {标题}
- AES: {类型标签}
- 基调: {调性} | 写透/粗放 | 克制约束 | 微动作
- 冲突: {核心冲突}
- 角色: {出场角色}
- 因果: {前因→选择→后果}

### 场面 2: ...

## 因果链
{事件A} → {角色选择} → {事件B} → ...

## 角色弧线
- {角色1}: {起始状态} → {失控时刻} → {结束状态}
- {角色2}: ...

## 伏笔操作
- 种: {新伏笔}
- 推进: {已有伏笔}
- 回收: {待回收伏笔}

## 弹性事件
1. {弹性事件1} (~500字)
2. {弹性事件2} (~500字)

## 已创建实体
- character: {name} (id={id})
- world: {name} (id={id})
- foreshadow: {id}
```

## DB 存盘伪代码

### 角色状态增量更新（character_increment）

```python
for character in involved_characters:
    character_increment(
        novel_name="NOVEL_NAME",
        character_name=character.name,
        snapshot_update=json.dumps({
            "identity": character.new_identity,
            "ability": character.new_ability_state,
            "goal": character.new_goal,
            "knows": character.new_knowledge,
            "doesnt_know": character.new_unknowns,
            "relationships": character.relationship_changes
        }),
        growth_add=json.dumps({
            "volume": current_volume,
            "chapter": chapter_number,
            "changes": character.changes_this_chapter,
            "trigger": character.trigger_event
        })
    )
```

### 角色快照（character_snapshot）

```python
for character in involved_characters:
    character_snapshot(
        novel_name="NOVEL_NAME",
        character_name=character.name,
        chapter_number=chapter_number,
        location=character.current_location,
        arc_phase=character.arc_phase,
        emotional_state=character.emotional_state,
        physical_state=character.physical_state,
        ability_snapshot=json.dumps(character.ability_state),
        inventory_snapshot=json.dumps(character.inventory),
        knowledge_snapshot=json.dumps(character.knowledge_state),
        notes=character.snapshot_notes
    )
```

### 关系快照（relation_snapshot）

```python
for relation_change in blueprint.relationship_changes:
    relation_snapshot(
        novel_name="NOVEL_NAME",
        from_name=relation_change.from_name,
        to_name=relation_change.to_name,
        chapter_number=chapter_number,
        intensity=relation_change.new_intensity,
        status=relation_change.new_status,
        notes=relation_change.description
    )
```

### 人物蒸馏演化记录（distillation_evolve）

```python
for character in characters_with_evolution:
    if not character.distillation_tracked:
        continue
    distillation_evolve(
        novel_name="NOVEL_NAME",
        character_name=character.name,
        chapter_number=chapter_number,
        decision_delta=json.dumps(character.decision_changes),
        new_knowledge=json.dumps(character.new_information),
        changed_beliefs=json.dumps(character.belief_shifts),
        relation_shifts=json.dumps(character.relation_shifts),
        voice_changes=json.dumps(character.voice_changes),
        ability_changes=json.dumps(character.ability_changes),
        arc_transition=json.dumps(character.arc_transition),
        key_decision=json.dumps(character.key_decision),
        notes=character.evolution_notes
    )
```

## Step 4 执行规范

### 事件分类

| 类型 | 作用 | 特征 |
|------|------|------|
| 线索推动型 | 推动线索进展 | 有线索标记（F1/F2...） |
| 人物关系型 | 推动关系变化 | 互动后信任/怀疑/依赖变化 |
| 场景铺垫型 | 为高潮铺垫 | 不直接推进，让后续更有冲击力 |
| 人物展示型 | 自然展现人物 | 通过对话/行动体现，禁评价词 |
| 伏笔埋设型 | 长线回收准备 | 必须填foreshadow_plant |

### 事件层级

| 层级 | 粒度 | 爽点要求 |
|------|------|---------|
| 超级 | 卷级 | 卷终决战/命运转折 |
| 大 | 弧级(8-12章) | Boss战/重大转折 |
| 中 | 段级(3-5章) | 阶段胜利/关系突破 |
| 小 | 章级 | 小胜利/小揭露/角色高光 |
| 微 | 场景级 | 对话钩子/信息投放 |

### 爽点密度

- 微/小爽点：每章至少1个
- 中爽点：每3-5章
- 大高潮：每8-12章
- 超级高潮：每卷1-2次
- **平路不超过3章**

### 4层内容模型

| 层 | 内容 | 占比 | 要求 |
|----|------|------|------|
| A推进层 | 主线/冲突/升级 | 40-50% | 每段必须有新信息 |
| B人物层 | 对话/心理/关系 | 25-30% | 主观镜头偏心 |
| C世界层 | 环境/NPC/世界观 | 15-20% | 用身体感受替代精确数字 |
| D氛围层 | 感官/节奏/伏笔 | 5-10% | 锯齿状叙事 |

### 章节结构变体（每5章至少2种）

| 变体 | 适用 | 结构 |
|------|------|------|
| 标准型 | 常规推进 | 起→承→转→合 |
| 突入型 | 延续高潮 | 直接从转开始→合留悬念 |
| 日常型 | 过渡铺垫 | 起→长段日常承→安静收束 |
| 倒叙型 | 揭露回忆 | 合段开头→倒回起→承→解释 |
| 碎片型 | 多线切换 | 3-4个短场景碎片拼接 |
| 螺旋型 | 高潮核心 | 起极短→承极长→转爆发→合极短 |

### NPC互动规则（每章至少2个有动机NPC）

| 类型 | 动机 | 对话特点 |
|------|------|---------|
| 商贩 | 利益驱动 | 价格变动/供需/行情 |
| 居民 | 地区文化 | 生活态度/舆论/流言 |
| 军人 | 专业背景 | 术语/经验/立场 |
| 逃亡者 | 创伤求生 | 谨慎/回避/试探 |

NPC必须有：姓名/绰号 + 背景暗示 + 可见动机 + 与主角的互动痕迹。

### 字数控制

- **最低**: 3000字（不含标点）
- **目标**: 3000-5000字
- 不足3000时按优先级填充：
  1. 先展开蓝图的弹性事件储备（世界呼吸/人物塑造/费笔纹理/人物互动）
  2. 再扩展现有场面的感官维度（嗅觉/触觉/温度/环境音）
  3. 再加入角色微动作/微表情/习惯细节
  4. **填充标准**：每次填充引入新内容（新动作/新对话/新冲突/新事件），不重复已有内容

### 内容丰富度14项检查

| 检查项 | 要求 |
|--------|------|
| 章节结构 | 使用合适变体，近5章至少2种不同变体 |
| 章末钩子 | 有钩子或确认是日常型 |
| 爽点密度 | 本章至少1个微/小爽点 |
| 信息缺口 | 至少1个 |
| 日常事件 | 2-3个日常场景 |
| NPC出场 | 至少2个有动机NPC |
| 场景搭建 | 每场景五感氛围铺垫 |
| 世界观展示 | 至少3个元素自然融入 |
| 人物性格 | 微表情/动作展示（禁直白词） |
| 分支事件 | 占15%-25%字数 |
| 4层内容 | A40-50%+B25-30%+C15-20%+D5-10% |
| 反注水 | 无孤立感官/无因果过渡/无重复意象 |
| 场景密度 | 每3段至少1段"同时做2+件事" |
| 伏笔处理 | 伏笔已标记并填写foreshadow_plant |

## consistency_guard 自动同步原理

编排器在创意决策中通过 MCP 创建了新实体（DB 已有），`consistency_guard` 自动检测 DB hash 变更并同步到文件。一个调用覆盖所有实体类型。

</supporting-info>
