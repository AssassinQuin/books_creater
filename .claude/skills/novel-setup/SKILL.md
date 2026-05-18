---
name: novel-setup
description: 小说项目基建。触发词：头脑风暴/建世界观/设定/加物品
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__*, mcp__memory__*
lifecycle: core
depends_on: novel-writer, lorecraft, engines/worldbuilding, engines/causality, engines/item
version: "1.2.0"
---

# 小说项目基建

<what-to-do>

## 强制流程

```
A1: 头脑风暴 → novel_create → 逐问深挖 → 🔒输出决策卡 → git commit
A2: world_query(已有) → 逐维度展开 → world_upsert → 🔒确认 → 交叉验证 → git commit
物品: world_query(查重) → skill_loader(engine,"item") → world_upsert → 🔒确认
```

所有 `world_upsert` 后必须 🔒 用户确认。

</what-to-do>

<supporting-info>

## A1: 项目启动（触发：头脑风暴/灵感）

### Step 1: 项目创建

1. 确认小说名，`novel_create(novel_name={name})` 创建项目
2. 如 novel_create 失败 → 提示用户检查是否重名，或手动确认后覆盖
3. 创建成功 → `novel_update(novel_name=NOVEL_NAME, genre="", status="brainstorm")`

### Step 2: 逐问深挖（每次只问一个，用户回答后再问下一个）

五个核心问题按序推进：

| # | 问题方向 | 深挖目的 | 典型追问 |
|---|---------|---------|---------|
| 1 | 画面 | 确立故事基调 | "你脑海中最先出现的画面是什么？" |
| 2 | 主角 | 确立核心视角 | "谁是这个世界的切入点？" |
| 3 | 情绪 | 确立读者体验目标 | "读完后你希望读者有什么感受？" |
| 4 | 对立面 | 确立核心冲突 | "什么在阻挡主角？" |
| 5 | 独特规则 | 确立世界观差异化 | "这个世界和现实最大的不同是什么？" |

每次回答后 `memory_store(content={回答摘要}, tags=["project:{NOVEL_NAME}", "idea"])`，后续流程可回溯。

### Step 3: 🔒 输出决策卡

向用户展示结构化决策卡，等待确认后才进入 A2：

```
【项目决策卡】
小说名：{name}
核心冲突：{一句话}
主线方向：{起→承→转→合 概述}
读者情绪：{目标情绪曲线}
亮点场景：{2-3个预设高光时刻}
品类节奏：{玄幻/仙侠/都市/科幻/末世} → 对应节奏模板

输入"OK"进入世界观建模（A2），或修改任意项。
```

### Step 4: 存档

- 用户确认 → `novel_update(genre={品类}, status="worldbuilding")`
- 创作决策做 ADR：`docs/decisions/ADR-TEMPLATE.md`
- `git commit -m "A1: {小说名}项目启动+决策卡"`

---

## A2: 世界观建模（触发：建世界观 | 前置：A1决策卡已确认）

### Step 1: 数据采集

1. `world_query(novel_name=NOVEL_NAME)` 查已有维度
2. 加载术语规范：`Read(".claude/skills/lorecraft/SKILL.md")` + `Read(".claude/skills/lorecraft/references/term-map.md")`
3. 加载世界构建引擎：`skill_loader("novel-setup", "engine", "worldbuilding")`

### Step 2: 逐维度展开（8维度）

| 维度 | 说明 | 输出 |
|------|------|------|
| 种族 | 种族体系、生理特征、文化差异 | `world_upsert(category='race', ...)` |
| 势力 | 势力分布、权力结构、竞争关系 | `world_upsert(category='faction', ...)` |
| 地理 | 地图结构、关键地点、灵能特征 | `world_upsert(category='geography', ...)` |
| 能力 | 力量体系、等级划分、修炼路径 | `world_upsert(category='ability', ...)` |
| 经济 | 货币体系、贸易网络、资源分布 | `world_upsert(category='economy', ...)` |
| 日常 | 民生文化、风俗习惯、饮食服饰 | `world_upsert(category='daily_life', ...)` |
| 历史 | 重大历史事件、纪年体系、传说 | `world_upsert(category='history', ...)` |
| 物品 | 关键物品、灵器/丹药/符箓体系 | `world_upsert(category='item', ...)` |

**每个维度的展开流程**（引导模式，默认）：

1. **双锚点**：确定"危机锚"（这个世界面临的最大威胁）和"变量锚"（主角改变的变量）
2. **核心稀缺资源**：找出最稀缺的资源，让获取它需要付出不可逆的代价
3. **刑具化**：将稀缺资源转化为故事引擎——获取/失去/争夺的过程即为主线推动力
4. **涟漪效应**：每个设定变更必须推演至少3层连锁反应（直接影响→间接影响→远期影响）
5. **逐维度填充**：从锚点出发，按8维度逐一展开

**快速模式**（用户明确说"快速建世界观"时）：
- 基于品类模板一次生成8维度（参考 `novel-framework` skill 中的品类节奏模板）
- 快速模式仍需执行交叉验证，不可跳过

### Step 3: 逐维度确认

每维度完成 → `world_upsert` → 🔒 向用户展示该维度概要，确认后才进入下一维度。

### Step 4: 🔒 交叉验证（5项）

全部维度完成后执行：

| # | 验证项 | 标准 | 不通过处理 |
|---|--------|------|-----------|
| 1 | 锚点稳固 | 更换任一锚点后主线是否仍成立 | 重新加固锚点因果链 |
| 2 | 稀缺真实 | 稀缺资源有明确来源/流通/争夺逻辑 | 补充稀缺资源的经济/社会基础 |
| 3 | 涟漪完整 | 核心变更推演≥3层连锁反应 | 补推未覆盖的连锁反应 |
| 4 | 价值一致 | 世界观规则与核心主题一致 | 移除或改写矛盾设定 |
| 5 | 术语合规 | 无现代科技术语残留（遵守 lorecraft） | 走 lorecraft 四步法替换 |

### Step 5: 存档

- 全部验证通过 → `novel_update(status="ready")` + `git commit -m "A2: 世界观建模完成"`
- 🔒 术语规范：所有世界观术语遵守 lorecraft/SKILL.md，新术语走四步法

### 加载引用

- `skill_loader("novel-setup", "engine", "worldbuilding")` — 世界构建方法论
- `skill_loader("novel-setup", "engine", "causality")` — 因果逻辑法（涟漪效应推演）
- `skill_loader("novel-setup", "engine", "item")` — 物品全生命周期模板

---

## 物品档案（触发：加物品/新物品首次出现）

1. `world_query(name='{物品名}')` 确认不重复
2. `skill_loader("novel-setup", "engine", "item")` 加载物品生命周期模板
3. 按模板填写完整档案（12维度：生成方式/外观/感官特征/功能功效/使用方式/副作用/等级变化/稀有度/剧情绑定/生命周期/状态追踪/变化过程）
4. `world_upsert(category='item', name='{物品名}', data={完整档案})`
5. 🔒 确认档案完整性（12维度全部填写，不可留空）

---

## 断点续传

`memory_search(query="flow-state", tags=["project:{NOVEL_NAME}", "flow-state"])`

---

## 边界条件

| 场景 | 处理 |
|------|------|
| 项目名重复 | novel_create 失败 → 提示覆盖/新建 |
| world_upsert 失败 | 检查参数完整性，重试1次仍失败则提示用户手动检查 |
| 新维度与已有维度矛盾 | 暂停展开，展示矛盾点 → 用户选择保留哪个 |
| 用户中断头脑风暴 | 保存当前 progress 到 memory → 下次从断点恢复 |
| 8维度不完整就跳到正文 | 阻断：至少完成种族+能力+势力3个核心维度才能进入 B1 |
| lorecraft 术语冲突 | 按 lorecraft 四步法重新生成，不走简单替换 |
| 快速模式用户要求微调 | 允许逐维度修改，修改后重新跑交叉验证 |

</supporting-info>
