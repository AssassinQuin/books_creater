---
name: novel-distill
description: >
  参考作品蒸馏引擎。输入小说文件路径，先粗提取作品画像并推荐维度优先级，
  子agent并行蒸馏所选维度，borrowable模式独立存储便于精准下锅。
  触发词：蒸馏XX/分析小说/拆解小说/蒸馏参考
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

# 参考作品蒸馏引擎

## 触发

用户说"蒸馏XX""分析小说""拆解小说""蒸馏参考"。

## 核心概念

**`_参考库`**：novel-db 中的特殊小说名，存储所有参考作品的蒸馏数据。不绑定任何具体小说，全局共享。

**三阶段流程**：
- Phase 1 粗提取 + 作品画像（快速扫描 -> 识别类型 -> 推荐维度优先级）
- Phase 2 精准蒸馏（定位 -> 子agent并行蒸馏 -> borrowable独立存储）
- Phase 3 蒸馏报告 + 下游消费指引

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

**目标**：快速识别作品骨架，输出作品画像和推荐维度优先级，而非均等菜单。

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

#### Step 1.3：维度覆盖检测

基于摘要，判断 6 个维度中哪些有实质内容：

| 维度 | 检测信号 |
|------|---------|
| 世界观 | 出现地理描述/历史事件/种族/文化 |
| 能力体系 | 出现等级/技能/修炼/战斗描述 |
| 人物 | 出现多人物互动/关系变化/成长 |
| 叙事手法 | 出现伏笔/悬念/视角切换/非线性叙事 |
| 节奏结构 | 可识别弧段/高潮/日常/转折 |
| 核心亮点 | 独特设定/创新手法/高口碑要素 |

#### Step 1.4：作品画像生成（新增）

基于 Step 1.2-1.3 的结果，生成作品画像：

```bash
world_upsert(
  novel_name="_参考库",
  category="ref_meta",
  name="{作品名}",
  data={
    "title": "{作品名}",
    "author": "{作者}",
    "genre": "{类型}",
    "subgenre": "{细分类型}",
    "volumes": [...],
    "volume_summaries": {...},
    "work_profile": {
      "type_signature": "{作品类型签名：如'公路旅行+成长'/'权谋+阵营战'}",
      "strength_dimensions": ["最强维度1", "最强维度2"],
      "dimension_priority": [
        {"dimension": "叙事手法", "priority": 1, "reason": "多视角切换、长线伏笔"},
        {"dimension": "人物", "priority": 2, "reason": "群像刻画丰富"},
        {"dimension": "节奏结构", "priority": 3, "reason": "冷暖弧交替明显"},
        {"dimension": "世界观", "priority": 4, "reason": "中规中矩"},
        {"dimension": "能力体系", "priority": 5, "reason": "设定较简单"},
        {"dimension": "核心亮点", "priority": 6, "reason": "无明显创新"}
      ],
      "distillation_focus": "叙事手法、人物、节奏结构"
    }
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

#### Step 1.5：输出推荐菜单（替代原均等菜单）

输出给用户：

```
{作品名} 粗提取完成：
- {N} 卷，{M} 章
- 作品类型：{type_signature}
- 推荐蒸馏优先级：{distillation_focus}（基于作品特征自动排序）

可蒸馏维度（按推荐优先级）：
  [1] 叙事手法 ★★★ — 多视角切换、长线伏笔，本作核心优势
  [2] 人物     ★★★ — 群像刻画丰富，关系网复杂
  [3] 节奏结构 ★★☆ — 冷暖弧交替明显，有借鉴价值
  [4] 世界观   ★☆☆ — 中规中矩
  [5] 能力体系 ★☆☆ — 设定较简单
  [6] 核心亮点 — 独特要素和创新点

选择要深入蒸馏的维度（可多选，如 1,2,4。留空则蒸馏推荐维度 1-3）：
```

### Phase 2：精准蒸馏（用户选维度后）

用户选择维度后，执行三步子流程。

#### Step 2a：定位（确定蒸馏范围）

```
1. 根据所选维度和维度优先级，生成蒸馏计划
2. 对每个维度，用 Phase 1 的卷摘要定位相关章节：
   - 世界观 → 出现地理/历史/种族/文化的卷
   - 能力体系 → 出现战斗/修炼/能力描述的卷
   - 人物 → 出现角色互动/成长的卷
   - 叙事手法 → 全卷扫描（需伏笔/悬念等跨卷要素）
   - 节奏结构 → 全卷扫描（需弧段交替模式）
   - 核心亮点 → 根据检测信号定位具体卷
3. 输出蒸馏计划：
   "维度 [1] 叙事手法 → 卷 1,3,5,7（含视角切换/伏笔关键卷）
    维度 [2] 人物     → 卷 2,4,6（角色成长密集卷）"
4. 用户确认计划后进入 2b
```

#### Step 2b：子agent并行蒸馏

**当选择多个维度时，启动子agent并行处理**，每个子agent负责一个维度。

并行调度规则：
```bash
# 伪代码
selected_dimensions = 用户选择的维度列表
IF len(selected_dimensions) >= 2:
    # 并行模式：每个维度一个子agent
    FOR dim IN selected_dimensions:
        Agent(
          model="sonnet",  # R5.1: 推理任务用sonnet
          task="执行 {作品名} 维度 [{dim}] 的细蒸馏。
                读取定位章节，按维度schema提取结构化数据，
                输出JSON结果。
                文件路径：{path}
                定位章节：{定位结果}
                维度schema：见下方定义",
          allowed_tools=["Read", "Grep"]
        )
    # 收集所有子agent结果
    收集并验证结果完整性
ELSE:
    # 单维度模式：主agent直接执行
    按维度schema提取
END IF
```

每个子agent的执行逻辑：

```
1. 读取该维度定位的章节全文（分段读取，避免爆 context）
2. 按维度 schema 提取结构化数据
3. 输出提取结果的 JSON
4. 主agent收集结果后统一写入 _参考库
```

**维度 Schema 定义**：

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
  ]
}
```

存储：
```bash
world_upsert(
  novel_name="_参考库",
  category="ref_world",
  name="{作品名}",
  data={...世界观数据...},
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
  "borrowable": ["可直接借鉴的模式"]
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
    "relationship_web": "关系网模式",
    "borrowable": ["可借鉴的人物设计模式"]
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
  "info_delivery": "信息投放方式",
  "borrowable": ["可借鉴的叙事模式"]
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
  "daily_vs_progression": "日常与推进的占比和交替模式",
  "borrowable": ["可借鉴的节奏模式"]
}
```

存储：`world_upsert(category="ref_rhythm", name="{作品名}")`

##### 维度 6：核心亮点

```json
{
  "unique_selling_points": [
    {"point": "亮点", "why_works": "为什么有效", "how_to_borrow": "如何借鉴"}
  ],
  "reader_hooks": ["读者留存的关键要素"],
  "innovations": ["创新之处"],
  "failures_or_risks": ["可能的失败点或风险"],
  "overall_assessment": "综合评价",
  "recommended_for": ["适合借鉴的小说类型"]
}
```

存储：`world_upsert(category="ref_highlight", name="{作品名}")`

#### Step 2c：borrowable 模式独立存储（新增）

每个维度的蒸馏结果中，将 `borrowable` 字段拆出，逐条独立存储，便于下游精准检索和"部分下锅"。

```bash
# 从每个维度的蒸馏结果中提取 borrowable 列表
# 每个模式存储为独立记录
FOR dim IN 已蒸馏维度列表:
    borrowable_list = 蒸馏结果[dim].borrowable
    FOR i, pattern IN enumerate(borrowable_list):
        world_upsert(
          novel_name="_参考库",
          category="ref_borrowable",
          name="{作品名}-{dim}-{pattern摘要}",
          data={
            "source_work": "{作品名}",
            "source_dimension": "{维度名}",
            "source_dimension_id": dim,
            "pattern_name": pattern,
            "pattern_detail": pattern的详细描述,
            "applicability": "直接可用/需改编/仅灵感",
            "adaptation_notes": "改编建议",
            "related_dimensions": ["关联维度"],
            "chapter_range": "{来源章节范围}"
          },
          tags=["{作品名}", "borrowable", "{维度名}", "{applicability}"]
        )
```

**部分下锅接口**：下游skill可按维度+适用性精准检索：

```bash
# 检索某类可借鉴模式（不绑定具体作品）
vector_search(
  novel_name="_参考库",
  query_text="{目标需求} 借鉴模式",
  filter={"category": "ref_borrowable"}
)

# 检索特定作品的特定维度
db_search(
  novel_name="_参考库",
  keyword="{作品名}",
  filter={"category": "ref_borrowable", "source_dimension": "叙事手法"}
)

# 按适用性筛选
db_search(
  novel_name="_参考库",
  keyword="直接可用",
  filter={"category": "ref_borrowable"}
)
```

### Phase 3：蒸馏报告 + 下游消费指引

完成细蒸馏后，输出合并报告。

#### Step 3.1：蒸馏报告

```markdown
# {作品名} 蒸馏报告

## 基础信息
- 类型：{type_signature}
- 卷数：{N}
- 核心人物：{M} 人

## 作品画像
- 推荐蒸馏维度：{distillation_focus}
- 类型特征：{subgenre}

## 已蒸馏维度
- [x] 世界观：{N} 地区, {M} 历史事件, {K} 种族
- [x] 能力体系：{体系名}，{N} 等级，{M} 技法
- [ ] 人物：未选择
- [x] 叙事手法：{N} 钩子类型, {M} 伏笔, {K} 独有技法
- [ ] 节奏：未选择
- [x] 亮点：{N} 个核心卖点

## 可借鉴模式（独立存储，可精准下锅）
| # | 模式 | 来源维度 | 适用性 | 改编建议 |
|---|------|---------|--------|---------|
| 1 | {模式1} | 叙事手法 | 直接可用 | ... |
| 2 | {模式2} | 节奏结构 | 需改编 | ... |
| 3 | {模式3} | 人物 | 仅灵感 | ... |

## 检索测试
- 搜索"{关键词}" → 命中 {N} 条
```

#### Step 3.2：下游消费指引（新增）

输出下游 skill 如何使用本次蒸馏结果：

```markdown
## 下游消费指引

### novel-setup 使用方式
- 建立世界观时说"参考{作品名}的{维度}"即可精准检索
- borrowable模式已独立存储，可按适用性（直接可用/需改编/仅灵感）筛选

### novel-character 使用方式
- 人物蒸馏已存入 _参考库，说"参考{作品名}的{人物名}的角色设计"
- 人物总体分析含 borrowable 模式，可独立引用

### novel-plan 使用方式
- 节奏结构可按弧段引用，不必加载整个维度
- 叙事手法的 foreshadowing 可独立检索具体伏笔模式

### 检索命令示例
- "搜索无职转生的可借鉴模式" → 返回所有 ref_borrowable 记录
- "搜索直接可用的节奏模式" → 按适用性筛选
- "参考权游的反派设计" → 精准命中 ref_characters 中的 villain_design
```

## 检索接口（其他 skill 使用）

### 在 novel-setup 中使用（PP-3 协议）

当用户说"参考XX小说的YY"时：

```
1. vector_search(novel_name="_参考库", query_text="{作品名} {维度}")
2. IF 结果为空 → db_search(novel_name="_参考库", keyword="{作品名}")
3. IF 仍为空 → 提示该作品尚未蒸馏，是否现在蒸馏？
4. 返回蒸馏数据，PP-3 协议执行适配验证
```

### 部分下锅接口（新增）

当用户说"借鉴XX的模式"/"类似XX的写法"时：

```
1. vector_search(novel_name="_参考库", query_text="{需求描述} 借鉴模式",
                  filter={"category": "ref_borrowable"})
2. IF 结果为空 → db_search(novel_name="_参考库", keyword="{关键词}",
                             filter={"category": "ref_borrowable"})
3. 返回匹配的 borrowable 模式列表（含来源维度、适用性、改编建议）
4. 下游 skill 根据适用性决定适配策略
```

### 直接查询

用户可随时查询已蒸馏的参考数据：

```
"无职转生的能力体系怎么样" →
  vector_search(novel_name="_参考库", query_text="无职转生 能力体系")

"有什么直接可用的叙事模式" →
  vector_search(novel_name="_参考库", query_text="借鉴模式 叙事",
                filter={"category": "ref_borrowable", "applicability": "直接可用"})
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

## 子agent并行规范

| 维度数 | 模式 | model | 说明 |
|-------|------|-------|------|
| 1 | 主agent直接执行 | - | 无并行开销 |
| 2-3 | 并行子agent | sonnet | 每维度一个子agent，主agent汇总 |
| 4-6 | 分批并行 | sonnet | 每批 3 个子agent，避免资源竞争 |

并行子agent必须遵守：
- 每个 子 agent 限读 3000 行（避免爆 context）
- 子 agent 输出 JSON 格式，主 agent 校验后写入 DB
- 任一 子 agent 失败 → 主 agent 降级为串行模式重试该维度

## 质量保障

1. **交叉验证**：人物关系与世界观设定交叉检查一致性
2. **引用溯源**：每条提取数据标注来源章节范围
3. **避免过度解读**：只提取文本中明确存在的内容，不推测作者意图
4. **借鉴定级**：每个 borrowable 模式标注适用范围（直接可用/需改编/仅灵感）
5. **子agent输出校验**：主 agent 汇总时检查 JSON 完整性，缺失字段回填

## 禁止

- 不编造原文没有的内容
- 不做主观价值判断（不说"写得好/写得差"，只描述"怎么写的"）
- 不存储完整原文段落（只存结构化提取结果）
- 不跳过 Phase 1 直接进入 Phase 2
- 不在子agent并行时共享未校验的中间结果
