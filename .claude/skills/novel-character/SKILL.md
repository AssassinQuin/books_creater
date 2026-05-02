---
name: novel-character
description: 小说人物设计 — 角色蒸馏法、语音画像、动态状态、关系网构建。触发词：设计人物/加人物/人物卡/加个人物/改人物。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__memory__memory_graph, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_create, mcp__novel-db__relation_list
---

# 小说人物设计

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`（含流程纪律）

## 强制流程

```
Step 1 召回世界观 → Step 2 📝角色蒸馏(4步) → Step 3 🔒写入novel-db → Step 4 交叉验证 → Step 5 git commit
```

每个角色**必须完成蒸馏4步**才能存入。跳过蒸馏直接存视为流程违规。

---

## A3: 人物设计

触发: "设计人物"/"加人物"/"人物卡" | 前置: 世界观已建（可跳过）

1. 读 `.claude/skills/novel-writer/references/character-design.md`，召回 `world_query` 的设定
2. 🔒**对每个角色必须完成蒸馏4步**（萃取→提炼→定标→锻造语音），缺任何一步不可进入 Step 3
3. 引导设计：

   **主角**: 出身/外部目标/内部渴望/性格(用行为定义)/缺陷/习惯/底线/禁忌 + 语音画像 + 初始动态状态
   **核心配角**(至少3人): 各自目标、独立故事线、与主角利益冲突 + 出场节拍器
   **反派**: 合理动机、自己逻辑、站他视角说得通 + 威胁层级 + 认知地图
   **NPC**: 摊贩/酒馆老板/巡逻兵，每人关联1-2条世界观触发

4. 写入 novel-db：
   - `character_create(...)` + `character_update(_status_json={动态状态})`
   - `relation_create(...)` 建关系（含 intensity 和动态 description）
5. **交叉验证**：群像独立检查 + 知识地图 + 世界观触发映射 + 关系网完整性
6. `git commit -m "A3: 人物完成 - {小说名}"`

---

## 角色蒸馏法（摘要）

详细指南见 `.claude/skills/novel-writer/references/character-design.md`

1. **萃取**: 从素材提取外貌、身份、关键行为、他人评价
2. **提炼**: 核心矛盾 + 行为驱动 + 情感锚点
3. **定标**: 用具体行为定义性格，不用形容词
4. **锻造语音**: 句式节奏 + 词汇层 + 情绪偏移 + 3-5句示例对话
