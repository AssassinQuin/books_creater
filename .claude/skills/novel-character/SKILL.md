---
name: novel-character
description: 小说人物设计/修改。触发词：设计人物/加人物/改人物/优化人物/人物卡。涉及新建或修改角色档案时触发。新建流程：DB采集世界观→蒸馏7步→外观→对话→同步DB+文件。修改流程：DB读完整数据→评估范围→改文件→确认→同步DB→consistency_guard→(可选)达尔文优化。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__character_detail, mcp__novel-db__relation_create, mcp__novel-db__relation_list, mcp__novel-db__relation_update, mcp__novel-db__skill_loader, mcp__novel-db__consistency_guard
lifecycle: core
depends_on: novel-planner, lorecraft, engines/character-design, engines/ability, engines/dialogue
version: "1.3.0"
---

# 小说人物设计

## 核心原则

**DB优先**：人物数据权威源在 DB（`characters` 表）。文件为可读副本。
- 新建：先 `character_create` 写入 DB，再写文件
- 修改：先 `character_detail_by_name(novel_name="NOVEL_NAME", character_name={name})` 读取 DB 完整数据，再改文件，再 `character_update` + `consistency_guard` 同步

**正向定义原则**：直接写"是什么"，避免用否定句式描述（如"不是什么"）。否定式定义会稀释特征浓度，让读者记住的是模糊轮廓而非鲜明形象。

---

<what-to-do>

## 新建人物流水线

```
Phase 1: 数据采集（DB优先）
  world_query(novel, category='race') + character_list → 避免重名
  如有参照角色 → character_detail_by_name(novel_name="NOVEL_NAME", character_name={name}) 获取完整档案
  ↓
Phase 2: 角色蒸馏7步
  萃取→深度(含弧线+原型)→洋葱→矛盾注入→共情细节→定标→锻造
  核心角色每步深挖；次要角色/NPC可精简但保留每步的核心产出
  ↓
Phase 3: 外观+对话设计 → 用户确认方案
  appearance 占角色档案整体篇幅的 5%-15%（核心角色取上限，NPC 取下限），race、speech_style、relation_adjustments 覆盖 ≥3 种关系类型
  ↓
Phase 4: 写入DB + 文件同步
  character_create(含JSONB字段) → sync_db_to_files(data_type='character')
  → relation_create → consistency_guard(novel, auto_sync=True)
```

## 修改人物流水线

```
Phase 1: 数据采集（DB优先）
  character_detail_by_name(novel_name="NOVEL_NAME", character_name={name}) + world_query(novel) + relation_list(novel)
  volume_get(novel_name="NOVEL_NAME", volume_number={N}) → 了解出场场景
  如有伏笔 → foreshadow_list(character_id=id)
  ↓
Phase 2: 评估修改范围 → 用户确认
  列出影响项：关系/能力/伏笔/已写章节/其他设定文件
  ↓
Phase 3: 执行修改（写入DB，不直接写文件）
  character_update_by_name(novel_name="NOVEL_NAME", character_name={name}, 变更字段...)
  sync_db_to_files(data_type='character')
  ⚠️ 正向定义原则：用"是什么"直接描述，避免"不是什么"的否定式补丁
  ↓
Phase 4: 用户确认修改结果
  展示改了什么+为什么+影响范围
  ↓
Phase 5: 级联同步
  relation_update → sync_db_to_files(data_type='character') → consistency_guard(auto_sync)
```

</what-to-do>

<supporting-info>

## 角色蒸馏7步详解

> **Phase 2 开始前**：`skill_loader("novel-character", "engine", "character-design")` 加载引擎。
> 核心角色每步深挖（每步≥3句具体描述），次要角色/NPC 可精简但保留每步的核心产出。

| 步 | 名称 | 执行要点 | 产出示例 |
|----|------|---------|---------|
| 1 | 萃取 | 提取外貌特征（≤2个标志特征）、身份标签、关键行为模式、他人评价。用**具体可感知的特征**，不用形容词堆砌 | "左眉有旧疤/说话前先叹气/同事说他'从不回头'" |
| 2 | 深度 | Ghost（过去创伤）→ Lie（错误信念）→ Want（表层欲望）→ Need（深层需求）→ 弧线方向 → 原型（捣蛋者/守护者/智者等） | Ghost:被师门驱逐→Lie:"力量等于安全"→Want:变强→Need:接受脆弱 |
| 3 | 洋葱三层 | 社会面具（对外展示）→ 自我认知（自己认为）→ 真实内核（实际）。三层之间必须有裂缝 | 面具：冷酷守信 / 自我：正义执行者 / 内核：害怕被抛弃 |
| 4 | 矛盾注入 | 主气质 × 矛盾特质 = 让人不舒服的缺陷。**🔐 检查点**：矛盾必须足够尖锐，读者初见时会"不喜欢但记住了" | 最冷静的人最冲动 / 最忠诚的人最善谎 |
| 5 | 共情细节 | 从6技法（反差/脆弱/固执/温柔/幽默/独处）中选2-3个 + 反差场景 + 标志习惯（口头禅/小动作） | 开打前先整理袖口/紧张时反而话多 |
| 6 | 定标 | 用**具体行为**定义性格，不用形容词。每条≤15字 | ❌"他很固执" → ✅"同一个问题被拒绝三次仍要问第四次" |
| 7 | 锻造语音 | 句式节奏（长句/短句/省略）+ 词汇偏好 + 情绪偏移（紧张vs放松时如何变化）+ 对不同人的温差 | 对上级：短句敬语 / 对朋友：反讽长句 / 对敌人：沉默 |

**🔐 检查点（Step 4 后）**：展示前4步蒸馏结果给用户，确认矛盾注入足够尖锐后再继续 Step 5-7。

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

- **appearance** 占角色档案整体篇幅的 5%-15%，核心角色取上限，NPC 取下限；避免形容词堆砌（如"美丽的""高大的"），用具体可感知的特征让读者自行形成印象；标志特征控制在 1-2 个并贯穿全文，过多则分散记忆点
- **race** 从 DB 取值：`world_query(novel, category='race')`
- **speech_style** 需要具体内容，relation_adjustments 覆盖 ≥3 种关系类型
- **觉醒者角色** 必须回答能力7问：`engines/ability.md`
- **对话设计** 参考 `engines/dialogue.md`
- **角色蒸馏7步**：核心角色每步深挖，次要角色/NPC 精简但保留每步的核心产出
- **🔒 术语规范**：角色设计中的能力名称、势力归属、世界观相关描述遵循 `lorecraft/references/term-map.md` 术语映射（如能力描述中用灵能术语替代现代术语）；角色口头禅和说话风格中涉及世界观概念时使用口语层术语（参考 term-map「角色口语」列）

## 边界条件

| 场景 | 处理 |
|------|------|
| 角色名重复 | character_list 检查 → 提示覆盖/新建 |
| appearance 篇幅不足角色档案 5% | 拒绝存盘，要求补充具体可感知的特征描写 |
| speech_style 为空 | 强制补充后再存 |
| relation_create 失败 | 检查 from/to ID 是否有效 |
| DB 读取失败 | 回退读本地文件 |
| DB 查无此人 | 提示先确认角色名是否存在于 DB |
| 角色关联未回收伏笔 | 修改前警告，用户确认后再改 |
| consistency_guard 失败 | 手动同步：先写 DB → 再写文件 或反之 |

</supporting-info>
