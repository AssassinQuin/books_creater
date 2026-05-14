---
name: novel-framework
description: "百万字级网文小说框架设计系统。提供9大专业Agent模块协同工作，覆盖世界观、时空观、人物、关系、能力体系、物品系统、故事架构、线索管理、逻辑校验全链路。当用户需要设计小说框架、创建世界观、构建人物体系、规划故事大纲、设定修炼/能力体系、管理伏笔线索、检查逻辑一致性时，务必使用此Skill。即使只是提到'写小说'、'网文设定'、'小说大纲'、'修炼体系'、'世界观设计'、'人物设计'、'小说设定集'等关键词，也应触发此Skill。适用于玄幻/仙侠/都市/科幻/奇幻/历史/悬疑等所有网文类型。"
---

# 百万字网文框架设计系统 (Novel Framework)

## 概述

本Skill为百万字级长篇网文提供系统化框架设计能力。通过9个专业Agent模块的协同工作，确保超长篇幅中的逻辑自洽、人物一致、节奏紧凑。每个Agent模块均可独立调用，也可按标准流程串联使用。

## 核心架构：三层 + 校验

```
基础层 ─┬─ World-Builder (世界观构建)
        └─ Chrono-Architect (时空观设计)

角色层 ─┬─ Character-Forge (人物设计)
        ├─ Relation-Weaver (关系网络)
        ├─ Power-System (能力体系)
        └─ Artifact-Smith (物品系统)

叙事层 ─┬─ Story-Architect (故事架构)
        └─ Thread-Keeper (线索管理)

校验层 ── Logic-Guardian (逻辑校验)
```

## 工作流决策树

```
用户请求
├─ "从零开始" / "新建小说项目"
│  └─ → 完整四阶段流水线（阶段一→四）
│
├─ 只需世界观/设定？
│  └─ → World-Builder + Chrono-Architect
│
├─ 只需人物/角色？
│  └─ → Character-Forge + Relation-Weaver
│
├─ 只需能力/修炼体系？
│  └─ → Power-System + Artifact-Smith
│
├─ 只需故事/大纲？
│  └─ → Story-Architect + Thread-Keeper
│
├─ 检查逻辑/一致性？
│  └─ → Logic-Guardian
│
├─ 修改/更新已有设定？
│  └─ → 读取现有文件 → 识别需更新的模块 → 局部执行
│
└─ 不确定需要什么？
   └─ → 先读取现有项目文件，评估当前状态，给出建议
```

## 阶段一：基础层构建

### 执行顺序
1. **World-Builder** → 2. **Chrono-Architect**

### World-Builder（世界观构建Agent）

读取 `references/world-building.md` 获取完整指南。

**输入要求**：题材类型、目标读者、期望基调、核心创意
**输出产物**：`world-building.md`（世界观设定文档）

**核心工作清单**：
- 宏观：宇宙/大陆/国家/势力分布
- 中观：城市/组织/门派/家族结构
- 微观：社会阶层/经济体系/文化习俗
- 独特元素：种族/魔法/科技/宗教信仰
- 扩展预留：未探索区域、未揭示的历史

### Chrono-Architect（时空观设计Agent）

读取 `references/chrono-architect.md` 获取完整指南。

**输入要求**：世界观基础文档
**输出产物**：`chrono-system.md`（时空设定文档）

**核心工作清单**：
- 纪元划分与历史时间线
- 当前故事所处的时间锚点
- 空间规则（地理/维度/位面/传送）
- 时间规则（时间流逝/时空异常/回溯机制）
- 历史大事件编年表

## 阶段二：角色层构建

### 执行顺序
3. **Character-Forge** → 4. **Relation-Weaver** → 5. **Power-System** → 6. **Artifact-Smith**

### Character-Forge（人物设计Agent）

读取 `references/character-forge.md` 获取完整指南。

**输入要求**：世界观文档、故事定位、角色功能需求
**输出产物**：`characters/[角色名].md`（每个角色独立档案）

**核心工作清单**：
- 基础信息：姓名/年龄/性别/外貌/身份
- 性格画像：核心特质/优点/缺点/说话风格
- 背景故事：身世/成长经历/转折事件
- 动机体系：表层目标/深层需求/内心矛盾
- 人物弧光：起始状态→转变→终态
- 百万字成长规划：阶段性变化节点

### Relation-Weaver（关系网络Agent）

读取 `references/relation-weaver.md` 获取完整指南。

**输入要求**：全部人物档案、世界观社会结构
**输出产物**：`relation-network.md`（关系网络文档）

**核心工作清单**：
- 关系类型：师徒/敌对/暗恋/利用/盟友/竞争
- 关系强度与变化轨迹
- 三角关系与多方博弈
- 关系对剧情的推动作用
- 分阶段变化规划

### Power-System（能力体系Agent）

读取 `references/power-system.md` 获取完整指南。

**输入要求**：世界观、时空规则、人物定位
**输出产物**：`power-system.md`（能力体系文档）

**核心工作清单**：
- 等级体系：段位划分/晋升条件/战力对标
- 数学建模：指数增长/线性增长/阶段跃迁
- 获取规则：天赋/修炼/机缘/传承
- 战斗逻辑：克制关系/组合技/消耗与恢复
- 天花板设计：上限突破机制

### Artifact-Smith（物品系统Agent）

读取 `references/artifact-smith.md` 获取完整指南。

**输入要求**：能力体系、世界观资源设定
**输出产物**：`artifacts.md`（物品系统文档）

**核心工作清单**：
- 物品分类：武器/防具/丹药/法器/材料
- 属性设计：品级/效果/副作用/稀有度
- 获取途径：掉落/锻造/拍卖/任务/机缘
- 进化体系：升级路线/材料需求/突破条件
- 关键物品与剧情绑定

## 阶段三：叙事层构建

### 执行顺序
7. **Story-Architect** → 8. **Thread-Keeper**

### Story-Architect（故事架构Agent）

读取 `references/story-architect.md` 获取完整指南。

**输入要求**：世界观、人物、能力体系、目标字数
**输出产物**：`story-outline.md`（故事大纲文档）

**核心工作清单**：
- 分卷规划：每卷核心冲突/字数分配
- 章节节奏表：高潮/低谷/过渡/伏笔密度
- 主线/支线交织策略
- 三幕式放大版（起→承→转→合×N卷）
- 卷间过渡与衔接设计

### Thread-Keeper（线索管理Agent）

读取 `references/thread-keeper.md` 获取完整指南。

**输入要求**：故事大纲、人物秘密、世界观谜题
**输出产物**：`thread-tracker.md`（线索追踪文档）

**核心工作清单**：
- 长线线索：跨越多卷的核心悬念
- 短线线索：单卷内回收的伏笔
- 线索铺设时机与回收节点
- 线索之间的嵌套与交叉
- 读者期待管理策略

## 阶段四：校验层

### Logic-Guardian（逻辑校验Agent）

读取 `references/logic-guardian.md` 获取完整指南。

**输入要求**：所有模块的输出文档
**输出产物**：`logic-report.md`（校验报告）

**校验维度**：
- 时间线一致性：事件顺序、年龄推算、纪年对应
- 人物行为动机：是否符合性格设定、成长阶段
- 能力体系平衡：等级是否自洽、战斗逻辑是否合理
- 物品获取逻辑：获得途径是否合理、品级是否匹配
- 世界观内洽：设定之间是否有矛盾
- 线索闭环：所有伏笔是否有回收计划

## 项目目录结构

初始化新项目时，使用以下标准目录结构：

```
[小说名称]/
├── README.md                    # 项目概览（题材/字数目标/核心卖点）
├── world-building.md            # 世界观设定
├── chrono-system.md             # 时空观设定
├── power-system.md              # 能力/修炼体系
├── artifacts.md                 # 物品系统
├── relation-network.md          # 人物关系网络
├── story-outline.md             # 故事大纲
├── thread-tracker.md            # 线索追踪表
├── logic-report.md              # 逻辑校验报告
├── characters/                  # 人物档案目录
│   ├── [主角名].md
│   ├── [女主名].md
│   └── ...
├── volumes/                     # 分卷规划目录
│   ├── vol-01/
│   │   ├── outline.md           # 本卷大纲
│   │   └── chapters.md          # 章节细纲
│   └── ...
└── changelog.md                 # 设定变更记录
```

运行 `scripts/init_project.sh [小说名称]` 可自动创建此结构。

## 扩展策略速查

读取 `references/expansion-strategies.md` 获取百万字扩展完整策略。

**核心原则**：
- 世界观展幅：每卷展开一个新区域，保留30%未探索
- 角色池：每卷引入2-3个新重要角色，淘汰或边缘化部分旧角色
- 能力天花板：每隔50-80万字引入一次体系突破
- 节奏黄金比：高潮:过渡:伏笔 = 3:4:3
- 中期疲劳：在第60-80万字处安排重大转折事件

## 百万字字数分配参考

| 卷序 | 字数范围 | 核心任务 | 节奏 |
|------|---------|---------|------|
| 第一卷 | 0-15万 | 世界观建立 + 主角起步 | 快速展开 |
| 第二卷 | 15-30万 | 世界拓展 + 初遇强敌 | 稳步推进 |
| 第三卷 | 30-50万 | 深入探索 + 重大转折 | 加速升级 |
| 第四卷 | 50-70万 | 体系突破 + 多线交织 | 高潮迭起 |
| 第五卷 | 70-100万 | 终局铺垫 + 最终对决 | 蓄力爆发 |

## 使用方式

1. **全新项目**：提供题材/核心创意 → 自动按四阶段流水线执行
2. **单模块调用**：明确需要哪个Agent → 读取对应reference → 执行
3. **校验现有项目**：提供项目目录路径 → 读取所有设定文档 → 运行Logic-Guardian
4. **迭代优化**：提供修改需求 → 读取现有设定 → 局部更新 → 增量校验

## 资源索引

| 参考文件 | 用途 | 何时加载 |
|---------|------|---------|
| `references/world-building.md` | 世界观构建指南 | 阶段一/需要世界观设计时 |
| `references/chrono-architect.md` | 时空观设计指南 | 阶段一/需要时间线设计时 |
| `references/character-forge.md` | 人物设计指南 | 阶段二/需要创建角色时 |
| `references/relation-weaver.md` | 关系网络指南 | 阶段二/设计人物关系时 |
| `references/power-system.md` | 能力体系指南 | 阶段二/设计修炼/能力系统时 |
| `references/artifact-smith.md` | 物品系统指南 | 阶段二/设计物品装备时 |
| `references/story-architect.md` | 故事架构指南 | 阶段三/规划故事大纲时 |
| `references/thread-keeper.md` | 线索管理指南 | 阶段三/管理伏笔线索时 |
| `references/logic-guardian.md` | 逻辑校验指南 | 阶段四/校验一致性时 |
| `references/expansion-strategies.md` | 扩展策略指南 | 规划百万字时 |
| `templates/*.md` | 各类数据模板 | 创建新文档时 |
