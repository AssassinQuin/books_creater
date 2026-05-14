---
name: novel-character
description: 小说人物设计，含角色蒸馏法、强制外观描写、关系差异化对话和动态状态管理。触发词：设计人物/加人物/改人物
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__memory__memory_graph, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_create, mcp__novel-db__relation_list
lifecycle: core
---

# 小说人物设计

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`
> 对话引擎：读 `.claude/skills/novel-writer/references/engine-dialogue.md`
> **能力体系**: 读 `references/ability-system.md`
> **关系追踪**: 读 `references/relationship-tracking.md`
> **术语定义**: 读项目根目录 `NOVEL-CONTEXT.md`

<what-to-do>
## 强制流程

```
Step 1 召回世界观 → Step 2 📝角色蒸馏(7步) → Step 3 外观+对话设计 → Step 4 质量验证 → Step 5 🔒写入novel-db → Step 6 交叉验证 → Step 7 git commit
```

每个角色**必须完成蒸馏7步+外观+对话**才能存入。跳过任何环节视为流程违规。
</what-to-do>

<supporting-info>

## A3: 人物设计

触发: "设计人物"/"加人物"/"人物卡"/"改人物" | 前置: 世界观已建（可跳过）

1. 读 `references/character-design.md`，召回 `world_query` 的设定
2. 读 `references/ability-system.md`，了解能力体系规范
3. 🔒**对每个角色必须完成蒸馏7步**（萃取→深度→弧线→原型→洋葱→定标→锻造）
4. 🔒**外观设计**（见强制模板）
5. 🔒**对话设计**（见关系差异化协议）
6. 🔒**能力设计**（觉醒者角色必须完成能力七问，见ability-system.md）
7. 引导设计：

   **主角**: Ghost→Lie/Want/Need/弧线/原型/洋葱三层/矛盾特质/共情细节/语音画像 + 初始动态状态
   **核心配角**(至少3人): 各自Want/Need、独立弧线、与主角利益冲突 + 出场节拍器
   **反派**: Ghost→Lie（站他视角说得通）/反派共情三技法 + 威胁层级 + 认知地图
   **NPC**: 摊贩/酒馆老板/巡逻兵，每人关联1-2条世界观触发 + 普遍性翻译

6. **质量验证**：
   - 质量检查8条（一句话渴望/创伤驱动/不舒服缺陷/不同面向/反差/合理路径/深层动机/标志习惯）
   - AI味红线8条（直线弧线/萌点缺陷/好人全干净/坏人全坏/全正确/全改变/全有答案/全对称）
7. 🔒写入 novel-db：`character_create` + `character_update` + `relation_create`
8. **交叉验证**：群像独立检查 + 知识地图 + 世界观触发映射 + 关系网完整性
9. `git commit -m "A3: 人物完成 - {小说名}"`

---

## 强制外观模板

```
gender: {男/女/其他}
appearance: {具体描写，不少于30字}
  - 体型 / 面部 / 头发 / 服饰 / 标志特征 / 肤色体态
race: {种族，关联world_query(category="race")}
```

规则：appearance 禁止形容词堆砌，必须具体视觉细节；外观匹配职业/经济状况；标志特征1-2个贯穿全文。

---

## 关系差异化对话设计

### 语音画像

```
speech_style: {句式节奏} + {词汇层} + {情绪偏移}
catchphrase: {口头禅，0-2句}
```

### 关系调节表（每人至少覆盖3种关系）

| 关系类型 | 语气倾向 | 对话示例 |
|----------|---------|---------|

### 弦外之音设计

为每个角色设定1-2种隐藏情绪表达方式：以动作代心理 / 以环境代情绪 / 以沉默代回答。

---

## 角色蒸馏法（摘要）

详细指南见 `references/character-design.md`

1. **萃取**: 外貌/身份/关键行为/他人评价
2. **深度**: Ghost→Lie + Want/Need + 弧线 + 原型
3. **洋葱三层**: 社会面具 + 自我认知 + 真实内核
4. **矛盾注入**: 主气质×矛盾特质
5. **共情细节**: 6技法选2-3 + 反差 + 标志习惯
6. **定标**: 用具体行为定义性格
7. **锻造语音**: 句式节奏 + 词汇层 + 情绪偏移

---

## 修改人物

触发: "改人物"

1. `character_get({id})` 读取当前档案
2. 🔒 保持外观模板和对话设计完整
3. `character_update` + 检查 `relation_list` 受影响关系
4. 提醒受影响章节
5. `git commit -m "A3: 人物修改 - {角色名}"`

</supporting-info>
