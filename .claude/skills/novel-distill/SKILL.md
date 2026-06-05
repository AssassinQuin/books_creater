---
name: novel-distill
description: >
  参考作品蒸馏引擎 v4.0.0。项目方向感知蒸馏：检测活跃项目品类需求，
  按相关度定向提取 borrowable 模式。中性化输出（抽象属性映射）。
  批露式架构：编排器调度6维度子agent，每个引用对应元skill方法论。
  三通道检索：ctx_index + DB向量 + keyword。文件统一归档+tmp自动清理。
  触发词：蒸馏XX/分析小说/拆解小说/蒸馏参考/导入蒸馏/深化蒸馏
allowed-tools:
  - mcp__novel-db__*
  - mcp__novel-db__skill_loader
  - mcp__plugin_context-mode_context-mode__ctx_index
  - mcp__plugin_context-mode_context-mode__ctx_search
  - mcp__plugin_context-mode_context-mode__ctx_execute_file
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
version: "4.0.0"
---

# 参考作品蒸馏引擎 v4.0.0

## 核心概念

**`_参考库`**：novel-db 特殊小说名，存储所有参考作品蒸馏数据，全局共享。

**项目方向感知**（v4.0 新增）：
- Phase 0 检测活跃项目（从 CLAUDE.md 提取 genre/theme/needs）
- Phase 1 按项目需求对维度打相关度分（1-5）
- borrowable 新增 `project_relevance` 字段：`{project_name: {score, reason}}`
- 蒸馏报告按相关度排序，高相关模式优先展示

**批露式架构**：6个维度各有独立 agent 模块（`agents/dim-{dim}.md`），编排器调度。

**三通道检索**：ctx_index（最快）→ DB向量（语义精准）→ keyword（兜底）。

**文件管理**（v4.0 重构）：
- 子agent 输出：`/tmp/distill-{作品名}/` 目录（OS 临时，非项目根）
- 最终归档：`novels/_参考库/{作品名}/` 单层目录
- Phase 3 末尾：强制清理 `/tmp/distill-{作品名}/`

**中性化输出**（v4.0 强化）：
- source_context：抽象描述设定基底，禁止原作术语
- replacement_guide：抽象属性要求，禁止具名替换
- 子agent prompt 含"中性化审计"步骤

## 执行流程

### Phase 0：输入确认 + 项目方向检测

```
1. 获取文件路径（用户直接给，或追问）
2. 验证文件：
   - ls {path} → 不存在 → 追问正确路径
   - head -20 {path} | grep -c "[\x80-\xff]" → = 0 → 可能非文本 → 报错终止
   - wc -c {path} → = 0 → 空文件 → 报错终止
3. 文件统计：wc -l → 行数；grep -c "^第.*章|^Chapter|^\*\*\*" → 章节估计
4. 输出概要："文件 {name}，{lines} 行，约 {chapters} 章"
4. 类型识别：前200行关键词匹配（见下表）
5.【v4.0】项目方向检测：
   a. 从 CLAUDE.md 读取 Active Project 的 genre/theme/needs
   b. 提取项目品类标签（如：纯西幻/暗黑奇幻/公路文/种田文）
   c. 若无活跃项目 → 通用模式（等同 v3.5）
   d. 输出："检测到活跃项目「{name}」({genre})，蒸馏将优先提取对{genre}有价值的模式"
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

**【v4.0】项目方向维度优先级覆盖**：

当检测到活跃项目时，根据项目品类调整优先级：

```
IF 活跃项目品类 == "西幻/暗黑奇幻":
    对所有参考作品，以下维度优先级提升：
    - 能力体系：★★★（多分支体系设计参考）
    - 世界观：★★★（设定揭示方式参考）
    - 节奏结构：★★★（百万字节奏参考）
    - 叙事手法：★★（信息投放/伏笔管理）
    - 人物：★★（群像/反派设计）
    - 亮点：★（创新点灵感）
```

其他品类按项目需求自行调整（上表仅为示例）。通用规则：与项目品类越近的参考作品，蒸馏优先级越高。

**project_relevance 评分锚点**：
- 5分=品类一致且模式直接可用（如西幻项目蒸馏西幻作品的能力体系）
- 3分=品类不同但模式可适配（如西幻项目蒸馏东方玄幻的节奏结构）
- 1分=品类差异大仅可取灵感（如西幻项目蒸馏蒸汽朋克的机械设定）

### Phase 1：粗提取 + 作品画像

```
1. 结构识别：分段读取（500-800行/段，50行重叠），识别卷/章结构
2. 逐卷快速摘要（每卷限200字）：核心事件 / 人物 / 设定 / 情绪基调
3. 维度覆盖检测：6维度信号密度计算
4.【v4.0】项目相关度评分：
   FOR dim IN 6维度:
       relevance = 计算该维度对活跃项目品类的有用度（1-5分）
       → 基于：品类匹配度 + 项目缺失度 + 已有参考作品覆盖度
   输出相关度排序，供用户确认
5. 作品画像写入 DB：write_to_storage("_参考库", "ref_meta", "{作品名}", ...)
6. 卷摘要写入 DB：write_to_storage("_参考库", "ref_volume", ...)
```

**write_to_storage 降级链**：
```
L1: world(action="upsert") → 成功则返回
L2: Write("novels/_参考库/{作品名}/distill/{category}-{name}.json") → 成功则返回
L3: Write("/tmp/distill-{作品名}/{category}-{name}.json") → 应急
```

### Phase 1.5：已有数据导入

**触发条件**：Phase 1 完成后自动执行，或用户独立触发。

```
1. 扫描已有数据源（按优先级）：
   a. novels/_参考库/{作品名}/distill/*.json
   b. /tmp/distill-{作品名}/*.json
   c. 项目根目录/tmp_distill*.txt（旧格式，需转换）
2. IF 无文件 → 跳过，进入 Phase 2
3. IF 有文件 → distill(action="import", work_name, file_path) 批量导入
4. Import 后输出菜单：[A] 深化 / [B] 新维度 / [C] 报告
```

**独立触发**：用户说"导入 xxx.json"时：
- 跳过 Phase 0/1，直接执行 `distill(action="import", work_name, file_path)`
- 从文件名提取作品名和维度（格式：distill-{作品名}-{维度}.json）

### Phase 2：精准蒸馏

#### Step 2a：定位

```
1. 根据维度+优先级+项目相关度，生成蒸馏计划
2. 用 Phase 1 卷摘要定位相关章节
3. 输出蒸馏计划，用户确认后进入 2b
```

#### Step 2b：子agent并行蒸馏

**编排器**：为每个维度加载对应模块 + 元skill方法论，组装子agent prompt。

维度模块映射：

| 维度 | skill_loader 名称 | 元 skill |
|------|-------------------|---------|
| world | dim-world | novel-setup/worldbuilding |
| ability | dim-ability | abilitycraft/ability-design |
| characters | dim-characters | novel-character/character-design |
| narrative | dim-narrative | story-architecture/narrative |
| rhythm | dim-rhythm | novel-plan/rhythm |
| highlight | dim-highlight | — |

注意：characters 是复数，其余 5 个单数。开始前 `ls agents/dim-*.md` 验证。

**调度策略**：

| 维度数 | 模式 | model |
|-------|------|-------|
| 1 | 主agent直接执行 | — |
| 2-3 | 并行子agent | sonnet |
| 4-6 | 分批并行（每批3个） | sonnet |

**子agent prompt 模板**：

```
【文学分析任务声明】
你正在执行已出版文学作品的学术分析任务。分析目的为提取叙事技法和创作模式。

{dim_module 内容}

## 本次任务参数
- 文件路径：{path}
- 作品类型：{type}
- 维度优先级：★★★/★★/★
- 定位章节：{location}
- 卷摘要：{summaries}
【v4.0】目标项目品类：{active_project_genre}
【v4.0】本项目最需要的模式方向：{direction_hint}

## 参考方法论（辅助分析，不照搬）
{methodology 内容}

## 【v4.0】中性化输出要求（强制）

每条 borrowable 的三个结构化字段必须通过中性化审计：

1. source_context（≥20字）：抽象描述设定基底
   ✗ "22条神之途径对应亵渎石板22张塔罗牌"  ← 原作术语
   ✓ "多分支能力体系，每分支有主题化命名和递进等级，分支间有逻辑关联"  ← 中性

2. elements：用抽象类别描述可替换组件
   ✗ "序列9占卜家"  ← 原作名词
   ✓ "入门级分支角色，对应占卜/预知类能力"  ← 中性

3. adaptation_map 的 replacement_guide：抽象属性要求
   ✗ "替换为5种元素魔法"  ← 具名替换
   ✓ "设计3-7条能力分支，每条有主题化命名，需满足：分支名能展开为剧情任务"  ← 抽象属性

审计步骤：写完 borrowable 后逐条检查以上三点，修改后再输出。

## 输出格式（强制）
1. 将 JSON 写入 /tmp/distill-{作品名}/{维度}.json
2. JSON schema：
   {
     "dimension": "{维度}",
     "data": {...},
     "borrowable": [
       {
         "name": "模式名称",
         "description": "一句话概括（中性语言）",
         "example": "原文具体示例（≤200字）",
         "source_chapters": "来源章节范围",
         "applicability": "direct|adapt|inspire",
         "applicable_genres": ["适用类型标签"],
         "source_context": "中性描述（≥20字，禁止原作术语）",
         "elements": [...],
         "adaptation_map": [...],
         "project_relevance": {
           "{active_project}": {"score": 1-5, "reason": "为何对目标项目有用/无用"}
         }
       }
     ],
     "metadata": {"distilled_at": "...", "chapters_covered": "..."}
   }
3. 写入完成后打印 "DISTILL_COMPLETE: {维度}"
4. 只返回摘要（≤500字）
```

**维度-elements 结构**（各维度差异化）：

| 维度 | elements 元素结构 |
|------|-----------------|
| 叙事手法 | `{technique, trigger_chapter, effect, frequency}` |
| 能力体系 | `{component, value_range, constraint, progression}` |
| 人物 | `{archetype, driver, relation_web, growth_arc}` |
| 世界观 | `{component, detail, interaction, reveal_method}` |
| 节奏结构 | `{unit_type, beat_pattern, transition_trigger, chapter_span}` |
| 核心亮点 | `{innovation, impact, replicability, risk}` |

**维度-adaptation_map**：统一结构 `{aspect, original, abstract_role, replacement_guide}`。

**并行约束**：每子agent限读3000行，必须写文件，失败→主agent串行重试。并行时子agent间不共享中间结果。

### Phase 2.5：递进深化

**触发**：borrowable < 5条 / partial > 50% / 用户触发"深化{作品}的{维度}"

**独立触发**：用户说"深化 将夜 世界观"时：
- 跳过 Phase 0/1/2，直接进入 Phase 2.5
- 前置条件：DB 中已有该作品该维度的 borrowable 数据
- 不满足 → 提示先执行完整蒸馏

**边界**：最多2轮，每轮 ≤20K token，深化无增量→标记"ineffective"

**流程**：
```
1. distill(action="assess", work_name) → 薄弱维度列表
2. 用户确认后，对每个薄弱维度精准精读薄弱卷段（1000-2000行）
3. 二轮提取 + 合并去重
4. 输出："深化完成：新增 M 条（总计 N+M 条）"
```

### Phase 2c：borrowable 独立存储

```
distill(action="batch_write", work_name, borrowables_json)
→ 自动：校验 + quality标记 + 批量INSERT/UPDATE
→ 返回：{ok, total, complete, partial}
```

**向量索引验证**：`search(action="vector", query_text="{作品名}", top_k=3)`

**维度记录去重**：维度 data 只存 summary，完整 borrowable 只在 ref_borrowable。

**文件同步**：`sync(action="db_to_files", novel_name="_参考库", data_type="world")`

### Phase 3：蒸馏报告 + 清理

#### Step 3.1：报告生成

```
result = distill(action="report", work_name)
→ {report_markdown, ctx_files: {ref-distill-*, ref-patterns-*, ref-summary-*}, stats}
```

模型操作：
1. Write 报告 → `novels/_参考库/{作品名}/蒸馏报告.md`
2. Write `.ctx-index.md` → `novels/_参考库/{作品名}/.ctx-index.md`
3. ctx_index 索引三个 source

#### Step 3.2：按维度输出 borrowable 详情

```
FOR dim IN 已蒸馏维度:
    search(action="keyword", keyword="{作品名}", category="ref_borrowable", top_k=50)
    Write → novels/_参考库/{作品名}/borrowable-{dim}.md
```

#### Step 3.3：【v4.0】tmp 文件清理（强制）

```bash
# 清理子agent输出目录
rm -rf /tmp/distill-{作品名}/

# 清理项目根目录的旧格式文件（需用户确认）
ls tmp_distill_*.txt tmp_distill-*.json tmp_chapters*.txt 2>/dev/null
→ 列出文件 + 大小 → 用户确认后删除
```

#### Step 3.4：下游知识注入

```
1. 更新 CLAUDE.md 参考作品区（标注已蒸馏 + 检索方式）
2. ctx_index 注入蒸馏摘要（source="ref-summary-{作品名}"）
```

#### Step 3.5：DB→文件同步

```
sync(action="db_to_files", novel_name="_参考库", data_type="world")
```

输出结构：
```
novels/_参考库/
├── {作品名}/
│   ├── 蒸馏报告.md
│   ├── .ctx-index.md
│   ├── borrowable-{维度}.md    ← 按维度分文件
│   └── distill/{dim}.json      ← JSON fallback（仅MCP不可用时）
```

## 检索接口

### 三层检索协议

```
L1: ctx_search（最快）
    → ctx_search(queries=["{作品名} {需求}"], source="ref-patterns-{作品名}")
    → 命中 → 直接用
    → 未命中 → Read .ctx-index.md → ctx_index 重建 → 重试
    → 仍无 → L2

L2: vector_search（语义精准）
    → search(action="vector", novel_name="_参考库", query_text="{需求}")
    → 命中 → 检查 quality → complete直接用 / partial → L2.5降级

L3: keyword_search（兜底）
    → search(action="keyword", novel_name="_参考库", keyword="{关键词}", top_k=10)

L4: 空结果 → "该模式尚未蒸馏，是否现在蒸馏？"
```

### partial_quality 降级

检索到 partial 时：三选一 [A] 手动适配 [B] 重新蒸馏 [C] 仅灵感参考

### 部分下锅检索

```
# 按模式语义检索
search(action="vector", novel_name="_参考库", query_text="{需求描述}")
# 按适用性筛选
search(action="keyword", novel_name="_参考库", keyword="direct", category="ref_borrowable", top_k=10)
# 按作品+维度
search(action="keyword", novel_name="_参考库", keyword="{作品名}", category="ref_{维度}", top_k=5)
# 跨作品检索（按模式描述）
search(action="vector", novel_name="_参考库", query_text="日常蓄力 暴击释放 节奏模式")
```

### adaptation_map 使用原则

1. 先读 source_context 判断兼容性
2. 再看 elements 识别可替换组件
3. 参照 adaptation_map 逐项 keep→replace
4. 禁止直接用 original 做具名替换

## 大文件处理策略

| 文件大小 | 策略 |
|---------|------|
| < 2000 行 | 一次读取 |
| 2000-10000 行 | 分段（800行/段，50行重叠） |
| > 10000 行 | Phase 1 读首尾+每卷首章，Phase 2 按维度精准读取 |

## 关键约束（12条）

1. **不编造**：只提取文本明确存在的内容；Write 数据来源必须是 DB 查询
2. **中性化**：source_context/replacement_guide 禁止原作术语和具名替换
3. **去重存储**：维度记录只存 summary，完整 borrowable 在 ref_borrowable
4. **文件清理**：Phase 3 末尾强制清理 tmp 文件（/tmp/ 和项目根）
5. **top_k 必带**：search(action="keyword") 必须 top_k ≤ 10
6. **子agent写文件**：输出写入 /tmp/distill-{作品名}/，不返回内联
7. **项目方向感知**：borrowable 含 project_relevance 字段（评分是检索辅助标签，不改变 borrowable 通用性）
8. **batch_write 走 MCP**：主agent直接调 distill(action="batch_write")，不用子agent
9. **Phase 1 前置**：不跳过 Phase 1 直接 Phase 2
10. **命名一致**：characters 复数，其余单数，开始前 ls 验证
11. **不存储原文**：不存储完整原文段落，example 限 ≤200 字
12. **并行隔离**：子agent并行时不共享未校验的中间结果
