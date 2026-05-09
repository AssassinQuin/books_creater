---
name: novel-doctor
description: 小说质量保障 — 审阅三线并行检查、健康诊断、破局方案、级联更新。触发词：审阅/检查/诊断/卡文/疲劳/写不动/改设定/改人物/调整/review。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__world_delete, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_list, mcp__novel-db__chapter_list, mcp__novel-db__chapter_get_context, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_recall, mcp__novel-db__timeline_query, mcp__novel-db__dimension_query, mcp__novel-db__db_search, mcp__novel-db__health_check
---

# 小说质量保障

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`（含流程纪律）

## 强制流程

```
B3审阅: 数据获取 → 3Agent并行分析 → 🔒评分卡 → 汇总报告
C2诊断: health_check → 对比健康指标 → 🔒破局方案
C3更新: 改数据 → db_search找影响 → 🔒确认改哪些
```

审阅/诊断结束时，**必须输出结构化结果文件**到 `novels/{小说名}/审阅报告/`。没有输出文件视为流程未完成。

---

## B3: 审阅

触发: "审阅"/"检查"/"review"

### 大纲级审阅（卷规划后/全书大纲完成后）

读 `.claude/skills/novel-writer/references/outline-review-checklist.md`，执行三阶段流程：

1. **Phase 1 达尔文评估**: 10维度并行Agent审计（按卷类型选取5-10维度），每维度量化评分(0-100)
2. **Phase 2 女娲修复**: P0/P1问题自动进入修复流程，每问题3方案+代价评估+修复蓝图
3. **Phase 3 验证迭代**: 修复后重评，对比前后分，达标则通过（综合≥85），不达标则迭代（最多3轮）

输出 → `novels/{小说名}/审阅报告/大纲审查-{日期}/`

### 章节级审阅（正文写作后）

读 `.claude/skills/novel-writer/references/review-checklist.md`
用 `db_search`/`foreshadow_list`/`dimension_query` 获取数据

3个Agent并行：
- **A-逻辑**: `timeline_query`+`dimension_query` 检查时间/空间/能力一致性，`foreshadow_list(status="planted")` 查超30章未回收伏笔标黄
- **B-人设**: `character_list` 对照人设检查OOC，AI味检测（对照 `.claude/skills/novel-writer/references/anti-ai-patterns.md` + Memory黑名单）
- **C-合规+竞争力**: 平台合规（参考 `.claude/skills/novel-writer/references/platform-rules.md`），爽点密度，钩子有效性，侧面描写

**章节评分卡**（每章量化打分）：

| 维度 | 1-3分 | 4-6分 | 7-10分 |
|------|-------|-------|--------|
| 文笔 | 大量AI味词/空洞描写 | 基本流畅/偶有AI味 | 生动有画面/句式多变 |
| 节奏 | 拖沓或赶进度 | 有节奏但平淡 | 张弛有度/有钩子 |
| 人设一致 | 明显OOC | 轻微偏离 | 行为符合人设 |
| 伏笔推进 | 无进展无提及 | 有提及但机械 | 自然融入/暗线推进 |
| 去AI味 | ≥5个黑名单词 | 1-2个黑名单词 | 0个/对话有废话 |

汇总 → `novels/{小说名}/审阅报告/` → 问题分级 + 评分卡
```
章节{N}总分: {Σ各维度}/50
趋势: {与最近5章均分对比 ↑↓→}
短板: {最低分维度}
```

---

## C2: 健康诊断

触发: "诊断"/"卡文"/"疲劳"/"写不动"

**一键诊断**：
```
health_check(novel_id)
→ 进度 + 伏笔积压(回收率/最老章距) + 配角活跃(出场间隔>10章标黄) + 升级曲线 + 卷完成度 + 警告列表
```

**健康指标**：

| 指标 | 健康 | 异常 |
|------|------|------|
| 伏笔积压 | 未回收<40% | >50%且最老>30章 |
| 配角活跃 | 核心配角5章内提及 | >10章无提及 |
| 升级节奏 | 符合genre建议 | 40章无升级且无替代爽点 |
| 日常密度 | 5-8章有日常 | 连续10章纯战斗 |
| 暗线推进 | 15-20章有新进展 | >30章无新线索 |

**破局方案**：
- **升级衰减**：切爽点类型（升级碾压→势力博弈/智斗/信息差/以弱胜强），引新体系（炼丹/阵法/灵兽）
- **配角遗忘**：信息差回归（他在暗处做了什么？），独立线与主线交汇，侧面描写维持存在
- **伏笔膨胀**：批量回收（选3-5条重要伏笔2-3章内回收），长线伏笔延后新卷，果断放弃不重要的

---

## C3: 级联更新

触发: "改设定"/"改人物"/"调整"

1. 改对应数据（`world_upsert`/`character_update`）
2. `db_search(novel_id, keyword)` 找受影响内容
3. 列出受影响章节 → 询问用户哪些需要改

---

## 断点续传

触发时先检查 `memory_search(query="flow-state", tags=["project:{名},flow-state"])`
有记录 → "上次我们在{步骤}暂停了，从那里继续？"
