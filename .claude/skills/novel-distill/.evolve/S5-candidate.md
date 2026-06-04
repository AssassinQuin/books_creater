---
name: novel-distill
description: >
  参考作品蒸馏引擎。输入小说文件路径，Phase 1 输出作品画像与推荐维度权重，
  系统按画像自动分配蒸馏路径（支持子 agent 并行），borrowable 模式独立存储为一级实体，
  下游 skill 可按维度/类型/适用场景精准检索借鉴。
  触发词：蒸馏XX/分析小说/拆解小说/参考分析/蒸馏参考
allowed-tools:
  - mcp__novel-db__*
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
version: "2.0.0"
---

# 参考作品蒸馏引擎 v2

## 触发

用户说"蒸馏XX""分析小说""拆解小说""参考分析""蒸馏参考"。

## 核心概念

**`_参考库`**：novel-db 中的特殊小说名，存储所有参考作品的蒸馏数据。不绑定任何具体小说，全局共享。

**作品画像（Portrait）**：Phase 1 的核心输出。包含作品类型标签、维度权重表、蒸馏路径推荐。画像决定后续蒸馏的资源分配和重点方向。

**borrowable 模式**：一级存储实体。每个可借鉴模式独立一条 `world_upsert`，带维度标签、适用类型、适配建议。下游 skill 可精准按模式检索，无需取整个维度 JSON。

**决策树流程**：Phase 1 输出画像 → 系统推荐蒸馏路径 → 用户确认/调整 → Phase 2 按路径并行蒸馏 → Phase 3 模式提取 → Phase 4 报告。

## 执行流程

### Phase 0：输入确认

```
1. 获取文件路径（用户直接给，或追问）
2. 验证文件存在：ls {path}
3. IF 文件不存在 → 追问正确路径
4. 统计文件大小和章节数：
   - wc -l {path}（行数）
   - grep -c "^第.*章\|^Chapter\|^\*\*\*" {path}（章节数估计）
5. 输出概要："文件 {name}，{lines} 行，约 {chapters} 章，预计 Phase 1 耗时 {est}"
6. IF 文件 > 2000 行 → 提示将分段读取
```

### Phase 1：粗提取 + 作品画像

**目标**：快速识别作品骨架，生成作品画像，推荐蒸馏路径。

#### Step 1.1：结构识别

```
分段读取文件（每段 500-800 行，重叠 50 行）：
1. 识别卷/章结构（正则：第X卷/第X章/Chapter X）
2. 记录每个分段的起止位置和标题
3. 输出结构摘要
```

#### Step 1.2：逐卷快速摘要

对每个卷/大段，提取（每卷限 200 字）：

```
- 核心事件（1-2 句）
- 出现人物（名字列表）
- 关键设定（地名/能力/势力名）
- 情绪基调（1 个词）
```

#### Step 1.3：维度覆盖检测 + 作品画像

基于摘要，判断 6 个维度中哪些有实质内容，并生成维度权重表：

| 维度 | 检测信号 | 权重评分依据 |
|------|---------|------------|
| 世界观 | 出现地理描述/历史事件/种族/文化 | 检测到的独立元素数量 x 丰富度 |
| 能力体系 | 出现等级/技能/修炼/战斗描述 | 体系复杂度（分类数 x 等级数） |
| 人物 | 出现多人物互动/关系变化/成长 | 核心人物数 x 关系密度 |
| 叙事手法 | 出现伏笔/悬念/视角切换/非线性叙事 | 技法种类数 x 使用频率 |
| 节奏结构 | 可识别弧段/高潮/日常/转折 | 弧段清晰度 x 转折密度 |
| 核心亮点 | 独特设定/创新手法/高口碑要素 | 独特性评分 |

**作品画像输出格式**：

```json
{
  "title": "{作品名}",
  "author": "{作者}",
  "genre": "{类型}",
  "genre_tags": ["西幻", "暗黑", "公路文"],
  "volumes": [...],
  "portrait": {
    "dimension_weights": {
      "world": { "score": 8, "evidence": "5地区/3种族/2文化体系" },
      "ability": { "score": 9, "evidence": "5级体系/4流派" },
      "character": { "score": 6, "evidence": "8核心人物" },
      "narrative": { "score": 7, "evidence": "3视角/多伏笔" },
      "rhythm": { "score": 5, "evidence": "可识别暖冷弧" },
      "highlight": { "score": 8, "evidence": "独特以太循环设定" }
    },
    "recommended_path": "ability > world > highlight > narrative > character > rhythm",
    "distillation_mode": "deep"
  }
}
```

#### Step 1.4：存储 meta 并输出画像

```bash
# 存储 meta 概览（含作品画像）
world_upsert(
  novel_name="_参考库",
  category="ref_meta",
  name="{作品名}",
  data={
    "title": "{作品名}",
    "author": "{作者}",
    "genre": "{类型}",
    "genre_tags": ["..."],
    "volumes": [...],
    "volume_summaries": {...},
    "portrait": { ... }
  }
)

# 存储卷摘要（每个卷一条）
world_upsert(
  novel_name="_参考库",
  category="ref_volume",
  name="{作品名}-卷{N}",
  data={...摘要数据...}
)
```

输出给用户（决策树模式，非菜单模式）：

```
{作品名} 画像分析完成：
类型：{genre_tags}
维度权重：能力体系[9] > 世界观[8] > 亮点[8] > 叙事[7] > 人物[6] > 节奏[5]

推荐蒸馏路径：能力体系 → 世界观 → 核心亮点 → 叙事手法
建议模式：深度蒸馏（全面提取 borrowable 模式）

确认？或调整优先级（如"重点做世界观和人物"）：
```

### Phase 2：子 agent 并行蒸馏

**核心变更**：支持多维度并行蒸馏，每个维度由独立子 agent 执行。

#### 并行策略

根据作品画像的维度权重，分配蒸馏资源：

| 维度权重 | 并行策略 | model 推荐 |
|---------|---------|-----------|
| score >= 8 | 独立子 agent，深度蒸馏 | sonnet |
| score 5-7 | 独立子 agent，标准蒸馏 | haiku |
| score < 5 | 主 agent 串行，快速提取 | haiku |

**并行上限**：最多 3 个子 agent 同时运行，避免 DB 写入冲突。

#### 子 agent 分发

```
1. 根据画像 recommended_path 排列维度
2. 按权重分组：高权重组(agent_1) + 中权重组(agent_2) + 低权重组(主agent串行)
3. 每个子 agent 接收：
   - 维度列表
   - 相关卷范围（从 Phase 1 卷摘要定位）
   - 作品类型标签（用于适配提取重点）
   - 输出 schema
```

#### 维度蒸馏 Schema（每个维度含类型适配提示）

##### 维度 1：世界观

```json
{
  "geography": [
    {"name": "地区名", "description": "描述", "significance": "叙事作用"}
  ],
  "history": [
    {"event": "事件名", "era": "时代", "impact": "对当前的影响"}
  ],
  "races": [
    {"name": "种族名", "traits": "特征", "relations": "与其他种族关系"}
  ],
  "culture": [
    {"aspect": "文化方面", "description": "描述", "narrative_role": "在故事中的表现"}
  ],
  "world_rules": [
    {"rule": "世界规则", "description": "描述", "how_shown": "如何展现给读者"}
  ],
  "_type_hint": "西幻作品重点关注种族关系和魔法体系对地理的影响；都市作品重点关注社会结构"
}
```

存储（维度级汇总）：
```bash
world_upsert(
  novel_name="_参考库",
  category="ref_world",
  name="{作品名}",
  data={...世界观数据（不含 borrowable）...},
  tags=["{作品名}", "world", "{genre}"],
  writing_guide="借鉴要点：..."
)
```

##### 维度 2：能力体系

```json
{
  "system_name": "体系名",
  "classification": "分类方式（元素/流派/属性）",
  "tiers": [
    {"level": "等级名", "description": "描述", "requirements": "晋升条件"}
  ],
  "combat": {
    "style": "战斗风格",
    "key_techniques": ["技法列表"],
    "power_ceiling": "力量上限如何控制"
  },
  "social_impact": "能力体系对社会结构的影响",
  "uniqueness": "与其他作品能力体系的区别",
  "_type_hint": "修仙作品关注修炼路径和瓶颈；西幻作品关注元素亲和和天赋树"
}
```

存储：`world_upsert(category="ref_ability", name="{作品名}")`

##### 维度 3：人物

对每个核心人物：

```bash
character_create(
  novel_name="_参考库",
  name="{人物名}@{作品名}",
  role="protagonist/antagonist/...",
  personality="...",
  background="...",
  goals="...",
  speech_style="...",
  arc_notes="成长弧线摘要",
  growth_trajectory="[{from: '初始', to: '最终', trigger: '触发事件'}]"
)
```

关系网络：
```bash
relation_create(
  novel_name="_参考库",
  from_name="{A}@{作品名}",
  to_name="{B}@{作品名}",
  relation_type="...",
  description="..."
)
```

人物总体分析：
```bash
world_upsert(
  novel_name="_参考库",
  category="ref_characters",
  name="{作品名}",
  data={
    "protagonist_pattern": "主角模式描述",
    "supporting_strategy": "配角策略",
    "villain_design": "反派设计",
    "relationship_web": "关系网模式"
  }
)
```

##### 维度 4：叙事手法

```json
{
  "pov": "视角方式",
  "pacing_pattern": "整体节奏模式",
  "hook_types": [
    {"type": "钩子类型", "examples": "具体例子", "effect": "效果"}
  ],
  "foreshadowing": [
    {"planted": "伏笔内容", "recalled": "回收方式", "span": "跨度"}
  ],
  "unique_techniques": [
    {"name": "技法名", "description": "描述", "example": "原文片段"}
  ],
  "info_delivery": "信息投放方式"
}
```

存储：`world_upsert(category="ref_narrative", name="{作品名}")`

##### 维度 5：节奏结构

```json
{
  "arc_structure": "弧段结构描述",
  "warm_arcs": [{"range": "章节范围", "content": "温暖弧内容", "hidden_hook": "暗线钩子"}],
  "cold_arcs": [{"range": "章节范围", "content": "冷色弧内容", "payoff": "兑现的伏笔"}],
  "climax_design": [{"position": "位置", "build_up": "蓄力方式", "release": "释放方式"}],
  "daily_vs_progression": "日常与推进的占比和交替模式"
}
```

存储：`world_upsert(category="ref_rhythm", name="{作品名}")`

##### 维度 6：核心亮点

```json
{
  "unique_selling_points": [
    {"point": "亮点", "why_works": "为什么有效"}
  ],
  "reader_hooks": ["读者留存的关键要素"],
  "innovations": ["创新之处"],
  "failures_or_risks": ["可能的失败点或风险"],
  "overall_assessment": "综合评价",
  "recommended_for": ["适合借鉴的小说类型"]
}
```

存储：`world_upsert(category="ref_highlight", name="{作品名}")`

### Phase 3：borrowable 模式提取 + 独立存储

**核心变更**：borrowable 不再嵌在维度 JSON 内，而是作为一级实体独立存储。

#### 提取规则

每个子 agent 在完成维度蒸馏后，从维度数据中提取 borrowable 模式。提取标准：

| 级别 | 标准 | 标签 |
|------|------|------|
| 可直接用 | 模式通用，不依赖特定世界观 | `usability: direct` |
| 需改编 | 模式有价值，但需适配当前世界观 | `usability: adapt` |
| 仅灵感 | 概念启发，需大幅改造 | `usability: inspire` |

#### 独立存储格式

每个 borrowable 模式独立一条 `world_upsert`：

```bash
world_upsert(
  novel_name="_参考库",
  category="ref_borrowable",
  name="{作品名}-{模式ID}",  # 如 "无职转生-borrow-001"
  data={
    "pattern_name": "模式名称",
    "source_work": "{作品名}",
    "source_dimension": "ability",
    "source_chapters": "第X卷第Y章",
    "description": "模式描述（2-3句）",
    "mechanism": "运作机制详解",
    "example": "原文中的具体表现",
    "usability": "direct|adapt|inspire",
    "applicable_genres": ["西幻", "暗黑奇幻"],
    "applicable_dimensions": ["ability", "world"],
    "adapt_notes": "如需改编，需要改什么",
    "tags": ["能力体系", "等级设计", "晋升机制"]
  }
)
```

#### 批量提取流程

```
1. 汇总所有维度的 borrowable 候选
2. 对每个候选：
   a. 评估 universality：是否脱离原世界观依然成立？
   b. 评估 novelty：是否比常见模式有创新？
   c. 评估 adaptability：改编难度如何？
3. 评分 >= 6 的候选 → 存储为独立 borrowable
4. 评分 < 6 的候选 → 留在维度 JSON 的 borrowable 数组中作为参考
```

### Phase 4：蒸馏报告 + 下游消费指引

完成蒸馏后，输出增强版报告：

```markdown
# {作品名} 蒸馏报告

## 基础信息
- 类型：{genre_tags}
- 卷数：{N}
- 核心人物：{M} 人
- 蒸馏模式：{deep/focused/quick}

## 维度权重（画像）
| 维度 | 权重 | 状态 | 提取量 |
|------|------|------|--------|
| 能力体系 | 9 | 已蒸馏 | {N} 等级, {M} 技法 |
| 世界观 | 8 | 已蒸馏 | {N} 地区, {M} 种族 |
| 叙事手法 | 7 | 已蒸馏 | {N} 技法, {M} 伏笔 |

## Borrowable 模式库
### 可直接借鉴（{N}个）
1. [B-{作品名}-001] {模式名} — {一句话}
2. [B-{作品名}-002] {模式名} — {一句话}

### 需改编（{N}个）
1. [B-{作品名}-003] {模式名} — {一句话}（需改：{改什么}）

### 仅灵感（{N}个）
1. [B-{作品名}-004] {模式名} — {一句话}

## 下游消费指引
### 建世界观时可用
- vector_search(novel_name="_参考库", query_text="genre:{你的类型} dimension:world usability:direct")
- 检索 "无职转生" 的世界观数据：
  db_search(novel_name="_参考库", keyword="无职转生", category="ref_world")

### 设计能力体系时可用
- 检索 borrowable 模式：
  vector_search(novel_name="_参考库", query_text="能力体系 晋升机制 等级设计")
- 精准取某模式：
  db_search(novel_name="_参考库", keyword="无职转生-borrow-001", category="ref_borrowable")

### 设计人物时可用
- 检索人物模式：
  db_search(novel_name="_参考库", keyword="{作品名}", category="ref_characters")
```

## 检索接口（其他 skill 使用）

### 精准检索 borrowable 模式（PP-3 协议增强）

```
# 按维度 + 适用类型检索
vector_search(novel_name="_参考库", query_text="{目标维度} {目标类型} 直接可用")
→ 返回 ref_borrowable 类别的匹配模式

# 按模式 ID 精确取
db_search(novel_name="_参考库", keyword="{作品名}-borrow-{NNN}", category="ref_borrowable")

# 按维度取维度汇总
db_search(novel_name="_参考库", keyword="{作品名}", category="ref_{dimension}")
```

### 在 novel-setup 中使用

当用户说"参考XX小说的YY"时：

```
1. 优先检索 borrowable 模式（最精准）：
   vector_search(novel_name="_参考库", query_text="{作品名} {YY相关关键词}")
2. IF borrowable 命中 → 返回模式 + 适配建议（adapt_notes）
3. IF 无 borrowable → 回退到维度级检索：
   db_search(novel_name="_参考库", keyword="{作品名}", category="ref_{最相关维度}")
4. IF 结果为空 → 提示该作品尚未蒸馏，是否现在蒸馏？
5. 返回数据，PP-3 协议执行适配验证
```

### 直接查询

用户可随时查询已蒸馏的参考数据：

```
"无职转生的能力体系怎么样" →
  vector_search(novel_name="_参考库", query_text="无职转生 能力体系")
  + db_search(novel_name="_参考库", keyword="无职转生", category="ref_ability")

"有什么可直接用的等级晋升模式" →
  vector_search(novel_name="_参考库", query_text="等级 晋升 直接可用")
  → 返回 ref_borrowable 中 usability:direct 的匹配项
```

## 大文件处理策略

| 文件大小 | 策略 |
|---------|------|
| < 2000 行 | 一次读取 |
| 2000-10000 行 | 分段读取（每段 800 行，重叠 50 行） |
| > 10000 行 | Phase 1 仅读首尾+每卷首章，Phase 2 按维度精准读取相关卷 |

分段读取实现：
```bash
# Phase 1：分段摘要
for i in $(seq 1 $SEGMENTS); do
  offset=$(( (i-1) * 800 + 1 ))
  Read {path} offset=$offset limit=850
  → 提取摘要
done

# Phase 2：精准定位
根据 Phase 1 的卷摘要 → 确定目标维度对应的卷范围 → 只读这些卷
```

## 类型适配指南

不同作品类型的蒸馏重点差异：

| 作品类型 | 优先蒸馏维度 | 特殊关注点 |
|---------|------------|-----------|
| 西幻/奇幻 | 能力体系 > 世界观 | 种族关系、魔法体系底层逻辑 |
| 修仙/玄幻 | 能力体系 > 节奏 | 修炼路径、境界突破、资源争夺 |
| 都市/现代 | 人物 > 叙事 | 人际关系、社会阶层、职业细节 |
| 科幻 | 世界观 > 能力体系 | 科技设定、社会结构、时间线 |
| 悬疑/推理 | 叙事手法 > 节奏 | 伏笔布局、信息控制、误导手法 |
| 恋爱/日常 | 人物 > 节奏 | 情感推进、日常描写、关系变化 |

画像生成时，根据 genre_tags 自动匹配上述优先级，调整 recommended_path。

## 质量保障

1. **交叉验证**：人物关系与世界观设定交叉检查一致性
2. **引用溯源**：每条提取数据标注来源章节范围
3. **避免过度解读**：只提取文本中明确存在的内容，不推测作者意图
4. **借鉴定级**：每个 borrowable 模式标注适用范围（direct/adapt/inspire）
5. **并行写入安全**：子 agent 间按维度隔离写入，category 不重叠，避免冲突
6. **画像一致性**：Phase 3 的 borrowable 提取结果回写后，更新 Phase 1 画像中的实际蒸馏状态

## 禁止

- 不编造原文没有的内容
- 不做主观价值判断（不说"写得好/写得差"，只描述"怎么写的"）
- 不存储完整原文段落（只存结构化提取结果）
- 不跳过 Phase 1 直接进入 Phase 2
- 不让 borrowable 模式脱离来源维度标签（每条模式必须标注 source_dimension）
- 不在子 agent 间共享可变状态（每个 agent 只写自己负责的维度 category）
