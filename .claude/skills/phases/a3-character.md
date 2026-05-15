# A3 人物设计阶段指令

> 本文件只包含人物设计阶段的执行指令。
> 需要时加载：engines/character-design.md, engines/ability.md, engines/dialogue.md, engines/relationship.md

## 输入

- 世界观数据（`world_query`）
- 已有角色列表（`character_list`）
- 决策卡中的核心冲突

## 执行步骤

### Step 1: 角色蒸馏7步

加载 `engines/character-design.md` → 逐步执行：
1. **萃取**: 外貌/身份/关键行为/他人评价
2. **深度**: Ghost→Lie + Want/Need + 弧线 + 原型
3. **洋葱三层**: 社会面具 + 自我认知 + 真实内核
4. **矛盾注入**: 主气质×矛盾特质
5. **共情细节**: 6技法选2-3 + 反差 + 标志习惯
6. **定标**: 用具体行为定义性格
7. **锻造语音**: 句式节奏 + 词汇层 + 情绪偏移

**必须完整7步，跳过=流程违规。**

### Step 2: 外观设计

强制外观模板：
- appearance: 具体描写≥30字（体型/面部/发/服饰/标志特征/肤色体态）
- race: `world_query(category="race")`
- 禁止形容词堆砌，必须具体视觉细节
- 标志特征1-2个贯穿全文

### Step 3: 对话设计

加载 `engines/dialogue.md` → 设计：
- 句式节奏
- 词汇层
- 情绪偏移
- 关系调节表（≥3种关系）

### Step 4: 能力设计（觉醒者角色）

加载 `engines/ability.md` → 回答能力7问。

### Step 5: 关系设计

加载 `engines/relationship.md` → 设计角色关系网：
- `relation_create` 创建关系
- 确保关系差异化（不同关系类型有不同互动模式）

### Step 6: 写入DB

```python
character_create(novel_id, name, role, appearance, speech_style, ...)
character_update(id, ability_level, status, ...)
relation_create(novel_id, from_id, to_id, relation_type, ...)
```

## 输出

- 状态总线.setting.characters 更新
- 文件: `设定/人物/{名}.md`
- DB: `character_create` + `relation_create`