---
name: novel-writer
description: 网文创作总路由器，分发到子技能并处理上架和状态查询。触发词：写小说/帮我写/上架/进度
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__novel_get, mcp__novel-db__novel_list, mcp__novel-db__novel_update, mcp__novel-db__novel_delete, mcp__novel-db__world_query, mcp__novel-db__chapter_list, mcp__novel-db__volume_list, mcp__novel-db__foreshadow_list, mcp__novel-db__character_list, mcp__novel-db__db_search, mcp__novel-db__writing_start, mcp__novel-db__validate_chapter, mcp__novel-db__writing_finish, mcp__novel-db__engine_detail, mcp__novel-db__rule_detail, mcp__novel-db__health_check
lifecycle: core
---

# 网文创作总入口

> **术语定义**: 读 `NOVEL-CONTEXT.md`（项目根目录）

<what-to-do>

## 意图路由

```
关键词                                          → 调用 Skill
────────────────────────────────────────────────────────────
"头脑风暴"/"灵感"/"建世界观"/"设定"/"加物品"     → novel-setup
"设计人物"/"加人物"/"人物卡"/"改人物"             → novel-character
"规划卷"/"大纲"/"卷大纲"                         → novel-planner
"写第N章"/"继续写"/"写一章"                      → novel-chapter-writer
"审阅"/"检查"/"诊断"/"卡文"/"改设定"/"OOC"       → novel-qa
"写战斗"/"战斗场景"/"战斗设计"                    → novel-battle
"修复"/"去重"/"批量改"/"修文"/"润色"             → novel-reviser
"上架"/"发布"                                    → 本skill处理（platform-rules.md）
"进度"/"状态"/"加素材"/"拆书"                    → 本skill处理
"搜一下"/"查一下{关键词}"                         → db_search()
无匹配 → novel_get + chapter_list 查进度，建议下一步
```

### 优先级
C3级联更新 > B2写作中断 > 模糊匹配

</what-to-do>

<supporting-info>

## 平台上架
`novel_get` + `world_query` 获取项目数据 → 合规检查 → 输出到 `novels/{小说名}/上架版/`
参考 `references/platform-rules.md`

## 状态查询
`novel_get` + `volume_list` + `chapter_list` + `foreshadow_list` + `character_list` + `health_check(novel_id)`

## 素材操作
灵感/素材 → `memory_store(tags="shared,material")`
新AI味 → `memory_store(tags="shared,anti-ai-pattern")`

## 拆书分析
读 `references/book-analysis-guide.md` → 段落拆解+技巧提取 → 风格建档(`memory_store`) → 写入 `novels/拆书笔记/`

## 数据搜索
`db_search(novel_id, keyword)` → 跨所有表搜索

</supporting-info>
