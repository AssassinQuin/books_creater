---
name: novel-qa
description: 小说全链路质量保障，含审阅、诊断和级联更新。触发词：审阅/检查/诊断/改设定/OOC
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__world_delete, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_list, mcp__novel-db__chapter_list, mcp__novel-db__chapter_get_context, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_recall, mcp__novel-db__timeline_query, mcp__novel-db__dimension_query, mcp__novel-db__db_search, mcp__novel-db__health_check, mcp__novel-db__validate_chapter, mcp__novel-db__skill_loader
lifecycle: quality
---

# 小说质量保障

<what-to-do>

## 强制流程

```
B3审阅: world_query+character_list+chapter_list → 3Agent并行分析 → 🔒评分卡 → 汇总报告
C4设定审查: 全量加载设定 → 6维度审查 → 🔒问题清单 → 修复 → 级联同步
C2诊断: health_check → 指标对比 → 🔒破局方案
C3更新: 改数据 → db_search找影响 → 🔒确认改哪些
```

输出到 `novels/{小说名}/审阅报告/`。无文件输出 = 流程未完成。

</what-to-do>

<supporting-info>

## B3: 大纲审阅
触发："审阅大纲"

加载：`skill_loader("novel-qa", "engine", "outline-review")` 大纲审阅清单

Phase 1: 10维度并行Agent审计（因果逻辑审计参考 `skill_loader("novel-qa", "engine", "causality")`，因果链断裂=P0）
Phase 2: P0/P1修复（每个问题3方案+代价评估）
Phase 3: 重评，综合≥85通过，最多3轮

## B3: 正文审阅
触发："审阅正文"/"校对"

Step 1: 加载角色状态（`character_get` + `chapter_get_context`）
Step 2: 3Agent并行扫描：人物维度(OOC/知识矛盾) / 逻辑维度(连贯/经济/伏笔/物品) / 质量维度(战斗/结构/爽点/NPC/写作风格+AI指纹)
Step 3: `validate_chapter(chapter_text)` 校验硬约束
Step 4: 问题分级 P0-致命 / P1-严重 / P2-中等 / P3-轻微
Step 5: 输出报告 → 评级 A/B/C/D

AI指纹检测：`skill_loader("novel-qa", "engine", "anti-ai")` 反AI检测；`validate_chapter()` 自动扫违禁词

## C4: 设定审查
触发："审设定"

1. `world_query` + `character_list` + `relation_list` + `foreshadow_list` 全量加载
2. 6维度审查：内部自洽/人物一致/物品合理/历史可信/关系完整/伏笔可行
3. 🔒问题清单 → 修复方案 → 执行 → 级联同步

## C2: 健康诊断
触发："诊断"/"卡文"
`health_check(novel_id)` → 伏笔积压/配角活跃/升级节奏/日常密度/暗线推进 → 破局策略

## C3: 级联更新
触发："改设定"/"改人物"
1. 更新数据 → `db_search` 找影响 → 🔒确认 → 执行 → 验证

## 设定矛盾检查工具
`skill_loader("novel-qa", "engine", "item")` 物品一致性规则
`skill_loader("novel-qa", "engine", "causality")` 因果逻辑审计清单

</supporting-info>
