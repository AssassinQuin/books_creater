# 人物模板

> 权威源：DB `characters` 表。文件为可读副本。
> 本模板定义人物设计的完整维度和字段规范。所有 skill 创建/修改人物时必须遵守。

## DB 字段映射

### 基础信息层（`character_create` 必填）

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| role | role | TEXT | ✅ | protagonist/ally/antagonist/mentor/rival/love_interest/npc |
| race | race | TEXT | ✅ | 种族，来自 world_query(novel_name="这次不一样了", category='race') |
| ability_level | ability_level | TEXT | 觉醒者必填 | 能力等级描述 |
| faction_id | faction_id | INT | 有归属时 | 所属势力ID |

### 外观与性格层

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| appearance | appearance | TEXT | ✅ | 外观简述（≥30字，具体视觉细节） |
| personality | personality | TEXT | ✅ | 性格关键词3-5个 |
| speech_style | speech_style | TEXT | ✅ | 说话风格简述 |
| catchphrase | catchphrase | TEXT | 可选 | 口头禅 |

### 背景与动机层

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| background | background | TEXT | ✅ | 背景故事 |
| goals | goals | TEXT | ✅ | 当前目标 |
| weaknesses | weaknesses | TEXT | ✅ | 弱点/缺陷 |

### 弧线层

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| arc_notes | arc_notes | TEXT | ✅ | 角色弧线备注 |
| first_appearance_chapter | first_appearance_chapter | INT | ✅ | 首次出场章节 |
| status | status | TEXT | 可选 | 当前状态JSON |

---

## 丰富数据层（人物蒸馏7步产出，JSONB字段）

### 外观描写库 (`appearance_detail`)

```json
{
  "gender": "性别",
  "body": "体型/身高/体重/体态特征（具体视觉描写）",
  "face": "脸型/五官/表情特征",
  "hair": "发型/发色/发质/打理方式",
  "skin": "肤色/肤质/疤痕/纹路",
  "clothing_daily": "日常穿着（材质/颜色/功能/来源）",
  "clothing_battle": "战斗/危险场景穿着变化",
  "clothing_logic": "穿衣逻辑（为什么这样穿）",
  "signature_features": [
    "标志特征1（贯穿全文不变）",
    "标志特征2"
  ],
  "appearance_changes": [
    {
      "stage": "V1起点",
      "change": "外观变化描述",
      "trigger": "触发原因"
    }
  ]
}
```

### 决策引擎 (`decision_engine`)

```json
{
  "core_conflict": "核心冲突（如：安全 vs 真相）",
  "daily_state": "日常状态下的决策倾向",
  "trigger_state": "触发条件下的决策转变",
  "escalation_state": "冲突升级时的决策模式",
  "rules": [
    {
      "priority": 1,
      "name": "规则名",
      "description": "规则描述",
      "expression": "行为表现"
    }
  ],
  "dialogue_generation": {
    "step1": "对话生成步骤1",
    "step2": "对话生成步骤2",
    "step3": "对话生成步骤3"
  },
  "action_generation": {
    "step1": "动作生成步骤1",
    "step2": "动作生成步骤2"
  },
  "scene_decisions": [
    {
      "scene": "场景描述",
      "default": "默认反应",
      "deviation": "例外反应",
      "condition": "例外条件"
    }
  ]
}
```

### 对话声音指纹 (`voice_fingerprint`)

```json
{
  "tone": "音色描述（具体比喻）",
  "pace": "语速描述（日常/紧急/下达判断时）",
  "habits": [
    "说话习惯1",
    "说话习惯2"
  ],
  "relation_adjustments": [
    {
      "target": "对方角色名/类别",
      "tendency": "对该人的说话倾向",
      "style": "句式/用词变化",
      "example": "示例对话"
    }
  ],
  "micro_expressions": [
    {
      "context": "情绪/场景",
      "action": "具体动作",
      "meaning": "含义"
    }
  ],
  "subtext_design": "弦外之音设计原则"
}
```

### 能力体系 (`ability_system`)

```json
{
  "core": "能力核心（一句话）",
  "essence": "能力本质描述",
  "stages": [
    {
      "name": "阶段名",
      "volume": "出现卷",
      "description": "阶段描述",
      "trigger": "解锁条件",
      "limits": ["限制1", "限制2"]
    }
  ],
  "pass_mechanism": {
    "name": "传递机制名（如有）",
    "description": "机制描述",
    "rules": ["规则1", "规则2"]
  },
  "teammate_combos": [
    {
      "teammate": "队友名",
      "type": "配合类型",
      "tactic": "配合战术"
    }
  ],
  "global_limits": ["全局限制1", "全局限制2"]
}
```

### 行为模式 (`behavior_pattern`)

```json
{
  "core_drive": "核心驱动（一句话）",
  "decision_logic": "决策逻辑（一句话）",
  "how_to_write": [
    "写法要点1",
    "写法要点2"
  ],
  "emotion_writing": {
    "愤怒": "写法",
    "紧张": "写法",
    "心疼/关心": "写法",
    "失控": "写法"
  },
  "wont_say": ["绝不说的话1", "绝不说的话2"]
}
```

### 当前快照 (`current_snapshot`)

```json
{
  "identity": "当前身份",
  "ability": "当前能力状态",
  "goal": "当前目标",
  "knows": "当前已知信息",
  "doesnt_know": "当前未知信息",
  "relationships": "当前关键关系"
}
```

### 成长轨迹 (`growth_trajectory`)

```json
[
  {
    "volume": "V1",
    "chapter": 1,
    "changes": "本章变化描述",
    "trigger": "触发事件"
  }
]
```

> `growth_trajectory` 为追加式数组，每章写完后通过 `character_increment(growth_add=...)` 追加，不覆盖。

---

## 文件格式（`设定/人物/{名}.md`）

```markdown
# {角色名}

## 基本信息
- **role**: {值}
- **race**: {值}
- **ability_level**: {值}
- **faction_id**: {值}

## 外观与性格
- **appearance**: {值}
- **personality**: {值}
- **speech_style**: {值}
- **catchphrase**: {值}

## 背景与动机
- **background**: {值}
- **goals**: {值}
- **weaknesses**: {值}

## 弧线
- **arc_notes**: {值}
- **first_appearance_chapter**: {值}
- **status**: {值}

## 外观描写库
- **appearance_detail**: {JSON}

## 决策引擎
- **decision_engine**: {JSON}

## 对话声音指纹
- **voice_fingerprint**: {JSON}

## 能力体系
- **ability_system**: {JSON}

## 行为模式
- **behavior_pattern**: {JSON}

## 当前快照
- **current_snapshot**: {JSON}

## 成长轨迹
- **growth_trajectory**: {JSON数组}

## 扩展维度
<!-- 预留：未来新增维度在此追加，格式为 ## {维度名} + - **{field}**: {JSON/TEXT} -->
```

---

## 扩展机制

新增维度时：
1. 在 DB `characters` 表新增 JSONB 列（如 `new_dimension JSONB DEFAULT '{}'`）
2. 在本模板末尾 `## 扩展维度` 部分追加新节
3. 在 `character_create` / `character_update` / `character_increment` MCP 工具中新增对应参数
4. 在 `novel-character/SKILL.md` 的写入DB部分追加字段说明
5. 更新 `consistency_guard` 的字段映射表
