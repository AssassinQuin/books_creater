# 子 Agent Prompt 模板

编排器加载此模板 + `agents/dim-{dim}.md` 模块内容，组装子 agent prompt。

## 文件写入规则（强制）

**文件输出必须使用 Write 工具。ctx_execute 仅用于分析处理（stdout 自动索引），sandbox 内文件写入不持久化到 host。**

```
正确: Write tool → {work_dir}/{dim}.json
正确: ctx_execute(language="python", code="...分析处理...") → stdout 被索引
错误: ctx_execute(language="python", code="open('...','w').write(...)")  ← sandbox 文件丢失
错误: ctx_execute_file(path=..., code="...写文件...")  ← sandbox 文件丢失
```

## Prompt 结构

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
- 目标项目品类：{active_project_genre}
- 本项目最需要的模式方向：{direction_hint}

## 参考方法论（辅助分析，不照搬）
{methodology 内容}

## 中性化输出要求（强制）

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

## 三重验证质量门（V1V2V3，强制自检）

**借鉴 cangjie-skill 的 Triple Verification**。每条 borrowable 提取后，在写入前必须通过以下三项（不通过的降级到 `{work_dir}/rejected/{dim}.json` 而非丢弃）：

### V1 — 跨域（cross_domain）
该技法在原作**至少 2 个独立场景/章节**出现？
- ✗ 同一案例换说法算两处（作弊）
- ✓ 不同章节 + 不同对象 + 不同结论
- **字段**：`quality.v1_cross_domain.passed` (bool) + `evidence` (数组，每条注明章节)

### V2 — 预测力（predictive_power）
能用 adaptation_map 处理一个**原作没写过的场景**吗？
- ✗ 只能复述原作案例 → 描述而非方法
- ✓ 能推导出非平庸结论
- **字段**：`quality.v2_predictive_power.passed` (bool) + `novel_question` + `derived_answer`

### V3 — 独特性（exclusivity）
不是"任何小说都有的套路"吗？
- ✗ "主角要有动机" / "冲突推动剧情" 这种常识
- ✓ 作者独特的反直觉手法 / 独特术语体系
- **字段**：`quality.v3_exclusivity.passed` (bool) + `why_not_common`

**判定规则**：三项全过 → 进入 borrowable；任一不通过 → 移入 `rejected/{dim}.json`，附 `failed_at` (V1/V2/V3) + `reason`。

### 反例（V3 不通过的常识型 borrowable）
```
✗ name: "主角动机"
   description: "主角需要有清晰的行动动机"
   → V3 不通过：任何小说都有，无需 skill 承载
```
### 正例（V3 通过的独特 borrowable）
```
✓ name: "暗线钩子延迟回收"
   description: "暖色弧里埋一个看似无关的细节，5-8章后冷色弧兑现"
   → V3 通过：反直觉（暖色弧应该纯粹温暖），作者独特手法
```

## Trigger Signals 字段（强制，3-5 条）

**借鉴 cangjie-skill 的 A2 (Future Trigger)**。每条 borrowable 必须标注"用户写作时说什么话应命中本条"：

```json
"trigger_signals": [
  "主角刚经历 X，想让他休息一下",
  "想给读者喘口气",
  "节奏太紧了需要缓和"
]
```

要求：
- 3-5 条用户实际会说的措辞（不要写"用户需要节奏控制时"这种抽象描述）
- 区分相邻 borrowable（暖色弧 vs 冷色弧的 trigger_signals 不能重叠）
- 写完检查：trigger_signals 之间是否互斥？如果两条 borrowable 的 signals 高度重叠，合并或重新拆分

## Related 字段（可选，Zettelkasten 关系图）

**借鉴 cangjie-skill 的 Zettelkasten**。同作品 borrowable 间三类关系：

```json
"related": [
  {"slug": "另一个borrowable的name", "relation": "composes-with"},
  {"slug": "...", "relation": "contrasts-with"},
  {"slug": "...", "relation": "depends-on"}
]
```

- **composes-with**：经常配合使用（如"暖色弧" composes-with "暗线钩子"）
- **contrasts-with**：二选一（如"暖色弧" contrasts-with "冷色弧"）
- **depends-on**：使用前提（如"小胜利" depends-on "暖色弧"）

节制原则：不要硬造关系。无真正关系的 borrowable 留空数组 `[]`。

## 输出格式（强制）
1. 使用 Write 工具将 JSON 写入 {work_dir}/{维度}.json
   （ctx_execute 仅用于分析，sandbox 内文件不持久化）
2. JSON schema（**严格按此结构，不可变体**）：
   {
     "dimension": "{维度}",
     "data": {...},
     "borrowable": [                          ← 必须是 "borrowable"，不是 "borrowables"
       {
         "name": "模式名称（≤10字中文）",
         "description": "一句话概括（中性语言）",
         "example": "原文具体示例（≤200字）",
         "source_chapters": "来源章节范围",
         "applicability": "direct|adapt|inspire",
         "applicable_genres": ["适用类型标签"],
         "source_context": "中性描述（≥20字，禁止原作术语）",
         "elements": [...],
         "adaptation_map": [{"aspect":"...","original":"...","abstract_role":"...","replacement_guide":"..."}],  ← 必须是数组
         "project_relevance": {
           "{active_project}": {"score": 1-5, "reason": "为何对目标项目有用/无用"}
         },
         "trigger_signals": ["用户写作时的语言信号1", "信号2", "信号3"],  ← 3-5条，强制
         "quality": {                                   ← V1V2V3 三重验证，强制
           "v1_cross_domain": {"passed": true/false, "evidence": ["章节A", "章节B"]},
           "v2_predictive_power": {"passed": true/false, "novel_question": "...", "derived_answer": "..."},
           "v3_exclusivity": {"passed": true/false, "why_not_common": "..."}
         },
         "related": [{"slug":"...", "relation":"composes-with|contrasts-with|depends-on"}]  ← 可选，无关系留 []
       }
     ],
     "metadata": {"distilled_at": "...", "chapters_covered": "..."}
   }

   **常见错误警告（检查你的输出避免这些）**：
   ✗ "borrowables": [...]  ← 键名错误，应为 "borrowable"
   ✗ 输出裸数组 [...]     ← 必须包裹在 {dimension, data, borrowable, metadata} 结构中
   ✗ "adaptation_map": {"key": "value"}  ← 必须是对象数组 [{aspect, original, abstract_role, replacement_guide}]
   ✗ 缺失 description/example/source_chapters 等必填字段

3. 写入完成后打印 "DISTILL_COMPLETE: {维度}"
4. 只返回摘要（≤500字）
```

## Rejected 落盘（V1V2V3 失败处理）

子 agent 自检 V1V2V3 时，**任何一项不通过的 borrowable**，不要直接丢弃，必须写入：

```
{work_dir}/rejected/{dim}.json
```

格式：
```json
{
  "dimension": "{dim}",
  "rejected": [
    {
      "name": "候选名称",
      "description": "一句话描述",
      "failed_at": "V1|V2|V3",
      "reason": "为什么不通过（具体）",
      "source_chapters": "...",
      "salvage_hint": "如果未来深化蒸馏时想捞回，需要补充什么"
    }
  ]
}
```

主 agent Phase 2b.7 会扫描 `rejected/` 目录，作为审计轨迹保留，不进入 DB。

## 维度 elements 差异化结构

| 维度 | elements 字段（数组内的对象结构） |
|------|-------------|
| narrative | `technique, trigger_chapter, effect, frequency` |
| ability | `component, value_range, constraint, progression` |
| characters | `archetype, driver, relation_web, growth_arc` |
| world | `component, detail, interaction, reveal_method` |
| rhythm | `unit_type, beat_pattern, transition_trigger, chapter_span` |
| highlight | `innovation, impact, replicability, risk` |

adaptation_map 统一结构：`{aspect, original, abstract_role, replacement_guide}`

## dim 模块与 borrowable schema 的关系（重要）

dim 模块（如 dim-narrative.md）中定义的 Schema（如 pov, hook_types, foreshadowing 等）描述的是输出 JSON 的 **`data` 字段**内容，不是 borrowable 数组的结构。

**输出 JSON 的三层结构**：
```
{
  "dimension": "narrative",
  "data": { ← dim 模块的 Schema 定义的是这一层
    "pov": "...",
    "hook_types": [...],
    ...
  },
  "borrowable": [ ← 这一层严格遵循上方的标准 borrowable schema
    {
      "name": "...",
      "description": "...",
      ...  ← 必须是标准字段，不使用 dim 模块的自定义字段名
      "elements": [...]  ← elements 的内部结构才使用维度差异化的字段
    }
  ],
  "metadata": {...}
}
```

**禁止**：在 borrowable 条目中使用 dim 模块 data 层的字段名（如 technique, trigger_chapter 等）作为顶层字段。这些字段只能出现在 `elements` 数组内部。
