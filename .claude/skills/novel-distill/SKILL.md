---
name: novel-distill
description: >
  参考作品蒸馏引擎。批露式架构：编排器调度6个维度子agent模块，
  每个模块引用对应元skill方法论指导蒸馏。borrowable独立存储+向量+ctx_index三通道检索。
  触发词：蒸馏XX/分析小说/拆解小说/蒸馏参考
allowed-tools:
  - mcp__novel-db__*
  - mcp__novel-db__skill_loader
  - mcp__plugin_context-mode_context-mode__ctx_index
  - mcp__plugin_context-mode_context-mode__ctx_search
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
version: "3.2.0"
---

# 参考作品蒸馏引擎

## 触发

用户说"蒸馏XX""分析小说""拆解小说""蒸馏参考"。

## 核心概念

**`_参考库`**：novel-db 中的特殊小说名，存储所有参考作品的蒸馏数据。不绑定任何具体小说，全局共享。

**三阶段流程**：
- Phase 1 粗提取 + 作品画像（快速扫描 -> 类型识别 -> 推荐维度优先级）
- Phase 2 精准蒸馏（定位 -> skill_loader加载维度模块 -> 子agent并行蒸馏 -> borrowable独立存储 -> 向量索引）
- Phase 3 蒸馏报告 + 下游消费指引

**批露式架构**：
- 6个维度各有独立 agent 模块（`agents/dim-{维度}.md`）
- 每个模块引用对应元 skill 方法论（通过 skill_loader）
- 编排器（本文件）负责调度，子agent执行具体维度蒸馏
- 维度模块可独立更新，不影响其他维度

**三通道检索**：
- ctx_index 知识库：蒸馏完成后自动索引，下游 skill 用 `ctx_search` 快速检索（最快，省 token）
- DB 向量检索：`vector_search` / `db_search` 语义精准查找
- borrowable 独立存储：每个可借鉴模式单独可查

## 执行流程

### Phase 0：输入确认 + 类型识别

```
1. 获取文件路径（用户直接给，或追问）
2. 验证文件存在：ls {path}
3. IF 文件不存在 → 追问正确路径
4. 文件内容校验：
   - head -20 {path} | grep -c "[\x80-\xff]" → IF = 0 → 可能非文本文件或乱码 → 报错终止
   - wc -c {path} → IF = 0 → 空文件 → 报错终止
5. 文件信息统计：
   - wc -l {path}（行数）
   - grep -c "^第.*章\|^Chapter\|^\*\*\*" {path}（章节数估计）
6. 输出概要："文件 {name}，{lines} 行，约 {chapters} 章，预计 Phase 1 耗时 {est}"
7. IF 文件 > 2000 行 → 提示将分段读取
8. 类型识别：读取前 200 行，按关键词匹配作品类型（见类型信号表）
9. 向量辅助识别（可选）：
   - 读取前 500 行内容摘要
   - vector_search(novel_name="_参考库", query_text="{摘要前100字}")
   - IF 命中已有蒸馏作品 → 对比类型标签辅助确认
```

**类型信号检测表**：

| 优先级 | 信号关键词 | 作品类型 |
|--------|-----------|---------|
| 1 | 修仙/灵气/渡劫/飞升/金丹/元婴/宗门 | 东方玄幻 |
| 2 | 异世界/转生/召唤/穿越/游戏系统 | 异世界/穿越 |
| 3 | 蒸汽/机械/齿轮/炼金/维多利亚 | 蒸汽朋克 |
| 4 | 克苏鲁/诡异/不可名状/古神 | 克苏鲁/诡异 |
| 5 | 魔法/骑士/精灵/龙/公会/领主 | 西幻 |
| 6 | 科幻/星际/赛博/量子/AI | 科幻 |
| 7 | 城市/学校/公司/现代/异能/觉醒 | 都市 |
| 8 | 朝代/皇帝/将军/科举/战争 | 历史架空 |
| 0 | 以上均不匹配 | 通用 |

匹配方法：统计前 200 行中各类型信号词出现次数，取最高频。最高频 ≤ 2 次 → 标记为"通用"。

**维度优先级映射表**：

| 作品类型 | ★★★ 深蒸馏 | ★★ 标准蒸馏 | ★ 快速扫描 |
|---------|-----------|-----------|-----------|
| 东方玄幻 | 能力体系、节奏结构 | 叙事手法、世界观 | 人物、亮点 |
| 异世界/穿越 | 世界观、能力体系 | 节奏结构、人物 | 叙事手法、亮点 |
| 蒸汽朋克 | 世界观、能力体系 | 人物、叙事手法 | 节奏结构、亮点 |
| 克苏鲁/诡异 | 世界观、叙事手法 | 能力体系、节奏结构 | 人物、亮点 |
| 西幻 | 世界观、能力体系 | 人物、叙事手法 | 节奏结构、亮点 |
| 科幻 | 世界观、能力体系 | 叙事手法、节奏结构 | 人物、亮点 |
| 都市 | 人物、叙事手法 | 节奏结构、亮点 | 世界观、能力体系 |
| 历史架空 | 世界观、人物、节奏 | 叙事手法、亮点 | 能力体系 |
| 通用 | 全部 ★★ | — | — |

### Phase 1：粗提取 + 作品画像

**目标**：快速识别作品骨架，输出作品画像和推荐维度优先级。

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

#### Step 1.3：维度覆盖检测 + 密度计算

基于摘要，判断 6 个维度中哪些有实质内容：

| 维度 | 检测信号 |
|------|---------|
| 世界观 | 出现地理描述/历史事件/种族/文化 |
| 能力体系 | 出现等级/技能/修炼/战斗描述 |
| 人物 | 出现多人物互动/关系变化/成长 |
| 叙事手法 | 出现伏笔/悬念/视角切换/非线性叙事 |
| 节奏结构 | 可识别弧段/高潮/日常/转折 |
| 核心亮点 | 独特设定/创新手法/高口碑要素 |

密度计算：
```
density = 该维度信号在卷摘要中出现总次数 / 卷总数
density >= 2 → 高密度（深蒸馏）
density < 2 → 低密度（快速扫描）
```

#### Step 1.4：作品画像生成

```bash
world_upsert(
  novel_name="_参考库",
  category="ref_meta",
  name="{作品名}",
  data={
    "title": "{作品名}",
    "author": "{作者}",
    "genre": "{Phase 0 识别的类型}",
    "volumes": [...],
    "volume_summaries": {...},
    "work_profile": {
      "type_signature": "{类型签名：如'公路旅行+成长'/'权谋+阵营战'}",
      "strength_dimensions": ["最强维度1", "最强维度2"],
      "dimension_priority": [
        {"dimension": "叙事手法", "priority": 1, "reason": "多视角切换、长线伏笔"},
        ...
      ],
      "distillation_focus": "叙事手法、人物、节奏结构"
    },
    "dimension_density": {"世界观": "高", "能力体系": "低", ...}
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

#### Step 1.5：输出推荐菜单

```
{作品名} 粗提取完成：
- {N} 卷，{M} 章
- 作品类型：{type_signature}
- 推荐蒸馏重点：{distillation_focus}

可蒸馏维度（按推荐优先级）：
  [1] 叙事手法 ★★★ — 多视角切换、长线伏笔，本作核心优势
  [2] 人物     ★★★ — 群像刻画丰富，关系网复杂
  [3] 节奏结构 ★★☆ — 冷暖弧交替明显
  [4] 世界观   ★☆☆ — 中规中矩
  [5] 能力体系 ★☆☆ — 设定较简单
  [6] 核心亮点 — 独特要素和创新点

选择要深入蒸馏的维度（可多选，如 1,2,4。留空则蒸馏推荐维度 1-3）：
```

### Phase 2：精准蒸馏（用户选维度后）

用户选择维度后，执行三步子流程。

#### Step 2a：定位（确定蒸馏范围）

```
1. 根据所选维度和优先级，生成蒸馏计划
2. 对每个维度，用 Phase 1 卷摘要定位相关章节：
   - 世界观 → 出现地理/历史/种族/文化的卷
   - 能力体系 → 出现战斗/修炼/能力描述的卷
   - 人物 → 出现角色互动/成长的卷
   - 叙事手法 → 全卷扫描（需伏笔/悬念等跨卷要素）
   - 节奏结构 → 全卷扫描（需弧段交替模式）
   - 核心亮点 → 根据检测信号定位具体卷
3. 输出蒸馏计划，用户确认后进入 2b
```

#### Step 2b：子agent并行蒸馏（批露式调度）

**编排器职责**：为每个维度加载对应模块 + 元 skill 方法论，组装子 agent prompt。

```
FOR dim IN 用户选择的维度列表:
    # 1. 加载维度模块
    dim_module = skill_loader("novel-distill", "agent", "dim-{dim}")

    # 2. 加载对应元 skill 方法论（可选，按维度映射）
    meta_skill = META_SKILL_MAP[dim]
    IF meta_skill != null:
        methodology = skill_loader(meta_skill.skill, meta_skill.level, meta_skill.resource)
    ELSE:
        methodology = ""

    # 3. 组装子 agent prompt
    agent_prompt = assemble_prompt(
        module=dim_module,
        methodology=methodology,
        path=文件路径,
        genre=作品类型,
        priority=维度优先级,
        location=定位章节,
        summaries=卷摘要
    )
END FOR
```

**元 skill 方法论映射**：

| 维度 | 元 skill | skill_loader 调用 |
|------|---------|-----------------|
| world | novel-setup | `skill_loader("novel-setup", "engine", "worldbuilding")` |
| ability | abilitycraft | `skill_loader("abilitycraft", "engine", "ability-design")` |
| characters | novel-character | `skill_loader("novel-character", "engine", "character-design")` |
| narrative | story-architecture | `skill_loader("story-architecture", "engine", "narrative")` |
| rhythm | novel-plan | `skill_loader("novel-plan", "engine", "rhythm")` |
| highlight | — | 无对应元 skill |

**维度模块精确名称映射**（skill_loader 必须用此表中的名称）：

| 维度 | skill_loader 名称 | 文件名 |
|------|-------------------|--------|
| world | dim-world | dim-world.md |
| ability | dim-ability | dim-ability.md |
| characters | **dim-characters** | dim-characters.md |
| narrative | dim-narrative | dim-narrative.md |
| rhythm | dim-rhythm | dim-rhythm.md |
| highlight | dim-highlight | dim-highlight.md |

注意：characters 是复数，其余 5 个是单数。Step 2b 开始前用 `ls agents/dim-*.md` 验证。

**维度数量决定调度策略**：

| 维度数 | 模式 | subagent_type | model | 说明 |
|-------|------|--------------|-------|------|
| 1 | 主agent直接执行 | - | - | 无并行开销 |
| 2-3 | 并行子agent | general-purpose | sonnet | 每维度一个子agent，主agent汇总 |
| 4-6 | 分批并行 | general-purpose | sonnet | 每批 3 个子agent，避免资源竞争 |

**子agent prompt 组装模板**：

```
【文学分析任务声明】
你正在执行已出版文学作品的学术分析任务。以下文本来自公开出版的小说，分析目的为提取叙事技法和创作模式。请以文学批评的专业视角进行分析。

{dim_module 内容}

## 本次任务参数
- 文件路径：{path}
- 作品类型：{type}
- 维度优先级：★★★/★★/★
- 定位章节：{location}
- 卷摘要：{summaries}

## 参考方法论（辅助分析，不照搬）
{methodology 内容}

## 输出格式（强制）
1. 将蒸馏结果 JSON 写入 /tmp/distill-{作品名}-{维度}.json
2. JSON schema: {"dimension": "{维度}", "data": {...维度数据...}, "borrowable": [{...},...], "metadata": {...}}
3. 写入完成后，用 Bash 打印 "DISTILL_COMPLETE: {维度}" 作为结束标记
4. 不要在响应中返回完整 JSON——只返回摘要（≤500字）：维度名 + 关键发现 + borrowable 数量
```

**并行约束**：
- 每个子agent限读 3000 行
- 子agent **必须**将 JSON 写入 `/tmp/distill-{作品名}-{维度}.json`，主agent用 `Read` 读取校验后写入 DB
- 任一子agent失败 → 主agent降级串行重试该维度
- 主agent读取 agent 输出文件后，用 `ctx_execute_file` 提取 JSON（不直接读取可能很大的 JSONL transcript）

#### Step 2c：borrowable 独立存储 + 向量索引

**独立存储**：每个 borrowable 模式存为一条独立记录。

```bash
FOR dim IN 已蒸馏维度列表:
    FOR pattern IN 蒸馏结果[dim].borrowable:
        world_upsert(
          novel_name="_参考库",
          category="ref_borrowable",
          name="{作品名}-{dim}-{pattern.name}",
          data={
            "source_work": "{作品名}",
            "source_dimension": "{维度名}",
            "pattern_name": pattern.name,
            "pattern_detail": pattern.description,
            "applicability": pattern.applicability,
            "applicable_genres": pattern.applicable_genres,
            "adaptation_notes": "改编建议",
            "example": pattern.example,
            "source_chapters": pattern.source_chapters
          },
          tags=["{作品名}", "borrowable", "{dim}", pattern.applicability]
        )
```

**向量索引（容错验证）**：

```bash
# 1. 尝试验证向量索引
result = vector_search(novel_name="_参考库", query_text="{作品名}", top_k=3)
IF result 成功:
    验证 borrowable 可被语义检索命中 ✓
ELSE (MCP bug / NameError):
    降级用 db_search 验证：db_search(novel_name="_参考库", keyword="borrowable", top_k=10)
    标注 "向量验证降级" —— 不阻塞蒸馏完成
```

**borrowable 批量写入策略**：

```
所有 borrowable 由主 agent 直接 FOR 循环调用 world_upsert 写入。
world_upsert 是纯机械 MCP 调用，无需推理能力，不使用子 agent。
按维度分组，每组 ≤15 条串行写入后输出进度。
```

**维度记录去重规则**：

```
维度记录（ref_world/ref_narrative 等）的 data 字段只存 borrowable_summary：
  "borrowable_summary": {
    "count": 10,
    "patterns": ["模式1名", "模式2名", ...]
  }

完整 borrowable（description/example/source_chapters 等）只存在 ref_borrowable 独立记录中。
检索时先用 summary 定位方向，再按 pattern_name 精准查 ref_borrowable 获取详情。
禁止在维度记录中嵌入完整 borrowable 数组。

**文件输出（人可读持久化）**：

蒸馏完成后，在文件系统生成人可读报告：

```bash
# 1. 蒸馏总报告
Write(
  path="参考/{作品名}/蒸馏报告.md",
  content=Phase 3 完整蒸馏报告 markdown
)

# 2. 每个维度的 borrowable 详情
FOR dim IN 已蒸馏维度:
    Write(
      path="参考/{作品名}/borrowable-{dim}.md",
      content=该维度 borrowable 模式的完整详情（含 example + source_chapters）
    )
```

**ctx_index 知识库索引（codemap 化）**：

蒸馏完成后，将蒸馏报告和 borrowable 模式摘要索引到 ctx_index：

```
# 索引蒸馏报告（下游 skill 用 ctx_search 快速检索，不浪费 token）
mcp__plugin_context-mode_context-mode__ctx_index(
  content=蒸馏报告markdown全文,
  source="ref-distill-{作品名}"
)

# 索引 borrowable 模式清单（结构化表格，下游精准命中）
mcp__plugin_context-mode_context-mode__ctx_index(
  content=模式清单表格markdown,
  source="ref-patterns-{作品名}"
)
```

### Phase 3：蒸馏报告 + 下游消费指引

#### Step 3.1：蒸馏报告

```markdown
# {作品名} 蒸馏报告

## 基础信息
- 类型：{type_signature}
- 卷数：{N}
- 核心人物：{M} 人

## 已蒸馏维度
- [x] 世界观 ★★★：{N} 地区, {M} 历史事件
- [x] 能力体系 ★★★：{体系名}，{N} 等级
- [ ] 人物 ★★：未选择
- [x] 叙事手法 ★★★：{N} 钩子类型, {M} 伏笔

## 可借鉴模式（已独立存储 + 向量索引）
| # | 模式 | 来源维度 | 适用性 | 适用类型 |
|---|------|---------|--------|---------|
| 1 | {模式1} | 叙事手法 | direct | 西幻,异世界 |
| 2 | {模式2} | 节奏结构 | adapt | 公路文 |

## 检索验证
- vector_search("{关键词}") → 命中 {N} 条 ✓
- ctx_search("ref-patterns-{作品名}") → 已索引 ✓
```

#### Step 3.2：下游消费指引

#### Step 3.3：下游知识注入（让其他 skill 知道怎么用蒸馏数据）

蒸馏完成后，更新两处确保持久可用：

**1. 更新项目 CLAUDE.md 参考作品区**：

```
在 CLAUDE.md 的参考作品列表中，将已蒸馏作品标记：
  参考作品：无职转生（✓已蒸馏）、权游（待蒸馏）、将夜（✓已蒸馏）

在参考作品下方追加检索入口：
  ### 参考作品检索方式
  - 精准检索模式："参考{作品名}的{维度}" → db_search("_参考库", keyword="{作品名}", category="ref_borrowable", top_k=5)
  - 语义检索模式："找类似XX的模式" → vector_search("_参考库", query_text="XX")
  - 快速查看：ctx_search(queries=["{作品名}"], source="ref-patterns-{作品名}")
  - 文件查阅：参考/{作品名}/蒸馏报告.md
```

**2. 蒸馏摘要注入 ctx_index**（下游 skill 触发时自动可用）：

```
ctx_index(
  content="# {作品名} 蒸馏摘要\n\n## 检索入口\n- db_search('_参考库', keyword='{作品名}', category='ref_borrowable', top_k=5)\n- ctx_search(queries=['{需求}'], source='ref-patterns-{作品名}')\n- 文件：参考/{作品名}/蒸馏报告.md\n\n## 可借鉴模式 TOP 5\n{从 Phase 3 报告中提取 TOP 5 模式的名称+一句话描述}",
  source="ref-summary-{作品名}"
)
```

这样下游 skill 触发时，模型通过 ctx_search 就能发现已蒸馏数据和检索方法。

## 检索接口（其他 skill 使用）

### 三层检索协议

```
L1: ctx_search（最快，token 最省）
    → ctx_search(queries=["{作品名} {需求}"], source="ref-patterns-{作品名}")
    → 命中 → 直接使用，不消耗 DB 查询

L2: vector_search（语义精准）
    → vector_search(novel_name="_参考库", query_text="{需求描述}")
    → 命中 ref_borrowable → 返回模式详情

L3: db_search（兜底，始终带 top_k=10）
    → db_search(novel_name="_参考库", keyword="{关键词}", top_k=10)
    → 命中 → 返回维度数据

L4: 空结果 → 提示"该作品/模式尚未蒸馏，是否现在蒸馏？"
```

### 部分下锅接口

```
# 按模式精准检索（不绑定具体作品）
vector_search(novel_name="_参考库", query_text="{目标需求}")

# 按适用性筛选
db_search(novel_name="_参考库", keyword="direct", category="ref_borrowable", top_k=10)

# 按作品+维度组合
db_search(novel_name="_参考库", keyword="{作品名}", category="ref_{维度}", top_k=5)

# 跨作品找相似模式
vector_search(novel_name="_参考库", query_text="日常蓄力 暴击释放 节奏模式")
```

## 大文件处理策略

| 文件大小 | 策略 |
|---------|------|
| < 2000 行 | 一次读取 |
| 2000-10000 行 | 分段读取（每段 800 行，重叠 50 行） |
| > 10000 行 | Phase 1 仅读首尾+每卷首章，Phase 2 按维度精准读取相关卷 |

## 质量保障

1. **交叉验证**：人物关系与世界观设定交叉检查一致性
2. **引用溯源**：每条提取数据标注来源章节范围
3. **避免过度解读**：只提取文本中明确存在的内容，不推测作者意图
4. **借鉴定级**：borrowable 模式三级标签 direct/adapt/inspire
5. **子agent输出校验**：主agent从 /tmp/distill-{作品名}-{维度}.json 读取，校验 JSON 完整性（dimension/data/borrowable 三字段必须存在），缺失字段回填
6. **向量索引验证**：蒸馏完成后验证 vector_search 可命中 borrowable 模式，失败时降级用 db_search
7. **ctx_index 索引**：蒸馏报告+模式清单+检索摘要自动索引，下游 skill 快速检索
8. **文件持久化**：蒸馏报告+每个维度 borrowable 详情写入 参考/{作品名}/ 目录，人可读
9. **下游知识注入**：更新 CLAUDE.md 参考作品区（标记已蒸馏+检索入口），ctx_index 注入检索摘要
10. **文学分析语境**：子agent prompt 必须包含文学分析任务声明，防止中文原文触发 API 内容安全过滤
11. **命名一致性**：Step 2b 前用 ls agents/dim-*.md 验证模块名，characters 用复数
12. **db_search 结果控制**：所有 db_search 调用必须带 top_k 参数（≤10），避免一次性拉回全量数据
13. **borrowable 去重存储**：维度记录只存 borrowable_summary（count+pattern names），完整数据只在 ref_borrowable 中

## 禁止

- 不编造原文没有的内容
- 不做主观价值判断（不说"写得好/写得差"，只描述"怎么写的"）
- 不存储完整原文段落（只存结构化提取结果）
- 不跳过 Phase 1 直接进入 Phase 2
- 不在子agent并行时共享未校验的中间结果
- 不将 borrowable 模式只嵌在维度 JSON 内而不独立存储
- 不在维度记录中嵌入完整 borrowable 数组（只存 summary）
- 不使用子 agent 执行纯机械的 world_upsert 循环写入
- 不在 db_search 中省略 top_k 参数
