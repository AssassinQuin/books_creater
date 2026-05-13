---
name: novel-chapter-writer
description: 逐章写作引擎，驱动从大纲到成文的完整流程。触发词：写第N章/继续写/写一章
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_get, mcp__novel-db__chapter_list, mcp__novel-db__chapter_update, mcp__novel-db__writing_start, mcp__novel-db__writing_finish, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_recall, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_list, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__timeline_query, mcp__novel-db__volume_get
lifecycle: core
---

# 逐章写作引擎

> 共享约定：读 `references/shared-conventions.md`
> **术语定义**: 读项目根目录 `NOVEL-CONTEXT.md`

<what-to-do>
## 强制流程

```
Step 0 断点检测 → Step 1 引擎加载上下文 → Step 2 写正文 → Step 3 🔒状态同步 → Step 4 存盘
```

**Step 3 是不可跳过的强制步骤**。每章写完后必须执行质量检查，未完成则拒绝存盘。
</what-to-do>

<supporting-info>

## 引擎参考文档

| 文档 | 用途 | 何时加载 |
|------|------|---------|
| `references/engine-loading.md` | 三级上下文加载协议 | Step 1 |
| `references/engine-snapshot.md` | 场景/事件/人物快照 | Step 1 + Step 3 |
| `references/engine-environment.md` | 环境5要素+感官描写 | Step 2.2 |
| `references/engine-dialogue.md` | 差异化对话+弦外之音 | Step 2.3 |
| `references/engine-action.md` | 动作链5拍+空间感知 | Step 2.2 |
| `references/engine-item.md` | 物品全生命周期 | Step 2.2 |

## Step 2 子文档索引

Step 2（写正文）拆分为以下子文档，按需加载：

| 子文档 | 内容 | 何时加载 |
|--------|------|---------|
| `PRE-CHECK.md` | 前置检查 + 事件拆解分类 + 思维模型 | Step 2.0 |
| `WRITING-CORE.md` | 章节结构模板 + 变体 + 4层内容模型 | Step 2.1 |
| `EVENT-SYSTEM.md` | 按事件序列写作 + 场景搭建规则 | Step 2.2 |
| `CHARACTER-ACTIVATION.md` | 人物鲜活化 + NPC互动规则 | Step 2.3-2.4 |
| `BRANCH-EVENTS.md` | 分支事件占比规则 | Step 2.5 |
| `QUALITY-CHECKLIST.md` | 14项内容丰富度检查 + 字数控制 | Step 2.6-2.7 |

---

## Step 0: 断点检测（续写场景必执行）

当用户说"继续写"/"接着写"时，在Step 1之前执行：

```
1. 检查目标章节文件：glob("novels/{小说名}/正文/第{NNN}章-*.md")
2. 检查writing_finish记录
3. 三态分支：
   (a) 文件不存在 → 正常从Step 1开始
   (b) 文件存在但<2500字且无finish → 🔒提示续写还是重写
   (c) 文件存在且≥2500字 → 🔒提示覆盖还是写下一章
```

新章节跳过此步骤。

---

## Step 1: 引擎加载上下文

读 `references/engine-loading.md`，按三级协议加载：

### Tier 1 必须加载

```
1. writing_start(novel_id, chapter_number) → 基础信息
2. volume_get(volume_id) → 当前卷规划
3. 每个出场人物 character_get → 按需提取:
   - 有对话 → speech_style + catchphrase + personality
   - 有动作 → ability_level + status
   - 有外观 → appearance + gender
4. relation_list → 人物关系（对话语气依据）
```

### Tier 2 按需加载

```
5. world_query(category="location", name="{本章地点}") → 环境档案
6. world_query(category="ability"/"economy", name="{物品名}") → 物品档案
7. world_query(category="history", name="{相关历史}") → 历史层
8. foreshadow_list(status="planted") → 未回收伏笔
```

### Tier 3 增强加载（重要章节时）

```
9. timeline_query(from_chapter=N-3, to_chapter=N) → 近期事件
10. dimension_query(from_chapter=N-3) → 近期变化
```

### 场景快照生成（写前必做）

读 `references/engine-snapshot.md`，生成≤200字速记：

```
地点: {参照环境档案}
时间: {时段+天气}
人物: {出场人物+位置+身体状态}
物品: {关键物品+状态}
目的: {这章的人物目标}
环境基线: {1-2个关键感官细节}
```

---

## Step 3: 状态同步（强制）

### 3.1 质量检查清单

| 检查项 | 标准 |
|--------|------|
| 事件完整性 | 大纲事件全部展开 |
| 事件类型混合 | 5种类型合理混合 |
| 分支事件 | 1-2个大纲外分支，15%-25% |
| 场景搭建 | 每场景100-200字五感铺垫 |
| 世界观植入 | 至少3个元素自然融入 |
| NPC出场 | 至少2个有动机NPC |
| 人物鲜活 | 微表情/动作，禁直白情绪词 |
| 口头禅 | 主要角色口头禅自然出现 |
| 字数达标 | ≥3000字 |
| 线索埋设 | 伏笔已标记并填写foreshadow_plant |
| 人物关系 | 互动体现关系变化 |
| 微动作泄露 | 离别/转折有微动作（禁"不舍""留恋""难过"） |
| 世界观自然度 | 通过场景/动作/对话带出，非角色科普 |
| 逻辑连贯 | 因果清晰，决策符合已知信息 |
| NPC传授途径 | 知识传授有合理途径 |

### 3.2 数据库同步（增量更新）

读 `references/engine-snapshot.md`，执行：

```
1. writing_finish(chapter_id, summary, key_events, characters_involved, ...)
2. timeline_add() → 本章时间线
3. character_update() → 只更新变化的状态字段
4. relation_create/update() → 关系变化
5. foreshadow_plant/recall() → 伏笔回收
6. dimension_log() → 维度变化
7. 角色蒸馏文件 → novels/{小说名}/设定/角色蒸馏/{角色}-V{卷}CH{章}.md
8. 受伤+物品同步 → character.status.injuries + inventory
9. 新设定同步 → world_upsert 写入新物品/异兽/能力/地点/势力
```

### 3.3 拒绝存盘条件

- 总字数 < 2500字
- 大纲事件未完成且无拆分方案
- 世界观植入 < 3个 / NPC < 2个 / 场景搭建缺失
- 人物描写直白（直白情绪词）/ 分支事件 < 15%

---

## Step 4: 存盘

```
novels/{小说名}/正文/第{NNN}章-{标题}.md
```

标题来自大纲或自拟，2-4字。

</supporting-info>
