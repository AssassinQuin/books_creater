---
name: novel-character
description: 小说人物设计/修改。触发词：设计人物/加人物/改人物/优化人物/人物卡。涉及新建或修改角色档案时触发。新建流程：DB采集世界观→蒸馏7步→外观→对话→同步DB+文件。修改流程：DB读完整数据→评估范围→改文件→确认→同步DB→consistency_guard→(可选)达尔文优化。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__character_detail, mcp__novel-db__relation_create, mcp__novel-db__relation_list, mcp__novel-db__relation_update, mcp__novel-db__skill_loader, mcp__novel-db__consistency_guard
lifecycle: core
---

# 小说人物设计

## 核心原则

**DB优先**：人物数据权威源在 DB（`characters` 表）。文件为可读副本。
- 新建：先 `character_create` 写入 DB，再写文件
- 修改：先 `character_detail_by_name(novel_name="这次不一样了", character_name={name})` 读取 DB 完整数据，再改文件，再 `character_update` + `consistency_guard` 同步

**禁止补丁式说明**：直接写"是什么"，不写"不是什么"。

---

<what-to-do>

## 新建人物流水线

```
Phase 1: 数据采集（DB优先）
  world_query(novel, category='race') + character_list → 避免重名
  如有参照角色 → character_detail_by_name(novel_name="这次不一样了", character_name={name}) 获取完整档案
  ↓
Phase 2: 角色蒸馏7步
  萃取→深度(含弧线+原型)→洋葱→矛盾注入→共情细节→定标→锻造
  核心角色每步深挖；次要角色/NPC可精简但禁止跳过
  ↓
Phase 3: 外观+对话设计 → 用户确认方案
  appearance ≥30字、race、speech_style、relation_adjustments≥3种
  ↓
Phase 4: 写入DB + 文件同步
  character_create(含JSONB字段) → 写 设定/人物/{名}.md
  → relation_create → consistency_guard(novel, auto_sync=True)
```

## 修改人物流水线

```
Phase 1: 数据采集（DB优先）
  character_detail_by_name(novel_name="这次不一样了", character_name={name}) + world_query(novel) + relation_list(novel)
  Read 相关卷大纲/章节 → 了解出场场景
  如有伏笔 → foreshadow_list(character_id=id)
  ↓
Phase 2: 评估修改范围 → 用户确认
  列出影响项：关系/能力/伏笔/已写章节/其他设定文件
  ↓
Phase 3: 执行修改
  改 设定/人物/{名}.md（遵守 character.md 模板）
  同步更新受影响的设定文件
  ⚠️ 禁止补丁式说明
  ↓
Phase 4: 用户确认修改结果
  展示改了什么+为什么+影响范围
  ↓
Phase 5: 同步DB
  character_update_by_name(novel_name="这次不一样了", character_name={name}, 变更字段...) → relation_update → consistency_guard(auto_sync)
```

</what-to-do>

<supporting-info>

## 角色蒸馏7步详解

| 步 | 名称 | 说明 |
|----|------|------|
| 1 | 萃取 | 外貌/身份/关键行为/他人评价 |
| 2 | 深度 | Ghost→Lie + Want/Need + 弧线 + 原型 |
| 3 | 洋葱三层 | 社会面具 + 自我认知 + 真实内核 |
| 4 | 矛盾注入 | 主气质×矛盾特质（让人不舒服的缺陷） |
| 5 | 共情细节 | 6技法选2-3 + 反差 + 标志习惯 |
| 6 | 定标 | 用具体行为定义性格（非形容词） |
| 7 | 锻造语音 | 句式节奏 + 词汇层 + 情绪偏移 |

详细指南：`engines/character-design.md`（编排器通过 skill_loader 注入）。

## 写入DB字段速查

### character_create / character_update

| 字段 | 类型 | 说明 |
|------|------|------|
| appearance_detail | JSON | 外观描写库（body/face/hair/skin/clothing_daily/battle/logic/signature_features/appearance_changes） |
| decision_engine | JSON | 决策引擎（core_conflict/rules/daily/trigger/escalation/scene_decisions） |
| voice_fingerprint | JSON | 声音指纹（tone/pace/habits/relation_adjustments/micro_expressions/subtext_design） |
| ability_system | JSON | 能力体系（core/essence/stages/teammate_combos/global_limits） |
| behavior_pattern | JSON | 行为模式（core_drive/decision_logic/how_to_write/emotion_writing/wont_say） |
| current_snapshot | JSON | 当前快照（identity/ability/goal/knows/doesnt_know/relationships） |
| growth_trajectory | JSON[] | 成长轨迹（[{volume,changes,trigger}]） |

### relation_create 增强字段

| 字段 | 类型 | 说明 |
|------|------|------|
| dialogue_adjustment | JSON | 对话调节表（语气/句式/用词变化） |
| micro_expressions | JSON[] | 微表情词典（[{context,action,meaning}]） |
| subtext_design | TEXT | 弦外之音设计 |

## 强制约束

- **appearance** ≥30字，禁止形容词堆砌，标志特征1-2个贯穿全文
- **race** 从 DB 取值：`world_query(novel, category='race')`
- **speech_style** 不可为空，relation_adjustments 覆盖 ≥3 种关系
- **觉醒者角色** 必须回答能力7问：`engines/ability.md`
- **对话设计** 参考 `engines/dialogue.md`
- **角色蒸馏7步**：核心角色每步深挖，次要角色/NPC 精简但禁止跳过任意步骤

## 边界条件

| 场景 | 处理 |
|------|------|
| 角色名重复 | character_list 检查 → 提示覆盖/新建 |
| appearance < 30字 | 拒绝存盘，要求补充 |
| speech_style 为空 | 强制补充后再存 |
| relation_create 失败 | 检查 from/to ID 是否有效 |
| DB 读取失败 | 回退读本地文件 |
| DB 查无此人 | 提示先确认角色名是否存在于 DB |
| 角色关联未回收伏笔 | 修改前警告，用户确认后再改 |
| consistency_guard 失败 | 手动同步：先写 DB → 再写文件 或反之 |

</supporting-info>
