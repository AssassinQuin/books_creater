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
Step 0 断点检测 → Step 1 writing_start → Step 2 写正文 → Step 3 🔒 writing_finish → Step 4 存盘
```

## 规则全在 MCP 中，渐进式加载

**Step 1** 调 `writing_start(novel_id, chapter_number)` → 返回完整的 `writing_prompt`（常驻信息）+ 结构化数据。

### 常驻信息（写在 prompt 中，无需额外加载）
- 章节概览 + 事件清单（写前确认序列，写中逐项勾选）
- 前3章摘要 + 出场人物索引 + 未回收伏笔索引
- 全部规则（硬约束/推荐/创作原则）
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

**核心变化**：不再读文件。所有内容来自 MCP 工具，按需调用。

## 流程说明

- **Step 0**: 断点检测（文件存在且完成→提示写下一章）
- **Step 1**: `writing_start(novel_id, chapter_number)` → 返回 `writing_prompt`（含全部常驻信息+工具指引）
- **Step 2**: 按事件清单写正文。字数不够加微事件不加描写。写对话/动作前调 `character_detail`；需要技法参考调 `engine_detail`；写中可调 `validate_chapter` 自查
- **Step 3**: `writing_finish(chapter_id, chapter_text, summary, key_events, characters_involved, ...)` → MCP 自动校验8条硬约束，不通过拒绝存盘。通过则自动存摘要+质量记录+收伏笔
- **Step 4**: 存盘 `novels/{小说名}/正文/第{NNN}章-{标题}.md`

## 正文纯净化
正文文件禁止包含注释、统计、审计备注等非正文内容。

</what-to-do>
