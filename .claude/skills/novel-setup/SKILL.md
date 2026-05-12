---
name: novel-setup
description: 小说项目基建 — 头脑风暴启动项目、世界观建模、物品档案、历史层。触发词：头脑风暴/灵感/建世界观/世界观/设定/加物品/建历史/我有个想法。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_create, mcp__novel-db__novel_list, mcp__novel-db__novel_get, mcp__novel-db__novel_update, mcp__novel-db__world_upsert, mcp__novel-db__world_query, mcp__novel-db__world_delete
---

# 小说项目基建

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`
> 物品引擎：读 `.claude/skills/novel-writer/references/engine-item.md`

## 强制流程

```
A1启动: 创建项目 → 头脑风暴(逐问) → 🔒输出决策卡 → 用户选定 → commit
A2世界观: 读模板 → 逐维度建立(含历史层+物品) → 交叉验证 → commit → 建议下一步
```

每个阶段有 🔒 检查点。用户说"改一下"→ 回退修改；说无关问题 → 简短回答后回到当前步骤。

---

## A1: 项目启动

触发: "头脑风暴"/"灵感"/"我有个想法"

1. 确认小说名，`novel_create` 创建项目
2. 读 `references/brainstorm-guide.md`，**一次只问一个问题**：
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

1. 读 `references/worldbuilding-template.md`
2. 逐维度建立，**一次一个维度**：种族→势力→地理→能力→经济→日常→**历史层**→**物品体系**
   - 用户说"跳过这个" → 记录，后续标注缺失，不强制补全
3. 每维度完成 → `world_upsert(novel_id, category, name, data)` + 🔒**向用户确认该维度**再进入下一个

### 快速模式

1. 根据 genre 读 genre-profiles.md 中对应品类模板
2. 一次生成8维度初稿（含历史+物品），写入 `world_upsert`（每个维度一条）
3. 🔒**整体展示** → 用户逐维度确认/修改
4. 修改 → `world_upsert` 覆盖

### 历史层（world_query category="history"）

世界观的纵深支撑——正文不写，但必须经得起推敲。

```
历史维度模板:
  时间线: {N年前发生了什么→导致了现在的格局}
  遗留物: {哪些旧时代的物品/建筑/制度保留至今}
  失传物: {哪些技术/知识消失了，为什么}
  自洽性: {遗留物为什么还能用/建筑为什么不塌/制度为什么不改}
  信息断层: {现在的人知道多少历史/哪些是传说/哪些是误读}
```

设计规则：
- 遗留物必须解释"为什么还在"（灵能设备自我维护？材料特殊？有人秘密维护？）
- 失传物必须解释"为什么丢了"（战乱？灵能污染？禁忌？）
- 现在的角色只能知道他们**能知道**的历史（拾荒者不知道400年前的技术原理）

### 物品体系（world_query category="ability"/"economy"）

关键物品必须建立完整档案，参照 `engine-item.md` 的生命周期模板：

```
首次出现物品必须建立:
  来源/产地/稀缺度 → 外观(形/色/质感/光泽/大小) → 感官(触/嗅/味/声)
  → 功能(用途/方式/条件/持续时间) → 等级差异 → 变化与衰减
  → 使用禁忌与代价 → 经济(价格/获取成本/存储条件)
```

存入 `world_upsert(category="ability"/"economy", name="{物品名}", data={完整档案})`

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
| **历史×遗留** | 遗留物与历史事件对应 | 400年建筑完好无解释 |
| **物品×经济** | 物品价格与稀缺度匹配 | 随处可见的物品天价 |

验证通过 → `git commit -m "A2: 世界观完成 - {小说名}"` → 建议下一步：`/novel-character`

---

## A2补充: 物品档案管理

触发: "加物品"/"建物品"/涉及新物品首次出现时

1. 确认物品是否已存在：`world_query(name="{物品名}")`
2. 不存在 → 按 `engine-item.md` 模板建立完整档案
3. `world_upsert(category="ability"/"economy", name="{物品名}", data={档案})`
4. 🔒确认档案完整性
5. 如果是已有物品有新发现 → 更新档案对应字段，不重写

---

## 断点续传

触发时先检查：
```
memory_search(query="flow-state", tags=["project:{名},flow-state"])
```
有记录 → "上次我们在{步骤}暂停了，从那里继续？"
