---
name: novel-distill
description: >
  参考作品蒸馏引擎 v3.5.0。批露式架构：编排器调度6个维度子agent模块，
  每个模块引用对应元skill方法论指导蒸馏。borrowable独立存储+向量+ctx_index三通道检索。
  v3.5.0: Phase 1.5 已有JSON导入、Phase 2.5 多轮递进深化、MCP三级降级链(write_to_storage)、
  JSON import校验协议(import_distill_json)、ctx文件持久化+自动恢复。
  v3.4.0: source_context/elements/adaptation_map 三字段实现跨项目通用适配映射，
  维度差异化 schema（6维度各有专属 elements/adaptation_map 结构），
  输出校验链（complete/partial_quality 质量标记）。
  文件输出：sync_db_to_files 统一 DB→文件，模板驱动保证一致性。
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
version: "3.5.0"
---

# 参考作品蒸馏引擎

## 触发

用户说"蒸馏XX""分析小说""拆解小说""蒸馏参考"。
扩展触发："导入蒸馏""导入{JSON文件}""深化蒸馏""深化{作品名}的{维度}"。

## 核心概念

**`_参考库`**：novel-db 中的特殊小说名，存储所有参考作品的蒸馏数据。不绑定任何具体小说，全局共享。

**四阶段流程**（v3.5.0 新增 Phase 1.5 和 Phase 2.5）：
- Phase 0 输入确认 + 类型识别
- Phase 1 粗提取 + 作品画像
- **Phase 1.5 已有数据导入**（v3.5.0：检测已有 JSON → import_distill_json 校验 → 导入 DB）
- Phase 2 精准蒸馏（定位 → 子agent并行蒸馏 → borrowable独立存储 → 向量索引）
  - **Phase 2.5 递进深化**（v3.5.0：薄弱维度精准精读 + 二轮提取 → 合并）
- Phase 3 蒸馏报告 + 下游消费指引 + **ctx 文件持久化**

**批露式架构**：
- 6个维度各有独立 agent 模块（`agents/dim-{维度}.md`）
- 编排器（本文件）负责调度，子agent执行具体维度蒸馏

**三通道检索**：
- ctx_index 知识库：下游 skill 用 `ctx_search` 快速检索
- DB 向量检索：`vector_search` / `db_search` 语义精准查找
- borrowable 独立存储：每个可借鉴模式单独可查

**ctx_index 跨 session 持久化**（v3.5.0）：
- 蒸馏完成后 ctx_index 内容写入 `novels/_参考库/{作品名}/.ctx-index.md`
- 下游 skill 检索 ctx 为空时自动重建（见三层检索协议）

**文件存储 fallback**（v3.5.0）：
- MCP 可用时：world_upsert → sync_db_to_files
- MCP 不可用时：降级到 `novels/_参考库/{作品名}/distill/{维度}.json`
- 详见"MCP 降级链"章节

**borrowable 跨项目通用设计原则**：
- adaptation_map 使用抽象属性要求，不做具名替换
- source_context 中性描述原文设定基底
- elements 以抽象类别描述可替换组件

## MCP 降级链（v3.5.0 全局容错协议）

所有涉及 world_upsert 的步骤必须遵循此降级链：

```
write_to_storage(novel_name, category, name, data, tags):
    # 名称安全化：替换非字母数字/非中文字符为 _，截断超 50 字符
    sanitized_name = name 替换 [^a-zA-Z0-9一-鿿_-] 为 _，截断至 50 字符

    # L1: MCP 写入
    尝试 world_upsert(novel_name, category, name, data, tags)
    IF 成功: 记录 "MCP_OK: {category}/{name}"，返回 success
    IF 失败: 记录 "MCP_FAIL: {category}/{name}"，进入 L2

    # L2: 项目文件写入
    fallback_dir = "novels/_参考库/{作品名}/distill"
    file_path = "{fallback_dir}/{category}-{sanitized_name}.json"
    尝试 mkdir -p {fallback_dir} + Write(path=file_path, content=JSON(..., _fallback: true))
    IF 成功: 记录 "FILE_OK: {file_path}"，返回 degraded
    IF 失败: 记录 "FILE_FAIL"，进入 L3

    # L3: /tmp 应急
    tmp_path = "/tmp/distill-{作品名}-{category}-{sanitized_name}.json"
    Write(path=tmp_path, content=JSON(..., _emergency: true))
    输出: "MCP 和项目文件均失败，数据已存 {tmp_path}，请手动恢复。"
    返回 emergency
```

**日志**：每条降级日志含 `{步骤}|{调用}|{结果}|{降级级别}|{路径}`，Phase 3 报告中汇总。

## JSON Import 校验协议（v3.5.0）

导入外部 JSON 时（Phase 1.5 或手动"导入{文件}"）必须经过此协议：

```
import_distill_json(file_path):
    raw = Read(file_path)
    json_data = JSON.parse(raw)

    # 必填三字段校验
    required = ["dimension", "data", "borrowable"]
    missing = [f FOR f IN required IF f NOT IN json_data]
    IF missing 非空: 报错终止 "缺失字段: {missing}"

    # borrowable 子结构校验
    IF json_data.borrowable 不是数组 OR length == 0:
        报错终止 "borrowable 为空"

    # 质量统计
    quality_stats = {"complete": 0, "partial_quality": 0}
    FOR b IN json_data.borrowable:
        has_sc = b.source_context 存在且 len >= 20
        has_el = b.elements 是数组且 len >= 1
        has_am = b.adaptation_map 是数组且 len >= 1
        IF has_sc AND has_el AND has_am: quality_stats.complete += 1
        ELSE: quality_stats.partial_quality += 1

    # 缺失字段补全
    FOR b IN json_data.borrowable:
        IF NOT b.source_context: b.source_context = "（未提取，需手动补充）"
        IF NOT b.elements: b.elements = []
        IF NOT b.adaptation_map: b.adaptation_map = []

    OUTPUT "校验通过: {file_path} — {len} borrowable (complete {stats.complete} / partial {stats.partial})"
    RETURN json_data
```

## 执行流程

### Phase 0：输入确认 + 类型识别

```
1. 获取文件路径（用户直接给，或追问）
2. 验证文件存在：ls {path}
3. IF 文件不存在 → 追问正确路径
4. 文件内容校验：
   - head -20 {path} | grep -c "[\x80-\xff]" → IF = 0 → 可能非文本 → 报错终止
   - wc -c {path} → IF = 0 → 空文件 → 报错终止
5. 文件信息统计：
   - wc -l {path}（行数）
   - grep -c "^第.*章\|^Chapter\|^\*\*\*" {path}（章节数估计）
6. 输出概要："文件 {name}，{lines} 行，约 {chapters} 章"
7. IF 文件 > 2000 行 → 提示将分段读取
8. 类型识别：读取前 200 行，按关键词匹配作品类型（见类型信号表）
9. 向量辅助识别（可选）：
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
# 使用 write_to_storage 降级链写入
write_to_storage(
  novel_name="_参考库",
  category="ref_meta",
  name="{作品名}",
  data={...画像数据（同v3.4.0）...}
)

# 存储卷摘要（每个卷一条）
FOR vol IN 卷列表:
    write_to_storage(novel_name="_参考库", category="ref_volume", name="{作品名}-卷{N}", data={...})
```

#### Step 1.5：输出推荐菜单

```
{作品名} 粗提取完成：
- {N} 卷，{M} 章
- 作品类型：{type_signature}
- 推荐蒸馏重点：{distillation_focus}

可蒸馏维度（按推荐优先级）：
  [1] 叙事手法 ★★★ — ...
  ...
选择要深入蒸馏的维度（可多选，如 1,2,4。留空则蒸馏推荐维度 1-3）：
```

### Phase 1.5：已有数据导入（v3.5.0 新增）

**触发条件**：Phase 1 完成后自动执行，或用户独立触发"导入{JSON文件}"。

```
1. 扫描已有数据源（按优先级）：
   a. novels/_参考库/{作品名}/distill/*.json   ← Phase 2c fallback 产物
   b. /tmp/distill-{作品名}-*.json              ← 子agent写入的临时文件（绝对路径）
   c. 项目根目录/tmp_distill_*.txt                        ← 旧格式粗提取（需转换）

2. IF 无任何文件 → 跳过 Phase 1.5，进入 Phase 2

3. IF 检测到文件：
   a. 逐文件调用 import_distill_json(path) 校验
   b. 校验失败 → 报告错误，跳过该文件
   c. 校验通过 → 进入 import 流程：

4. Import 流程：
   FOR each validated_json:
       FOR pattern IN validated_json.borrowable:
           write_to_storage(
             novel_name="_参考库",
             category="ref_borrowable",
             name="{作品名}-{dim}-{pattern.name}",
             data={...（同Phase 2c的borrowable schema）...},
             tags=["{作品名}", "borrowable", "{dim}"]
           )
       ctx_index(content="导入: {dim} {N}条 borrowable", source="ref-distill-{作品名}")

5. Import 后输出：
   "已有蒸馏数据已导入 DB：
   - 导入维度：{列表}
   - borrowable 总计：{N} 条（complete {M} / partial {K}）
   建议操作：
   [A] 深化已有维度（Phase 2.5）
   [B] 蒸馏新维度（Phase 2）
   [C] 直接生成报告（Phase 3）"
```

**独立触发**：用户说"导入 tmp_distill-女巫-world.json"时：
- 跳过 Phase 0/1，直接执行 import_distill_json + write_to_storage
- 从文件名提取作品名和维度（格式：distill-{作品名}-{维度}.json）

### Phase 2：精准蒸馏（用户选维度后）

#### Step 2a：定位（确定蒸馏范围）

```
1. 根据所选维度和优先级，生成蒸馏计划
2. 对每个维度，用 Phase 1 卷摘要定位相关章节
3. 输出蒸馏计划，用户确认后进入 2b
```

#### Step 2b：子agent并行蒸馏（批露式调度）

**编排器职责**：为每个维度加载对应模块 + 元 skill 方法论，组装子 agent prompt。

```
FOR dim IN 用户选择的维度列表:
    dim_module = skill_loader("novel-distill", "agent", "dim-{dim}")
    IF dim_module 为空 OR 包含 "NOT_FOUND":
        OUTPUT "⚠ 维度模块 {dim} 加载失败，跳过"
        CONTINUE（下一个维度）
    meta_skill = META_SKILL_MAP[dim]
    IF meta_skill != null:
        methodology = skill_loader(meta_skill.skill, meta_skill.level, meta_skill.resource)
    ELSE:
        methodology = ""
    agent_prompt = assemble_prompt(module, methodology, path, genre, priority, location, summaries)
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

**维度模块精确名称映射**：

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
你正在执行已出版文学作品的学术分析任务。以下文本来自公开出版的小说，分析目的为提取叙事技法和创作模式。

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
2. JSON schema（v3.5.0）：
   {
     "dimension": "{维度}",
     "data": {...},
     "borrowable": [
       {
         "name": "模式名称",
         "description": "一句话概括",
         "example": "原文具体示例（≤200字）",
         "source_chapters": "来源章节范围",
         "applicability": "direct|adapt|inspire",
         "applicable_genres": ["适用类型标签"],
         "source_context": "原文设定基底中性描述（≥20字）",
         "elements": [...],
         "adaptation_map": [...]
       }
     ],
     "metadata": {"distilled_at": "...", "chapters_covered": "..."}
   }
3. source_context/elements/adaptation_map 为必填字段
4. 写入完成后打印 "DISTILL_COMPLETE: {维度}"
5. 只返回摘要（≤500字）
```

**维度-elements 结构映射**：

| 维度 | elements 含义 | 数组元素结构 |
|------|-------------|------------|
| 叙事手法 | 叙事技巧组件 | `{"technique": "...", "trigger_chapter": "...", "effect": "...", "frequency": "..."}` |
| 能力体系 | 升级机制组件 | `{"component": "...", "value_range": "...", "constraint": "...", "progression": "..."}` |
| 人物 | 角色原型要素 | `{"archetype": "...", "driver": "...", "relation_web": "...", "growth_arc": "..."}` |
| 世界观 | 设定组件 | `{"component": "...", "detail": "...", "interaction": "...", "reveal_method": "..."}` |
| 节奏结构 | 节奏单元 | `{"unit_type": "...", "beat_pattern": "...", "transition_trigger": "...", "chapter_span": "..."}` |
| 核心亮点 | 创新点 | `{"innovation": "...", "impact": "...", "replicability": "...", "risk": "..."}` |

**维度-adaptation_map 结构映射**：

所有维度统一结构：`{"aspect": "层面", "original": "原文形态", "abstract_role": "抽象功能", "replacement_guide": "替换属性要求"}`

关键约束：replacement_guide 使用抽象属性要求，禁止具名替换。

**并行约束**：
- 每个子agent限读 3000 行
- 子agent必须将 JSON 写入 `/tmp/distill-{作品名}-{维度}.json`
- 任一子agent失败 → 主agent降级串行重试该维度
- 主agent用 `ctx_execute_file` 提取 JSON

### Phase 2.5：递进深化（v3.5.0 新增）

**目标**：对薄弱维度执行精准精读和二轮提取，提升 borrowable 数量和质量。

**触发条件**（可配置，默认值）：
- 该维度 borrowable 数量 < 5（Phase 0 时可调：`--deepen-threshold=N`）
- 该维度 partial_quality 占比 > 50%
- 用户显式触发："深化{作品名}的{维度}"

**边界保护**：
- 最多 2 轮深化
- 每轮 token 预算 ≤ 20K
- 深化后 borrowable 未增加 → 标记 "ineffective"，不再允许该维度深化

**执行流程**：

```
1. 薄弱维度评估（Phase 2b 完成后自动执行）：
   FOR dim IN 已蒸馏维度:
       IF borrowable_count < 5 OR partial_ratio > 0.5:
           标记为 "薄弱维度"

2. IF 无薄弱维度 AND 非用户触发 → 跳过

3. 输出薄弱报告，用户确认后执行深化

4. 深化执行：
   FOR dim IN 薄弱维度:
       a. 定位薄弱章节：基于 Phase 1 卷摘要中该维度的信号密度，
          选取密度最低的 1-2 个卷段（已覆盖章节之外的区域）
       b. 精准精读 1000-2000 行（仅读薄弱卷段，不重读全文）
       c. 二轮提取（传入已有 borrowable 避免重复）
       d. 结果合并去重（pattern_name 相同保留更完整者）

5. 输出深化报告：
   "{维度} 深化完成：新增 {M} 条（总计 {N+M} 条）"
```

**独立触发**：用户说"深化 将夜 世界观"时：
- 跳过 Phase 0/1/2，直接进入 Phase 2.5
- 前置条件：DB 中已有该作品该维度的 borrowable 数据
- 不满足 → 提示先执行完整蒸馏

### Phase 2c：borrowable 独立存储 + 向量索引

**输入校验**：主 agent 读取子 agent 输出 JSON 时，必须经过 import_distill_json 校验。

**输出校验链（写入前强制）**：

```
FOR each borrowable IN 蒸馏结果.borrowable:
    checklist = {
        "source_context": borrowable.source_context 非空（长度 ≥ 20 字）,
        "elements": borrowable.elements 是数组且 length ≥ 1,
        "adaptation_map": borrowable.adaptation_map 是数组且 length ≥ 1
    }
    IF 三项全部通过: quality_flag = "complete"
    ELSE:
        quality_flag = "partial_quality"
        记录缺失项 → 填入占位值
```

**校验后报告**：
```
borrowable 写入完成：{total} 条（complete: {N} / partial_quality: {M}）
{for each partial: "  ⚠ {name} ({dim}): 缺失 {fields}"}
```

**独立存储（使用 write_to_storage 降级链）**：

```bash
FOR dim IN 已蒸馏维度列表:
    FOR pattern IN 蒸馏结果[dim].borrowable:
        write_to_storage(
          novel_name="_参考库",
          category="ref_borrowable",
          name="{作品名}-{dim}-{pattern.name}",
          data={
            "source_work": "{作品名}",
            "source_dimension": "{维度名}",
            "pattern_name": pattern.name,
            "pattern_detail": pattern.description,
            "source_context": pattern.source_context,
            "elements": pattern.elements,
            "adaptation_map": pattern.adaptation_map,
            "applicability": pattern.applicability,
            "applicable_genres": pattern.applicable_genres,
            "example": pattern.example,
            "source_chapters": pattern.source_chapters,
            "quality": quality_flag,
            "missing_fields": missing_fields
          },
          tags=["{作品名}", "borrowable", "{dim}", pattern.applicability, quality_flag]
        )
```

**向量索引（容错验证）**：

```bash
result = vector_search(novel_name="_参考库", query_text="{作品名}", top_k=3)
IF result 成功: 验证命中
ELSE: 降级 db_search(keyword="borrowable", top_k=10) + 标注 "向量验证降级"
```

**borrowable 批量写入策略**：
- 主 agent 直接 FOR 循环调用 write_to_storage
- 按维度分组，每组 ≤15 条串行写入后输出进度

**维度记录去重规则**：
- 维度记录 data 只存 borrowable_summary（count + pattern names）
- 完整 borrowable 只在 ref_borrowable 中
- 禁止在维度记录中嵌入完整 borrowable 数组

**文件输出（DB→文件同步）**：

```bash
sync_db_to_files(novel_name="_参考库", data_type="world")
```

**ctx_index 知识库索引**：

```bash
ctx_index(content=蒸馏报告全文, source="ref-distill-{作品名}")
ctx_index(content=模式清单表格, source="ref-patterns-{作品名}")
```

### Phase 3：蒸馏报告 + 下游消费指引 + ctx 持久化

#### Step 3.1：蒸馏报告

```markdown
# {作品名} 蒸馏报告

## 基础信息
- 类型：{type_signature}
- 卷数：{N} | 核心人物：{M} 人

## 已蒸馏维度
- [x] 世界观 ★★★：{N} 地区, {M} 历史事件
- [x] 能力体系 ★★★：{体系名}，{N} 等级
- [ ] 人物 ★★：未选择

## 可借鉴模式
| # | 模式 | 来源维度 | 适用性 | 适配判断 | 质量 |
|---|------|---------|--------|---------|------|
| 1 | {模式1} | 叙事手法 | direct | {elements核心组件} | complete |
| 2 | {模式2} | 节奏结构 | adapt | {elements核心组件} | partial_quality ⚠ |

## 降级日志（v3.5.0）
| 步骤 | 调用 | 结果 | 降级级别 | 路径 |
|------|------|------|---------|------|
| {if any} | world_upsert ref_meta | 失败 | L2 文件 | novels/_参考库/.../ref_meta.json |

## 深化记录（v3.5.0）
| 维度 | 轮次 | borrowable 变化 | 状态 |
|------|------|----------------|------|
| {dim} | 1/2 | 8 → 12 (+4) | effective |

## 检索验证
- vector_search("{关键词}") → 命中 {N} 条
- ctx_search("ref-patterns-{作品名}") → 已索引
```

#### Step 3.2：下游消费指引

#### Step 3.3：下游知识注入

**1. 更新 CLAUDE.md 参考作品区**：
```
参考作品：无职转生（✓已蒸馏）、权游（待蒸馏）、将夜（✓已蒸馏）

### 参考作品检索方式
- 精准：db_search("_参考库", keyword="{作品名}", category="ref_borrowable", top_k=5)
- 语义：vector_search("_参考库", query_text="XX")
- 快速：ctx_search(queries=["{作品名}"], source="ref-patterns-{作品名}")
- 文件：novels/_参考库/{作品名}/蒸馏报告.md → borrowable-{维度}.md
```

**2. 蒸馏摘要注入 ctx_index**：
```
ctx_index(content="# {作品名} 蒸馏摘要\n\n## 检索入口\n...\n## TOP 5 模式\n...", source="ref-summary-{作品名}")
```

#### Step 3.4：ctx 文件持久化（v3.5.0 强制）

蒸馏完成后，将 ctx_index 内容写入磁盘快照，解决跨 session 丢失：

```
snapshot = "# {作品名} ctx 索引快照\n> 自动生成，勿手动编辑\n\n"
FOR source IN ["ref-distill-{作品名}", "ref-patterns-{作品名}", "ref-summary-{作品名}"]:
    snapshot += "## source: {source}\n{对应ctx内容}\n\n"

Write(path="novels/_参考库/{作品名}/.ctx-index.md", content=snapshot)
```

#### Step 3.5：DB→文件同步 + 按作品输出（强制）

```bash
# 1. 聚合备份
sync_db_to_files(novel_name="_参考库", data_type="world")

# 2. 按作品输出
FOR dim IN 已蒸馏维度:
    # 维度数据
    db_search(novel_name="_参考库", keyword="{作品名}", category="ref_{dim}", top_k=1)
    Write(path="novels/_参考库/{作品名}/{dim}.md", content=维度数据)

    # borrowable 详情
    db_search(novel_name="_参考库", keyword="{作品名}", category="ref_borrowable", top_k=50)
    Write(path="novels/_参考库/{作品名}/borrowable-{dim}.md", content=筛选后详情)

# 3. 蒸馏总报告
Write(path="novels/_参考库/{作品名}/蒸馏报告.md", content=Step 3.1 报告)
```

输出结构：
```
novels/_参考库/
├── 设定/世界观/ref_*.md      ← sync 聚合备份
├── {作品名}/
│   ├── 蒸馏报告.md
│   ├── .ctx-index.md          ← ctx 持久化（v3.5.0）
│   ├── distill/               ← JSON fallback（v3.5.0）
│   │   └── {dim}.json
│   ├── world.md
│   ├── borrowable-叙事手法.md
│   └── ...
```

## 检索接口（其他 skill 使用）

### 三层检索协议（含 ctx 恢复）

```
L1: ctx_search（最快）
    → ctx_search(queries=["{作品名} {需求}"], source="ref-patterns-{作品名}")
    → 命中 → 直接使用
    → 未命中 → 检查 .ctx-index.md 存在 → Read → ctx_index 重建 → 重试
    → 仍无 → 降级 L2

L1.5: adaptation_map 检索
    → ctx_search(queries=["adaptation_map {aspect}"], source="ref-patterns-{作品名}")

L2: vector_search（语义精准）
    → vector_search(novel_name="_参考库", query_text="{需求}")
    → 命中 ref_borrowable → 检查 quality → complete 直接用 / partial_quality 降级

L3: db_search（兜底，top_k=10）
    → db_search(novel_name="_参考库", keyword="{关键词}", top_k=10)

L4: 空结果 → 提示"该作品/模式尚未蒸馏，是否现在蒸馏？"
```

### adaptation_map 缺失降级指引

```
检索到 partial_quality 时：
1. 提示缺失字段 + 三选一：[A] 手动适配 [B] 重新蒸馏 [C] 仅灵感参考
2. 不阻塞当前操作
3. 选 [A] 则提供该维度的 adaptation_map 空模板
```

### 部分下锅接口

```
# 按模式检索
vector_search(novel_name="_参考库", query_text="{需求}")
# 按适用性
db_search(novel_name="_参考库", keyword="direct", category="ref_borrowable", top_k=10)
# 按作品+维度
db_search(novel_name="_参考库", keyword="{作品名}", category="ref_{维度}", top_k=5)
# 跨作品
vector_search(novel_name="_参考库", query_text="日常蓄力 暴击释放 节奏模式")
# 按 adaptation_map aspect
vector_search(novel_name="_参考库", query_text="组织形态 定期同步多线情报的枢纽组织")
```

### adaptation_map 使用原则

1. 先读 source_context 判断设定基底兼容性
2. 再看 elements 识别可替换组件
3. 参照 adaptation_map 逐项 keep→replace
4. 禁止直接用 original 做具名替换
5. 蒸馏数据跨项目通用

## 大文件处理策略

| 文件大小 | 策略 |
|---------|------|
| < 2000 行 | 一次读取 |
| 2000-10000 行 | 分段读取（每段 800 行，重叠 50 行） |
| > 10000 行 | Phase 1 仅读首尾+每卷首章，Phase 2 按维度精准读取 |

## 质量保障

1. **交叉验证**：人物关系与世界观设定交叉检查
2. **引用溯源**：每条数据标注来源章节范围
3. **避免过度解读**：只提取文本明确存在的内容
4. **借鉴定级**：borrowable 三级标签 direct/adapt/inspire
5. **子agent输出校验**：import_distill_json 校验后写入（v3.5.0）
6. **向量索引验证**：失败时降级用 db_search
7. **ctx_index 索引**：蒸馏报告+模式清单+检索摘要自动索引
8. **文件持久化**：sync_db_to_files 聚合 + db_search+Write 按作品输出
9. **下游知识注入**：更新 CLAUDE.md + ctx_index 注入
10. **文学分析语境**：子agent prompt 含文学分析声明
11. **命名一致性**：Step 2b 前用 ls 验证，characters 复数
12. **db_search 结果控制**：必须带 top_k（≤10）
13. **borrowable 去重存储**：维度记录只存 summary
14. **跨项目通用适配**（v3.4.0）：source_context/elements/adaptation_map 必填
15. **输出校验链**（v3.4.0）：写入前逐条验证三字段
16. **下游降级兼容**（v3.4.0）：partial_quality 三选一降级
17. **MCP 降级链**（v3.5.0）：所有 world_upsert 使用 write_to_storage 三级降级
18. **JSON import 校验**（v3.5.0）：import_distill_json 强制 schema + 质量统计
19. **多轮递进深化**（v3.5.0）：Phase 2.5 最多2轮 + 20K token预算 + ineffective 检测
20. **ctx 文件持久化**（v3.5.0）：.ctx-index.md 快照 + 下游自动重建

## 禁止

- 不编造原文没有的内容
- 不做主观价值判断
- 不存储完整原文段落
- 不跳过 Phase 1 直接进入 Phase 2
- 不在子agent并行时共享未校验的中间结果
- 不将 borrowable 只嵌在维度 JSON 内不独立存储
- 不在维度记录中嵌入完整 borrowable 数组
- 不使用子 agent 执行纯机械 world_upsert 循环
- 不在 db_search 中省略 top_k
- 不编造文件内容——Write 数据来源必须是 DB 查询
- 不在 adaptation_map 的 replacement_guide 中使用具名替换
- 不将蒸馏数据针对特定目标作品预适配
- 不在 import_distill_json 校验失败时跳过（v3.5.0）
- 不跳过 .ctx-index.md 快照写入（v3.5.0）
- 不在深化无效后继续深化同一维度（v3.5.0）
- 不在 Phase 2.5 深化时跳过去重直接合并（v3.5.0）
