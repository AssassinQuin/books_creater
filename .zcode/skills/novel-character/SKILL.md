---
name: novel-character
description: 小说人物设计（达尔文版·ZCode 文件流优化）— 角色蒸馏法4步、语音画像、动态状态、关系网构建。触发词：设计人物/加人物/人物卡/加个人物/改人物/人物采访。
---

# 小说人物设计（novel-character）

> 源自达尔文优化版，移植到 ZCode 文件流。共享铁律见 `.zcode/knowledge/legacy/novel-writer/references/shared-conventions.md`。

## 强制流程

```
Step 1 召回世界观 → Step 2 📝角色蒸馏(4步) → Step 3 🔒落盘角色文件 → Step 4 交叉验证 → Step 5 git commit
```

每个角色**必须完成蒸馏4步**才能落盘。跳过蒸馏直接写文件视为流程违规。

## ZCode 编排

- **主力子 agent**：`character-smith`（简报 `.zcode/agents/character-smith.md`）；蒸馏4步、语音画像、交叉验证都 spawn 它执行
- **spawn 前**：`ref_route(人物设计)` 把权威文件清单（含历史 257 行深度指南）贴进任务提示；需要成熟作品的人物模式时加 `ref_search(query, scope="borrow")`
- 断点续传：`novels/{书名}/设定/角色/` 已有文件数 vs 用户意图

---

## A3: 人物设计

触发: "设计人物"/"加人物"/"人物卡" | 前置: 世界观已建（可跳过）

1. 读 `.zcode/knowledge/legacy/novel-writer/references/character-design.md`，召回 `novels/{书名}/设定/世界观/` 设定
2. 🔒**对每个角色必须完成蒸馏4步**（萃取→提炼→定标→锻造语音），缺任何一步不可进入 Step 3
3. 引导设计：

   **主角**: 出身/外部目标/内部渴望/性格(用行为定义)/缺陷/习惯/底线/禁忌 + 语音画像 + 初始动态状态
   **核心配角**(至少3人): 各自目标、独立故事线、与主角利益冲突 + 出场节拍器
   **反派**: 合理动机、自己逻辑、站他视角说得通 + 威胁层级 + 认知地图
   **NPC**: 摊贩/酒馆老板/巡逻兵，每人关联1-2条世界观触发

4. 落盘（文件流替代 character_create/relation_create）：
   - `novels/{书名}/设定/角色/{角色名}.md` — 人设卡 + 语音画像 + 动态状态（当前目标/位置/知道什么/想要什么）
   - `novels/{书名}/设定/关系.md` — 关系网（关系类型/强度/动态描述），append 或重写
   - 已进入正文的项目：核心角色同时 `tracking_commit` 更新角色快照
5. **交叉验证**（spawn `character-smith` 执行）：群像独立检查 + 知识地图 + 世界观触发映射 + 关系网完整性
6. `git commit -m "A3: 人物完成 - {角色名/批次}"`

---

## 角色蒸馏法（摘要）

详细指南见 `.zcode/knowledge/legacy/novel-writer/references/character-design.md`

1. **萃取**: 从素材提取外貌、身份、关键行为、他人评价
2. **提炼**: 核心矛盾 + 行为驱动 + 情感锚点
3. **定标**: 用具体行为定义性格，不用形容词
4. **锻造语音**: 句式节奏 + 词汇层 + 情绪偏移 + 3-5句示例对话
