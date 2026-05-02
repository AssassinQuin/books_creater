---
name: novel-setup
description: 小说项目基建 — 头脑风暴启动项目、世界观建模。触发词：头脑风暴/灵感/建世界观/世界观/设定/我有个想法。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_create, mcp__novel-db__novel_list, mcp__novel-db__novel_get, mcp__novel-db__novel_update, mcp__novel-db__world_upsert, mcp__novel-db__world_query, mcp__novel-db__world_delete
---

# 小说项目基建

> 共享约定（铁律/数据分层/Memory模型/Git规范）：读 `.claude/skills/novel-writer/references/shared-conventions.md`

---

## A1: 项目启动

触发: "头脑风暴"/"灵感"/"我有个想法"

1. 确认小说名，`novel_create` 创建项目
2. 读 `.claude/skills/novel-writer/references/brainstorm-guide.md`，**一次只问一个问题**：
   - 画面感 → 主角特质 → 读者情绪(爽/虐/燃/感动/紧张) → 对立面 → 独特规则
   - 用户提到"群像"→ 追问每个核心角色的独立线和交汇点
3. 每个回答 → `memory_store(tags="project:{名},idea")`
4. 结束输出：核心冲突(1-3选1) + 主线方向(2-3选1) + 建议品类(参考 `.claude/skills/novel-writer/references/genre-profiles.md`)
5. 用户选定 → `novel_update(genre, status)` + `memory_store(tags="decision")`
6. `git commit -m "A1: 项目启动 - {小说名}"`

**完成后建议**：调用 `/novel-setup` 建世界观，或 `/novel-character` 设计人物。

---

## A2: 世界观建模

触发: "建世界观"/"世界观"/"设定" | 前置: A1完成

1. 读 `.claude/skills/novel-writer/references/worldbuilding-template.md`
2. 引导逐维度建立，**一次一个维度**：种族→势力→地理→能力→经济→日常
3. 每维度完成 → `world_upsert(novel_id, category, name, data)` + 写文件
4. 全部完成 → 维度交叉验证（时间×空间、经济×势力、能力×种族）
5. `git commit -m "A2: 世界观完成 - {小说名}"`

**完成后建议**：调用 `/novel-character` 设计人物。
