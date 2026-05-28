---
name: novel-reviser
description: "[DEPRECATED] 已废弃。功能已合并入 novel-fix。触发词：修复/去重/修文/润色 → 使用 novel-fix。"
lifecycle: deprecated
version: "1.2.0"
---

# ⚠️ 已废弃 — 请使用 novel-fix

> **废弃日期**: 2026-05-28
> **替代方案**: `novel-fix`（含修复/润色/术语修复3种模式）
> **迁移**: 修复/去重/修文/润色 → 触发 `novel-fix`

> 修订不等于改错——每一刀都要服务于叙事目标，而非追求"标准答案"。

<what-to-do>

## 修订总则

1. **同类问题同一章内只改一次**，其余用替代方案（不同措辞/不同角度）
2. **情感高点保留**——战斗高潮、情感爆发、伏笔回收处不做删改
3. **文件修改后必须同步 DB**，否则下游 skill 读到旧数据造成数据漂移
4. **从后往前修改**——同一文件内多行修改时，先改大行号，避免偏移
5. **P0 优先**——P0 修复与 P1 冲突时，P0 优先，P1 顺延重评估
6. **批量修改超过 10 章时分批执行**，每批 5 章，批间确认

## Step 1: 诊断——识别问题源

根据触发来源选择诊断路径（A/B/C/D 四选一）：

### 路径 A：审阅报告修复（最常见）

**1.1 定位报告** — 默认 `novels/{NOVEL_NAME}/审阅报告/正文审阅-{date}.md`，用户提供路径则直接使用。

**1.2 解析报告**（novel-qa 输出协议，详见 supporting-info）：
- 从 `## P0 问题（必须修复）` / `## P1 问题` / `## P2 问题` / `## P3 问题` 章节逐级提取
- 每条格式：`- [{类别}] {描述} | 位置：{文件}:{行号} | 建议修复：{方案}`
- 从 `## 术语合规` 提取违规项，从 `## Smell Test` 确认 AI 味判定

**1.3 排序分组** — P0→P1→P2→P3；同级内按文件分组；标记跨章问题。

**1.4 上下文校验** — Read 每条问题的目标文件（行号 ±20 行），确认报告描述与实际文本一致，调整偏移行号。

### 路径 B：模式去重

**1.1** Grep 扫描 `novels/{NOVEL_NAME}/正文/*.md`，统计目标 pattern 出现次数 N。
**1.2** 标记保留位置（情感高点处保留），其余标记为替换候选。目标：减少至 N/3 以下。

### 路径 C：连续性修复

**1.1** 交叉验证：`character_get_by_name(novel_name=NOVEL_NAME)` + `world_query(novel_name=NOVEL_NAME)`。
**1.2** 标记矛盾点：人物状态（能力/伤势/情绪/位置）、物品逻辑、时间线、世界观。

### 路径 D：风格打磨

**1.1** 加载风格引擎：
- `skill_loader("novel-reviser", "engine", "author-voice")` — 作者声音定义
- `skill_loader("novel-reviser", "engine", "writing-style")` — 写作风格规范
- `skill_loader("novel-reviser", "engine", "anti-ai-quickref")` — AI 指纹速查

**1.2** 扫描目标章节：AI 味检测（旁白式心理总结/过度从容/段落均匀/过渡词堆砌）+ `validate_chapter(text)` 硬约束 + 术语违规扫描（`lorecraft/references/term-map.md`）。

---

## Step 2: 方案生成——制定修改方案

**2.1 加载风格上下文**（所有路径建议加载，路径 D 必选）：
- `skill_loader("novel-reviser", "engine", "author-voice")`
- `skill_loader("novel-reviser", "engine", "writing-style")`
- `skill_loader("novel-reviser", "engine", "anti-ai-quickref")`

**2.2 逐条生成方案**，格式：`{问题ID} | {摘要} | {文件}:{行号} | {修改策略} | {改后预览}`
- 审阅报告修复：优先参考报告"建议修复"字段，结合风格引擎优化
- 模式去重：为替换候选生成替代措辞（保留原意，变化表达）
- 连续性修复：明确需同步更新的 DB 字段
- 风格打磨：标注违反的风格规则编号，给出改后文本

**2.3 冲突检测** — 多方案改同一行/相邻行则合并；方案互相矛盾则标记重评估；跨章联动项单独标记。

**2.4 🔒 展示方案清单**，表格形式（序号 | 文件 | 行号 | 问题 | 策略 | 影响范围），注明跨章联动项和 DB 同步项，**等待用户确认**。

---

## Step 3: 执行——批量修改

**3.0 安全网** — 执行前 `git stash push -m "pre-reviser-{timestamp}"`

**🔒 3.0.1 执行前最终确认** — 展示修改统计（P0×N / P1×N / P2×N / P3×N，涉及×个文件，DB同步×项），确认后才开始修改。

**3.1 逐条执行** — 顺序 P0→P1→P2→P3；同一文件内行号从大到小；每次 Edit 前 Read 确认当前行号。

**3.2 DB 同步（强制——数据一致性铁律）**：
- 首先调 `consistency_guard(novel_name=NOVEL_NAME, auto_sync=True)` 自动同步文件权威数据→DB
- 修订改变了 authoritative 数据时，额外调对应 MCP 工具：

| 变更类型 | 同步工具 | 说明 |
|---------|---------|------|
| 角色状态 | `character_update` | 能力/伤势/情绪/位置变化 |
| 世界观/地点/物品 | `world_upsert` | 设定描写更新 |
| 回收了伏笔 | `foreshadow_recall` | 标记伏笔已回收 |
| 章节摘要/事件 | `writing_finish` | 重新提交更新后的元数据 |

**3.3 批量模式** — 每批 ≤5 章；每批执行完→Step 4 验证→🔒确认→下一批。

---

## Step 4: 验证——确认修改质量

**4.1 硬约束复检** — `validate_chapter(text)` 检查修改后章节；返回 violations 则评估是否本次引入→是则回滚。

**4.2 重复模式复检**（路径 B）— Grep 统计替换后次数，确认 ≤N/3；抽查通顺性。

**4.3 连续性复检**（路径 C）— 重查修改涉及的角色/物品/时间线 DB 数据，确认与文件一致。

**4.4 术语合规复检** — 重新扫描修改区域，确认无术语违规残留，替换用词符合 term-map.md。

**4.5 新问题检测** — 修改是否破坏邻近段落衔接；是否引入新设定矛盾；情感高点是否被误改。

**4.6 输出修订摘要** — 修改条目数（P0/P1/P2/P3）、DB 同步项列表、未修复项及原因。

---

## 边界条件（6 条铁律）

| # | 场景 | 处理规则 |
|---|------|---------|
| 1 | 修改影响多章 | 先展示完整影响范围→🔒确认→批量执行 |
| 2 | 修改引入新矛盾 | 每条修改后验证相关章节一致性，发现矛盾立即回滚 |
| 3 | P0 修复与 P1 冲突 | P0 优先，P1 重新评估是否仍需修改 |
| 4 | 修改后硬约束不达标 | validate_chapter 返回 violations→回滚该条修改 |
| 5 | 批量修改超过 10 章 | 分批执行，每批 5 章，批间验证+确认 |
| 6 | 报告位置与实际不符 | 先 Read 文件确认，以实际文本为准，调整行号 |

## 回滚机制

- **单条回滚**：该条修改验证不通过→Edit 还原该处文本
- **批量回滚**：`git stash pop` 恢复到修改前状态
- **Diff 留痕**：保留每批修改的 git diff，可逐条对比回滚

</what-to-do>

<supporting-info>

## 审阅报告数据协议（novel-qa → novel-reviser）

novel-qa 输出标准 Markdown，novel-reviser 按以下规则解析：

```
## P0 问题（必须修复）         → 提取所有 "- [{类别}]" 行
## P1 问题（限1轮修复）        → 同上
## P2 问题（可延期）/ ## P3    → 可选提取
## 术语合规                   → "详情：{位置→替换建议}" 映射为 Edit 替换
## Smell Test                 → 不通过→该章节进入风格打磨路径
```

每条问题格式：`- [{类别}] {描述} | 位置：{文件}:{行号} | 建议修复：{方案}`
- `位置：novels/{NOVEL_NAME}/正文/第X章.md:{行号}` → 拆为文件路径 + 行号
- `建议修复：{方案}` → 作为修改方案主要参考

## 风格引擎索引

| 引擎 | 加载方式 | 修订中的作用 |
|------|---------|------------|
| 作者声音 | `skill_loader("novel-reviser", "engine", "author-voice")` | 确保改后文字符合作者叙事口吻 |
| 写作风格 | `skill_loader("novel-reviser", "engine", "writing-style")` | 节奏/密度/视角等风格参数校准 |
| 反AI速查 | `skill_loader("novel-reviser", "engine", "anti-ai-quickref")` | 快速识别和消除 AI 写作指纹 |
| 因果引擎 | `skill_loader("novel-reviser", "engine", "causality")` | 修改后验证因果链完整性 |
| 术语映射 | `lorecraft/references/term-map.md` | 术语合规扫描与替换 |

</supporting-info>
