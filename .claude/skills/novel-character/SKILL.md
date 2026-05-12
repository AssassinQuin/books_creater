---
name: novel-character
description: 小说人物设计 — 角色蒸馏法（含Ghost→Lie+Want/Need深度方法论）、强制外观描写、关系差异化对话、语音画像、动态状态、关系网构建。触发词：设计人物/加人物/人物卡/加个人物/改人物。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__memory__memory_graph, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_create, mcp__novel-db__relation_list
---

# 小说人物设计

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`（含流程纪律）
> 对话引擎：读 `.claude/skills/novel-writer/references/engine-dialogue.md`

## 强制流程

```
Step 1 召回世界观 → Step 2 📝角色蒸馏(7步) → Step 3 外观+对话设计 → Step 4 质量验证 → Step 5 🔒写入novel-db → Step 6 交叉验证 → Step 7 git commit
```

每个角色**必须完成蒸馏7步+外观+对话**才能存入。跳过任何环节视为流程违规。

---

## A3: 人物设计

触发: "设计人物"/"加人物"/"人物卡"/"改人物" | 前置: 世界观已建（可跳过）

1. 读 `references/character-design.md`，召回 `world_query` 的设定
2. 🔒**对每个角色必须完成蒸馏7步**（萃取→深度→弧线→原型→洋葱→定标→锻造），缺任何一步不可进入 Step 3
3. 🔒**外观设计**（见下方强制模板）
4. 🔒**对话设计**（见下方关系差异化协议）
5. 引导设计：

   **主角**: 出身/Ghost→Lie/Want/Need/弧线/原型/洋葱三层/矛盾特质/共情细节/语音画像 + 初始动态状态
   **核心配角**(至少3人): 各自Want/Need、独立弧线、与主角利益冲突 + 出场节拍器
   **反派**: Ghost→Lie（站他视角说得通）/反派共情三技法 + 威胁层级 + 认知地图
   **NPC**: 摊贩/酒馆老板/巡逻兵，每人关联1-2条世界观触发 + 普遍性翻译

6. **质量验证**（每个角色过检）：
   - 质量检查清单8条（一句话渴望/创伤驱动/不舒服缺陷/不同面向/反差/合理路径/深层动机/标志习惯）
   - AI味红线8条（直线弧线/萌点缺陷/好人全干净/坏人全坏/全正确/全改变/全有答案/全对称）
7. 🔒写入 novel-db：
   - `character_create(...)` + `character_update(_status_json={动态状态})`
   - `relation_create(...)` 建关系（含 intensity 和动态 description）
8. **交叉验证**：群像独立检查 + 知识地图 + 世界观触发映射 + 关系网完整性
9. `git commit -m "A3: 人物完成 - {小说名}"`

---

## 强制外观模板

每个角色**必须填写**以下字段，写入 `character_create` 对应参数：

```
gender: {男/女/其他}
appearance: {具体描写，不少于30字}
  - 体型: {瘦削/结实/矮胖/高挑/中等}
  - 面部: {脸型/眉眼/嘴/疤/特征}
  - 头发: {长短/颜色/扎法/是否乱}
  - 服饰: {常穿什么/质感/磨损程度}
  - 标志特征: {一眼能认出来的细节}
  - 肤色/体态: {与职业/生活环境匹配}
race: {种族，关联world_query(category="race")}
```

**规则**：
- appearance 不能用形容词堆砌（"高大帅气"），必须用具体视觉细节（"下巴有道旧疤，笑的时候扯着嘴角"）
- 外观必须与职业/生活环境/经济状况匹配（拾荒者不会穿干净衣服）
- 标志特征是读者记住角色的锚点，每角色1-2个，贯穿全文不变

---

## 关系差异化对话设计

基于 `engine-dialogue.md`，为每个角色设计**对每类关系**的说话方式：

### 语音画像（speech_style + catchphrase）

```
speech_style: {句式节奏: 短句/长句/碎句/正式/方言}
              {词汇层: 粗糙/文雅/术语多/口语化}
              {情绪偏移: 话少/话多/冷淡/热情}
catchphrase: {口头禅，0-2句，不要硬造}
```

### 关系调节表（每人至少覆盖3种关系）

| 关系类型 | 语气倾向 | 对话示例 |
|----------|---------|---------|
| 对战友/信任者 | {该角色的信任表达方式} | {1-2句示例} |
| 对陌生人 | {该角色的警惕/好奇/冷漠} | {1-2句示例} |
| 对弱者/下属 | {该角色的态度} | {1-2句示例} |
| 对敌人/竞争者 | {该角色的对抗方式} | {1-2句示例} |

写入 `relation_create(description={关系描述中的对话风格说明})`

### 弦外之音设计

为每个角色设定1-2种**隐藏情绪的表达方式**：
- 不说破的技法：以动作代心理 / 以环境代情绪 / 以沉默代回答 / 以重复代执念
- 微表情锚点：紧张时攥什么 / 压抑时嘴角怎样 / 不想多说时怎么回应

---

## 角色蒸馏法（摘要）

详细指南见 `references/character-design.md`

1. **萃取**: 从素材提取外貌、身份、关键行为、他人评价
2. **深度**: Ghost→Lie因果链 + Want/Need矛盾 + 弧线类型判定 + 原型匹配
3. **洋葱三层**: 社会面具 + 自我认知 + 真实内核
4. **矛盾注入**: 主气质×矛盾特质 = 化学反应
5. **共情细节**: 6技法选2-3 + 反差 + 标志习惯 + 不完美时刻 + 普遍性翻译
6. **定标**: 用具体行为定义性格，不用形容词
7. **锻造语音**: 句式节奏 + 词汇层 + 情绪偏移 + 3-5句示例对话

---

## 修改人物

触发: "改人物"

1. `character_get({id})` 读取当前档案
2. 🔒 修改后必须保持外观模板和对话设计完整
3. `character_update({id}, ...)` 更新变化字段
4. 如果修改影响关系 → `relation_list` 检查受影响的关系并更新
5. 如果修改影响已写章节 → 提醒用户受影响的章节范围
6. `git commit -m "A3: 人物修改 - {角色名}"`
