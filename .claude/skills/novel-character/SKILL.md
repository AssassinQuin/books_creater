---
name: novel-character
description: 小说人物设计。触发词：设计人物/加人物/改人物
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__character_detail, mcp__novel-db__relation_create, mcp__novel-db__relation_list, mcp__novel-db__relation_update, mcp__novel-db__skill_loader
lifecycle: core
---

# 小说人物设计

<what-to-do>

## 强制流程

```
召回世界观 → 角色蒸馏7步 → 外观设计 → 对话设计 → character_create/update + relation_create → 交叉验证
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

详细指南: `engines/character-design.md（编排器通过 skill_loader 注入）`

## 强制外观模板
```
appearance: 具体描写≥30字（体型/面部/发/服饰/标志特征/肤色体态）
race: world_query(category="race")
```
appearance禁止形容词堆砌，必须具体视觉细节。标志特征1-2个贯穿全文。

## 对话设计
`engines/dialogue.md（编排器通过 skill_loader 注入）` 差异化对话协议。
`character_get` 加载说话人档案（speech_style/catchphrase/personality）。
关系调节表覆盖 ≥3 种关系。

## 写入DB
- `character_create(novel_id, name, role, appearance, speech_style, ...)` → 获取 id
  - **必须传入的丰富字段**（人物蒸馏7步产出）：
    - `appearance_detail`: JSON — 外观描写库（gender/body/face/hair/skin/clothing_daily/clothing_battle/clothing_logic/signature_features/appearance_changes）
    - `decision_engine`: JSON — 决策引擎（core_conflict/daily_state/trigger_state/escalation_state/rules/dialogue_generation/action_generation/scene_decisions）
    - `voice_fingerprint`: JSON — 对话声音指纹（tone/pace/habits/relation_adjustments/micro_expressions/subtext_design）
    - `ability_system`: JSON — 能力体系（core/essence/stages/pass_mechanism/teammate_combos/global_limits）
    - `behavior_pattern`: JSON — 行为模式（core_drive/decision_logic/how_to_write/emotion_writing/wont_say）
    - `current_snapshot`: JSON — 当前快照（identity/ability/goal/knows/doesnt_know/relationships）
    - `growth_trajectory`: JSON数组 — 成长轨迹（[{volume,changes,trigger}]）
- `character_update(id, ability_level, status, ...)` → 补充信息（同上字段均可增量更新）
- `relation_create(novel_id, from_id, to_id, relation_type, ...)` → 关系
  - **关系增强字段**：
    - `dialogue_adjustment`: JSON — 对话调节表（对特定人的语气/句式/用词变化）
    - `micro_expressions`: JSON数组 — 微表情词典（[{context,action,meaning}]）
    - `subtext_design`: TEXT — 弦外之音设计

## 修改人物

触发词："改人物"

```
character_get(id) → 评估修改范围 → 执行修改 → character_update
    ↓
relation_list(novel_id) → 筛选受影响关系 → 同步更新或添加关系变化记录
    ↓
git commit（修改摘要 + 影响范围）
```

**修改前必查**：
- 该人物是否有未回收伏笔？（改设定可能破坏因果链）
- 该人物关系网中哪些角色会受影响？
- 外观/能力/性格变更是否需同步更新已写章节？

**修改后必做**：
- 更新 `角色总览.md` 对应章节
- 如能力有变，同步 `ability-system.md` 阶段定义
- 如关系有变，同步 `relationship-tracking.md` 态度追踪

## 能力设计
觉醒者角色必须回答能力7问：`engines/ability.md（编排器通过 skill_loader 注入）` 完整模板。

## 边界条件
- 角色名重复：character_list 检查 → 提示用户选择覆盖或新建
- 外观描写不足：appearance < 30字 → 拒绝存盘，要求补充
- 对话风格缺失：speech_style 为空 → 强制补充后再存
- 关系创建失败：relation_create 返回错误 → 检查 from/to ID 是否有效

</supporting-info>
