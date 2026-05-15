---
name: novel-chapter-writer
description: 逐章写作引擎，驱动从大纲到成文的完整流程。触发词：写第N章/继续写/写一章
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__writing_start, mcp__novel-db__validate_chapter, mcp__novel-db__writing_finish, mcp__novel-db__rule_detail, mcp__novel-db__character_detail, mcp__novel-db__event_checklist, mcp__novel-db__engine_detail, mcp__novel-db__author_voice, mcp__novel-db__writing_spec, mcp__novel-db__character_get, mcp__novel-db__character_list, mcp__novel-db__relation_list, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_recall, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__timeline_query, mcp__novel-db__volume_get, mcp__novel-db__chapter_list
lifecycle: core
---

# 逐章写作引擎

<what-to-do>

## 强制流程

```
Step 0 断点检测 → Step 1 writing_start → Step 2 写正文(含事件序列确认+场面设计) → Step 3 🔒 writing_finish → Step 4 存盘
```

## 规则全在 MCP 中，渐进式加载

**Step 1** 调 `writing_start(novel_id, chapter_number)` → 返回完整的 `writing_prompt`（常驻信息）+ 结构化数据。

### 常驻信息（写在 prompt 中，无需额外加载）
- 章节概览 + 事件清单（写前确认序列，写中逐项勾选）
- 前3章摘要 + 出场人物索引 + 未回收伏笔索引
- 全部规则（硬约束+创作原则，**全部强制**）
- 质量趋势 + 预警

### 按需钻取（写作中需要时调对应工具）

| 场景 | 工具 | 获得内容 |
|------|------|---------|
| 写对话/动作前需要角色深度信息 | `character_detail(id)` | 外观+性格+说话风格+能力+状态+关系+相关物品 |
| 确认事件序列/标记进度 | `event_checklist(chapter_id)` | 事件清单+检查表 |
| 需要场景/动作/对话/环境/物品引擎参考 | `engine_detail('scene'/'action'/'dialogue'/'environment'/'item')` | 核心技法+示例 |
| 需要作者声音维度 | `author_voice(novel_id)` | 6维声音定义 |
| 需要写作规范 | `writing_spec(novel_id)` | 小说特定的字数/结构/风格要求 |
| 查看某条创作原则完整说明 | `rule_detail('{key}')` | 铁律详细解释 |
| 写中提前校验 | `validate_chapter(chapter_text)` | violations+warnings |

## 流程说明

### Step 0: 断点检测
文件存在且完成→提示写下一章

### Step 1: `writing_start(novel_id, chapter_number)` → 返回 `writing_prompt`
含全部常驻信息+工具指引。

### Step 2: 写正文（增强版）

#### 2.0 事件序列确认（写前必做）
从 `writing_start` 返回的事件清单中确认：

```
□ 本章核心事件的因果链完整吗？
  因为{前因} → 所以{后果} → 逼出{角色选择}
  
□ 微事件是否覆盖：
  费笔≥2条（纯纹理，不回收不解释）
  日常≥2条（生活细节/习惯/物价）
  世界呼吸≥2条（势力痕迹/他人生活/系统运作）

□ 本章出场角色都"有理由在场"吗？
  （不为出场而出场）

□ 伏笔节点检查：需要埋设/提起的伏笔已确认？
```

#### 2.1 场面设计清单（写前必做）
对本章每个场面（2-4个），设计：

```
场面{N} | 密度: {轻量/中量/重量/大场面}
- 时间/地点:
- 人物及目标（角色矩阵）:
  · 角色A: 想{什么} / 障碍{什么} / 对B: {态度}
  · 角色B: 想{什么} / 障碍{什么} / 对A: {态度}
- 核心事件:
- 微事件分配: 费笔__ / 日常__ / 世界呼吸__
- 伏笔操作: 埋设/提起/回收
- 镜头序列: 建立→{对话/动作/反应}→插入→收束
```

**场面密度参考**（来自 scene-composition-guide.md）：

| 密度 | 人物 | 字数 | 适用场景 | 章内占比 |
|------|------|------|---------|---------|
| 轻量 | 1-2人 | 500-800 | 过渡/独处/信息投放 | 15-20% |
| 中量 | 2-3人 | 800-1500 | 对话博弈/关系推进 | 30-40% |
| 重量 | 3-5人 | 1500-2500 | 团队互动/多立场碰撞 | 30-40% |
| 大场面 | 5+人 | 2500-3500 | 群像戏/战斗/高潮 | 可占整章 |

**规则**: 每章至少1个中量以上场面。连续2个轻量后必须接中量或重量。

#### 2.2 写正文
写对话/动作前调 `character_detail`；需要技法参考调 `engine_detail`。

写中优先保证事件密度（每句话做≥2件事，见场景深化指南），其次才是字数达标。

#### 2.3 写中自查
调 `validate_chapter` 自查，若返回 `enrichment` 字段（PUA 风格字数不足指引），**必须**按其 L1/L2/L3 强制动作执行：
- L1(<20%): 选1个 engine_detail 展开
- L2(20-50%): 因果链展开/Telling→Showing/加子冲突
- L3(>50%): 大纲中找未使用的事件加

注意：字数不足的第一优先级是加微事件（费笔/日常/世界呼吸），不是扩描写。

### Step 3: 🔒 `writing_finish`
`writing_finish(chapter_id, chapter_text, summary, key_events, characters_involved, ...)`

MCP 自动校验全部硬约束（含标点密度/否定句式/字数/标点多样性/对话打断等），不通过拒绝存盘。

若返回 `enrichment` 字段，**必须**按 L1→L2→L3 阶梯充实后重新调用，不准原样重调和磨洋工。每次 reject 后必须比上次更努力。

**写后自检（增强版）**：
```
事件完整性:
□ 核心事件的因果链完整（前因→后果→选择）
□ 微事件≥6条（费笔≥2/日常≥2/世界呼吸≥2）
□ 本章留下的"未闭合"尾巴是什么

场面质量:
□ 每章至少1个中量以上场面
□ 多人物场景使用角色矩阵
□ 关键对话有潜台词层
□ 费笔不回收不解释

世界观刑具化:
□ 世界观规则在本章对角色产生压力
□ 势力痕迹自然存在（不为出场而出场）
```

通过后自动存摘要+质量记录+收伏笔。

### Step 4: 存盘
`novels/{小说名}/正文/第{NNN}章-{标题}.md`

## 正文纯净化
正文文件禁止包含注释、统计、审计备注等非正文内容。

</what-to-do>
