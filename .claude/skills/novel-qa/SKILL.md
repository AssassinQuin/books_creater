---
name: novel-qa
description: 小说全链路质量保障，含审阅、诊断和级联更新。触发词：审阅/检查/诊断/改设定/OOC
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__world_delete, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_list, mcp__novel-db__chapter_list, mcp__novel-db__chapter_get_context, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_recall, mcp__novel-db__timeline_query, mcp__novel-db__dimension_query, mcp__novel-db__db_search, mcp__novel-db__health_check
lifecycle: quality
---

# 小说质量保障

> 共享约定：读 `references/shared-conventions.md`
> 快照引擎：读 `references/engine-snapshot.md`（一致性校验规则）
> 物品引擎：读 `references/engine-item.md`（物品一致性校验）
> AI指纹检测：读 `references/ai-fingerprint-detection.md`
> **术语定义**: 读项目根目录 `NOVEL-CONTEXT.md`

<what-to-do>
## 强制流程

```
B3审阅: 数据获取 → 3Agent并行分析 → 🔒评分卡 → 汇总报告
C4设定审查: 全量加载设定 → 6维度审查 → 🔒问题清单 → 优化方案 → 执行修复 → 级联同步
C2诊断: health_check → 健康指标对比 → 🔒破局方案
C3更新: 改数据 → db_search找影响 → 🔒确认改哪些
```

输出结构化结果到 `novels/{小说名}/审阅报告/`。无文件输出 = 流程未完成。
</what-to-do>

<supporting-info>

## B3: 审阅

### 大纲审阅（Phase 1-3 达尔文评估体系）

触发: "审阅大纲"/"检查大纲"

**Phase 1 达尔文评估**：
- 10维度并行Agent审计（根据卷类型选5-10维度），每维度0-100分
- 参照 `references/outline-review-checklist.md`

**Phase 2 女娲修复**：
- P0/P1问题进入自动修复流程，每个问题生成3个修复方案 + 代价评估

**Phase 3 验证迭代**：
- 修复后重新评估，综合≥85通过，最多3轮迭代

### 正文审阅（15维度扫描）

触发: "审阅正文"/"检查正文"/"校对"/"proofread"

**Step 1: 加载角色状态**（优先级: 蒸馏文件 > 角色深化 > 锁定设定 > novel-db）

**Step 2: 15维度逐章扫描 — 3Agent并行**

**Agent A — 人物维度**：人设OOC检查 / 知识矛盾 / 微动作检查

**Agent B — 逻辑维度**：逻辑连贯 / 经济逻辑 / 伏笔一致性 / 受伤一致性 / 物品状态 / 新元素合理性

**Agent C — 质量维度**：战斗质量 / 结构变异 / 爽点密度 / NPC深度 / 叙事视角+术语 / 写作风格 / **AI指纹检测(2.15b)**

**AI指纹检测（V2.0新增）**: 按 `ai-fingerprint-detection.md` 执行4项核心指纹扫描：FP-1句号切割法 / FP-2解释式展示 / FP-3结构对称 / FP-4否定转折模式化。综合评分<6.0 = P2问题。

**Step 3: 问题分级** P0-致命 / P1-严重 / P2-中等 / P3-轻微 / P4-建议

**Step 4: 输出报告** → 评级: A(无P0/P1) / B(有P1无P0) / C(有P0) / D(严重OOC)

---

## C4: 设定审查+优化

触发: "审设定"/"优化设定"/"审查世界观"/"设定矛盾"

1. 全量加载设定（world_query + character_list + relation_list + foreshadow_list + 设定文件）
2. 六维度审查（内部自洽 / 人物一致性 / 物品合理性 / 历史经得起推敲 / 关系网完整性 / 伏笔可行性）
3. 🔒问题清单（P0设定矛盾 / P1不合理 / P2缺失 / P3可优化）
4. 优化方案 → 执行修复 → 级联同步
5. 输出报告到 `novels/{小说名}/审阅报告/设定审查-{日期}.md`

---

## C2: 健康诊断

触发: "诊断"/"卡文"/"疲劳"/"写不动"

`health_check(novel_id)` → 指标对比（伏笔积压/配角活跃/升级节奏/日常密度/暗线推进）→ 破局策略

---

## C3: 级联更新

触发: "改设定"/"改人物"/"调整"

1. 更新对应数据 → 2. db_search 找受影响内容 → 3. 🔒确认改哪些 → 4. 执行修改 → 5. 验证

---

## 断点续传

检查 `memory_search(query="flow-state", tags=["project:{名},flow-state"])`
有记录 → "上次在{步骤}暂停了，从那里继续？"

</supporting-info>
