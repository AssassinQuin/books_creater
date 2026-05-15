---
name: novel-character
description: 小说人物设计，含角色蒸馏法、强制外观描写、关系差异化对话和动态状态管理。触发词：设计人物/加人物/改人物
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_create, mcp__novel-db__relation_list, mcp__novel-db__skill_loader
lifecycle: core
---

# 小说人物设计

<what-to-do>

## 强制流程

```
召回世界观 → 角色蒸馏7步 → 外观设计 → 对话设计 → character_create/update + relation_create → 🔒交叉验证
```

**角色蒸馏7步必须完整**：萃取→深度→弧线→原型→洋葱→定标→锻造。跳过=流程违规。

</what-to-do>

<supporting-info>

## 角色蒸馏7步
1. **萃取**: 外貌/身份/关键行为/他人评价
2. **深度**: Ghost→Lie + Want/Need + 弧线 + 原型
3. **洋葱三层**: 社会面具 + 自我认知 + 真实内核
4. **矛盾注入**: 主气质×矛盾特质
5. **共情细节**: 6技法选2-3 + 反差 + 标志习惯
6. **定标**: 用具体行为定义性格
7. **锻造语音**: 句式节奏 + 词汇层 + 情绪偏移

详细指南: `skill_loader("novel-character", "engine", "character-design")`

## 强制外观模板
```
appearance: 具体描写≥30字（体型/面部/发/服饰/标志特征/肤色体态）
race: world_query(category="race")
```
appearance禁止形容词堆砌，必须具体视觉细节。标志特征1-2个贯穿全文。

## 对话设计
`skill_loader("novel-character", "engine", "dialogue")` 差异化对话协议。
`character_get` 加载说话人档案（speech_style/catchphrase/personality）。
关系调节表覆盖 ≥3 种关系。

## 写入DB
- `character_create(novel_id, name, role, appearance, speech_style, ...)` → 获取 id
- `character_update(id, ability_level, status, ...)` → 补充信息
- `relation_create(novel_id, from_id, to_id, relation_type, ...)` → 关系

## 修改人物
触发："改人物"
`character_get(id)` → 修改 → `character_update` → 检查 `relation_list` 受影响关系 → git commit

## 能力设计
觉醒者角色必须回答能力7问：`skill_loader("novel-character", "engine", "ability")` 完整模板。

</supporting-info>
