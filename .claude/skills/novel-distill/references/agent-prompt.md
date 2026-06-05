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

## 输出格式（强制）
1. 使用 Write 工具将 JSON 写入 {work_dir}/{维度}.json
   （ctx_execute 仅用于分析，sandbox 内文件不持久化）
2. JSON schema：
   {
     "dimension": "{维度}",
     "data": {...},
     "borrowable": [
       {
         "name": "模式名称（≤10字中文）",
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

## 维度 elements 差异化结构

| 维度 | elements 字段 |
|------|-------------|
| narrative | `technique, trigger_chapter, effect, frequency` |
| ability | `component, value_range, constraint, progression` |
| characters | `archetype, driver, relation_web, growth_arc` |
| world | `component, detail, interaction, reveal_method` |
| rhythm | `unit_type, beat_pattern, transition_trigger, chapter_span` |
| highlight | `innovation, impact, replicability, risk` |

adaptation_map 统一结构：`{aspect, original, abstract_role, replacement_guide}`
