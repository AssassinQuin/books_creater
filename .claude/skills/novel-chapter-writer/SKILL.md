---
name: novel-chapter-writer
description: 逐章写作引擎 — 跨大纲全量加载、角色蒸馏让人物活过来、设定冲突检测整改、3k+字数强制、角色状态增量更新。触发词：写第N章/继续写/写一章。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_get, mcp__novel-db__chapter_list, mcp__novel-db__chapter_update, mcp__novel-db__writing_start, mcp__novel-db__writing_finish, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_recall, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_list, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__timeline_query, mcp__novel-db__volume_get, mcp__novel-db__health_check, mcp__novel-db__dimension_query
---

# 逐章写作引擎

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`（含流程纪律）

---

## 强制流程

```
Step 1 注入全量上下文 → Step 2 写正文 → Step 3 🔒状态同步 → Step 4 存盘
```

**Step 3 是不可跳过的强制步骤。** 即使写完正文后用户说了别的话，必须先完成 `writing_finish` 再回应。未完成 Step 3 视为流程中断，下次触发时检测并提醒。

---

## Step 1: 注入全量上下文

```
writing_start(novel_id, chapter_number)
→ 基础信息（前3章摘要+活跃人物+未回收伏笔）
```

**跨大纲全量加载（强制）：**

```
1. world_query(category="faction") → 势力范围、当前势力关系
2. world_query(category="location") → 区域设定、本章涉及地点详情
3. world_query(category="ability") | world_query(category="economy") → 物品/资源体系
4. character_get(character_id) → 章节涉及人物最新状态(status含position/inventory/mental_state)
5. relation_list() → 人物关系网，判断对话立场/冲突来源
6. timeline_query(from_chapter=1, to_chapter=当前章) → 全卷时间线，避免矛盾
7. volume_get(volume_id) → 当前卷完整规划，理解本章在卷中位置
```

---

## Step 2: 写正文

### 2.0 前置检查（强制）

```
读 设定/写作执行规范.md
```

**强制遵守：**
- 最低字数：3000字（不含标点）
- 目标字数：3500-4500字
- 内容依据：本章大纲为纲，世界观/人物状态为准
- 检查清单：逐项勾选，写后逐项确认

### 2.1 角色分析指导（让人物活过来）

**目标**：基于novel-character技能的完整人物档案，使用角色蒸馏法分析当前剧情人物，推理反应/行为、话语，指导写作。

**执行流程：**

```
1. character_get(character_id) × N → 获取所有涉及人物的完整档案
2. 角色蒸馏分析（7步）：
   a. 萃取：从档案中提取外貌、身份、关键行为
   b. 深度：Ghost→Lie因果链 + Want/Need矛盾 + 弧线类型判定
   c. 洋葱三层：社交面具 + 自我认知 + 真实内核
   d. 矛盾注入：主气质 × 矛盾特质 = 化学反应
3. 剧情推理：
   a. 当前处境：人物在哪？什么环境？谁在场？
   b. 压力源：Ghost（创伤）？Lie（谎言）？Want（欲望）？Need（需求）？
   c. 冲突分析：与谁对立？谁是盟友？谁是敌对？
   d. 关系网络：与其他人物的关系强度
4. 行为指导生成：
   a. 说话风格：紧张/放松/愤怒时的用词、句式节奏
   b. 行动倾向：主动/被动/犹豫/果断
   c. 对话立场：对每个角色的具体态度
   d. 情绪反应：遇到冲突时的真实反应（不"震惊""难以置信"）
```

**输出：写作指导卡片**

```
[人物分析指导 - 第{章节号}章]

涉及人物：
| 姓名 | 当前处境 | 压力源 | 冲突对象 | 说话风格 | 行动倾向 | 对话立场 |
|------|----------|---------|----------|----------|----------|
| {A} | {描述} | {Ghost/Lie/Want/Need} | {人物名} | {具体描述} | {具体描述} | {具体描述} |

[场景级指导]
- {人物A}遇到{场景}时：会{具体反应}，说话{风格}，动作{具体}
- {人物B}与{人物A}互动：考虑{关系}，对话体现{立场}
```

**写作时参考此卡片，确保人物反应符合档案设定。**

### 2.2 设定冲突检测与整改

写作过程中持续检查，发现冲突立即处理：

**检测维度：**
| 冲突类型 | 检测方法 |
|-----------|---------|
| 世界观冲突 | 是否与world_query返回的设定矛盾？ |
| 人物冲突 | 是否与character_get返回的status/背景矛盾？ |
| 时间线冲突 | 是否与timeline_query返回的历史事件矛盾？ |
| 大纲冲突 | 是否偏离writing_start返回的outline逻辑？ |
| 前文冲突 | 是否与前3章摘要中的关键事实矛盾？ |

**整改流程（用户确认）：**
1. 暂停写作，明确列出冲突点
2. 展示选项给用户：
   - 选项1：整改设定（调用world_upsert/character_update）
   - 选项2：整改大纲（更新outline）
   - 选项3：重构正文（重写当前段落）
3. ⚠️ **等待用户确认**，收到选择后执行修复
4. 修复后继续写作

### 2.3 写作执行

读 `.claude/skills/novel-writer/references/writing-style.md` + `anti-ai-patterns.md`

#### 场景类型策略

| emotion_type | 核心策略 | 占比 | 具体写法 |
|-----------|---------|------|----------|
| dialogue | 潜台词+废话+抢话 | 对话≥60% | 「那个...你说呢」+打断+省略号，少用"他说""她问" |
| action | 短句密集+动词驱动 | 动作≥50%，对话≤20% | 「剑气一闪""他冲出去""手掌按住地面"——动词主语 |
| atmosphere | 五感铺陈+环境暗示情绪 | 环境≥40%，内心≥30% | 视觉+听觉+触觉：天空灰得像脏布；风声里夹着哀嚎；指尖触到冷的铁栏杆 |
| psychology | 情绪分层+回忆碎片 | 内心独白≥40% | 三层：当前感受+过去联想+本能反应，用「」区分 |
| daily | 闲聊带设定+毛边细节 | 闲聊+侧面≥60% | 「这批灵石是北境运来的吧？""那倒是...」 |
| montage | 多片段快切+强画面 | 100-300字/片段 | 用「---」「///」分隔 |

如果 `emotion_type` 未指定，根据大纲关键词判断。同一章场景类型≤2种。

#### 多线交织策略

**主线判断：**
1. 查volume_get返回的main_plotlines → 本章属于哪条线节点
2. 对比timeline_query → 本章在时间线位置

**伏笔操作：**
1. 查foreshadow_list → 计划回收的伏笔？
2. 暗线埋设：非暗线章节用日常不经意带过
3. 伏笔回收：暗线章节在高潮前3-5章回收

**配角控制：**
1. 检查哪些配角最近5章没出场
2. 避免堆砌：同章配角≤3人，每人出场≥200字

**场景切换：**
1. 同一场景切换≤2次
2. 用动作/环境过渡，不用"与此同时""另一边"等显式连接

**暗线埋设示例：**
「李三点了根烟，烟灰飘向窗外...」（不经意带过北境灵石涨价）

#### 去AI味要点

| 避免 | 示例 |
|------|------|
| 均匀句式 | 「他看着她，她看着你。」「剑光闪过，剑气炸开。」 |
| "然而""于是""随后"堆砌 | 手一松，剑落地。他冲了出去。 |
| 完美逻辑对话 | 「那个...你说呢？」「啊...我...」+打断+省略号 |
| 过度规整 | 桌角翘一块皮，桌面有茶渍，窗户缝塞着传单 |
| 情绪词堆砌 | 指尖在抖。他的瞳孔放大。 |

#### 节奏控制

**字数约束（强制）：**
- 最低3000字，目标3500-4500字
- 检测：如<3000字，必须扩展而非拖沓

**节奏分布：**
- 开头10%承接铺垫 → 发展40%核心推进 → 高潮30%最紧张 → 收尾20%钩子悬念

**防拖沓原则（不要特异凑字数）：**
| 禁止 | 替代 |
|------|------|
| "于是""随后""接着"过渡 | 动作接动作，不写连接词 |
| 无意义长心理描写 | 用具体行为展示情绪 |
| 重复相同动作 | 合并或一次概括 |
| 环境描写填充 | 用环境暗示情绪，不单独堆砌 |
| 章节末无推进 | 每段至少一个推进点 |

**爽点密度：**每3-5章一个（打脸/逆袭/获得/展示/复仇）

---

## Step 3: 🔒写后状态更新（不可跳过）

> **正文写完后立即执行，不管用户接下来说什么。**

### 3.1 角色档案增量更新

```
for each character in characters_involved:
  character_update(character_id,
    status={
      position: "人在哪？",
      inventory: ["手中有什么物？"],
      mental_state: "当前情绪/认知/压力？",
      recent_events: ["本章发生的关键事件"]
    })
```

**更新原则：**
- 只更新本章确实变化的状态字段
- 保留未变化字段为空（不覆盖）
- recent_events用增量方式（追加而非替换）

### 3.2 完整状态同步

```
writing_finish(chapter_id, summary="章节概要",
  key_events=["事件1","事件2"],
  characters_involved=[人物id列表],
  new_foreshadows=[{description:"伏笔描述",importance:"medium"}],
  resolved_foreshadows=[伏笔id列表],
  ability_level="金丹中期", location="潜龙城",
  timeline_events=[{event_time:"午后", event_order:1, event_description:"XXX"}])
```

一步完成：摘要 + 状态 + 伏笔 + 维度 + 时间线 + **角色增量更新**。

完成后向用户确认：`"✓ 第{N}章状态已更新（摘要/伏笔/时间线/维度/角色状态）"`

**然后**才能进入对话、修改、或下一章。

---

## Step 4: 存盘

`novels/{小说名}/正文/第{NNN}章-{标题}.md` → `git commit -m "ch{N}: {标题}"`

---

## 流程中断恢复

触发时检查：是否有上一章写完但未执行 `writing_finish`？

```
chapter_list → 最近一章状态是否为written？
```

如果是drafting → 提醒"上次第{N}章写完了但状态没更新，先补writing_finish？"

---

## 每10章：健康快检

```
foreshadow_list(status="planted") → 未回收伏笔
character_list → 长期未出场配角
dimension_query(dimension="ability") → 升级节奏
```

发现问题 → **暂停提醒用户**，建议调用 `/novel-doctor` 深入诊断。
