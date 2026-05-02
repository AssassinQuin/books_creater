---
name: novel-setup
description: 小说项目基建 — 头脑风暴启动项目、世界观建模。触发词：头脑风暴/灵感/建世界观/世界观/设定/我有个想法。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_create, mcp__novel-db__novel_list, mcp__novel-db__novel_get, mcp__novel-db__novel_update, mcp__novel-db__world_upsert, mcp__novel-db__world_query, mcp__novel-db__world_delete
---

# 小说项目基建

> 共享约定（铁律/数据分层/Memory模型/Git规范）：读 `.claude/skills/novel-writer/references/shared-conventions.md`

## 强制流程

```
A1启动: 创建项目 → 头脑风暴(逐问) → 🔒输出决策卡 → 用户选定 → commit
A2世界观: 读模板 → 逐维度建立(每维🔒确认) → 交叉验证 → commit → 建议下一步
```

每个阶段有 🔒 检查点。用户说"改一下"→ 回退修改；说无关问题 → 简短回答后回到当前步骤。

---

## A1: 项目启动

触发: "头脑风暴"/"灵感"/"我有个想法"

1. 确认小说名，`novel_create` 创建项目
2. 读 `.claude/skills/novel-writer/references/brainstorm-guide.md`，**一次只问一个问题**：
   - 画面感 → 主角特质 → 读者情绪(爽/虐/燃/感动/紧张) → 对立面 → 独特规则
   - 用户提到"群像"→ 追问每个核心角色的独立线和交汇点
3. 每个回答 → `memory_store(tags="project:{名},idea")`
4. 🔒**输出决策卡**（结构化模板）：

   ```
   项目: {小说名}
   核心冲突: {1-3个候选}
   主线方向: {2-3个候选}
   读者情绪: {主情绪}
   亮点场景: {列表}
   建议品类: {参考 genre-profiles.md}
   建议节奏: {快/中/慢}
   ```

5. 用户选定 → `novel_update(genre, status)` + `memory_store(tags="project:{名},decision")`
6. `git commit -m "A1: 项目启动 - {小说名}"`

完成后建议：`/novel-setup` 建世界观，或 `/novel-character` 设计人物。

---

## A2: 世界观建模

触发: "建世界观"/"世界观"/"设定" | 前置: A1完成

**前置校验**: `novel_get(novel_id)` 确认项目存在且 status 允许建世界观。

**已有世界观检测**: `world_query(novel_id)` 查已有维度。
- 已有维度 → "你已建了{N}个维度（{列表}），要修改哪个？还是继续新建？"
- 修改模式：`world_delete` 删除旧版 → `world_upsert` 写新版 → 🔒确认
- 空白 → 进入逐维度建立

### 模式选择

| 用户意图 | 模式 | 流程 |
|---------|------|------|
| "帮我设计一个完整世界" | **引导模式** | 逐维度问答（默认） |
| "给我一个标准{品类}世界" | **快速模式** | 基于模板+genre-profiles自动生成6维初稿 → 用户审阅修改 |
| "改一下{某维度}" | **修改模式** | world_query查当前 → world_delete旧 → world_upsert新 |

### 引导模式（默认）

1. 读 `.claude/skills/novel-writer/references/worldbuilding-template.md`
2. 逐维度建立，**一次一个维度**：种族→势力→地理→能力→经济→日常
   - 用户说"跳过这个" → 记录，后续标注缺失，不强制补全
3. 每维度完成 → `world_upsert(novel_id, category, name, data)` + 🔒**向用户确认该维度**再进入下一个

### 快速模式

1. 根据 genre 读 genre-profiles.md 中对应品类模板
2. 一次生成6维度初稿，写入 `world_upsert`（每个维度一条）
3. 🔒**整体展示** → 用户逐维度确认/修改
4. 修改 → `world_upsert` 覆盖

### 交叉验证（两种模式都必须执行）

逐项检查，不合理解释原因并建议修改：

| 检查项 | 验证方法 | 异常标准 |
|--------|---------|---------|
| 种族×地理 | 各种族分布与地理是否匹配 | 有种族无分布区域 |
| 势力×地理 | 势力地盘与区域对应 | 势力无明确地盘 |
| 势力×经济 | 势力财力支撑其行为 | 穷势力养大军/富势力不做贸易 |
| 能力×种族 | 先天能力差异自洽 | 弱种族突然有超强能力无解释 |
| 经济×日常 | 物价与生活水平匹配 | 一顿饭=普通人一年收入 |
| 时间×距离 | 出行时间与距离合理 | 步行1小时跨大陆 |

验证通过 → `git commit -m "A2: 世界观完成 - {小说名}"` → 建议下一步：`/novel-character`

---

## 断点续传

触发时先检查：
```
memory_search(query="flow-state", tags=["project:{名},flow-state"])
```
有记录 → "上次我们在{步骤}暂停了，从那里继续？"
