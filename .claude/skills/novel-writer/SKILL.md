---
name: novel-writer
description: 百万字网文创作引擎总路由器。根据用户意图分发到对应子技能，处理上架/进度/素材查询。触发词：写小说/帮我写/上架/进度/加素材/规划/设计人物/写章/审阅/修复/卡文/头脑风暴
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*, mcp__memory__*
depends_on: novel-setup, novel-character, novel-planner, novel-planner-volume, novel-chapter-writer, novel-qa, novel-reviser, abilitycraft, lorecraft
lifecycle: core
---

# 百万字网文创作引擎

> 总路由器：识别用户意图 → 分发到对应子技能。不直接执行创作。

<what-to-do>

## Step 0: 上下文初始化

```
1. 读取项目配置：
   - 读取 novels/ 下目录名 → 确定当前项目列表
   - 如只有一个项目 → 自动设为 active_project
   - 如有多个项目 → 读取 CLAUDE.md 或询问用户选择
2. 将 active_project 赋值给 NOVEL_NAME（后续所有 DB 调用使用此变量）
3. 检查子技能可用性（快速检查 .claude/skills/ 下各目录是否存在 SKILL.md）
```

🔒 **阻断条件**：无任何项目目录时 → 提示用户先创建项目（触发 novel-setup A1）

## Step 1: 意图识别

### 1.1 精确匹配路由表

| 用户意图 | 触发词（精确） | 分发目标 | 子阶段 |
|---------|---------------|---------|--------|
| 头脑风暴/灵感 | "头脑风暴"/"灵感"/"创意" | novel-setup | A1 |
| 建世界观/设定 | "建世界观"/"世界观"/"设定"/"加物品" | novel-setup | A2 |
| 设计人物 | "设计人物"/"加人物"/"改人物"/"新建角色" | novel-character | A3 |
| 能力设计 | "能力设计"/"能力体系"/"觉醒设计"/"灵能设计" | abilitycraft | — |
| 全书大纲 | "规划全书"/"全书框架"/"卷级目标" | novel-planner | B1 |
| 卷级大纲 | "设计卷"/"卷大纲"/"章节规划"/"事件设计" | novel-planner-volume | B1 |
| 写章节 | "写第N章"/"继续写"/"写一章"/"下一章"/"续写" | novel-chapter-writer | B2 |
| 审阅 | "审阅大纲"/"大纲审查" | novel-qa | B3(大纲) |
| 审阅 | "审阅正文"/"审阅最近"/"检查正文" | novel-qa | B3(正文) |
| 诊断 | "诊断"/"卡文"/"为什么卡"/"写不动" | novel-qa | C2 |
| 设定审查 | "审设定"/"OOC"/"冲突检测" | novel-qa | C4 |
| 修复/润色 | "修复"/"去重"/"修文"/"润色"/"去AI味" | novel-reviser | — |
| 上架/发布 | "上架"/"发布" | C1流程（见Step 3） |
| 进度/状态 | "进度"/"状态"/"写到哪了" | 状态查询（见Step 4） |
| 加素材 | "加素材"/"记一下" | 素材入库（见Step 5） |

### 1.2 语义兜底（精确匹配失败时）

当用户输入不匹配任何精确触发词时，按以下规则进行语义推断：

| 用户输入特征 | 推断意图 | 分发目标 |
|------------|---------|---------|
| 提到具体章节号（"第X章"/"ChXX"） | 写章/改章 | novel-chapter-writer |
| 提到角色名+问题（"XX的XX不对"） | 修改人物 | novel-character |
| 提到具体卷号（"VX"/"第X卷"） | 卷级操作 | novel-planner-volume |
| 提到质量/问题/不满意 | 审阅诊断 | novel-qa |
| 短句（<10字）+疑问语气 | 不确定 → 引导选择 | 进入 Step 1.3 |
| 长段落描述创作需求 | 综合意图 | 拆解为多步骤 |

### 1.3 意图消歧对话

当无法判断用户意图时（精确匹配失败 + 语义兜底也无法确定）：

```
请选择你要进行的操作：
1. 🆕 创建/修改设定（世界观、人物、能力、物品）
2. 📋 规划大纲（全书框架、卷级章节规划）
3. ✍️ 写作（写新章节、续写）
4. 🔍 审阅/诊断（检查质量、OOC、卡文诊断）
5. 🔧 修订（修复问题、润色、去AI味）
6. 📊 查看进度
7. 📦 其他（请描述你的需求）
```

### 1.4 冲突消歧

多意图匹配时的优先级：C3（级联更新）> B2（章节写作）> B3（审阅）> B1（规划）> A（设定）

## Step 2: 路由执行

```
1. 确认目标子技能存在（SKILL.md 文件存在）
2. 将 NOVEL_NAME 和上下文信息传递给子技能
3. 通过 Agent/Task 启动子技能执行
4. 子技能完成后返回结果给用户
```

### 路由失败处理

| 失败场景 | 处理 |
|---------|------|
| 子技能 SKILL.md 不存在 | 提示："子技能 {name} 未安装，请检查 .claude/skills/" |
| 子技能执行报错 | 记录错误信息，提示用户重试或手动操作 |
| 用户意图模糊且消歧失败 | 回到 Step 1.3 引导选择 |
| DB 连接失败 | 提示："数据库连接失败，请检查 .mcp.json 配置" |

## Step 3: C1 上架流程

```
1. 确认目标平台（番茄/起点/纵横）
2. skill_loader("novel-writer", "engine", "platform") 加载平台规则
3. 检查合规性（违禁词/字数/章节结构）
4. 格式化输出
5. 🔒 发布前与用户确认，避免误操作导致内容提前公开
```

## Step 4: 状态查询

```
volume_list(novel_name=NOVEL_NAME) → 卷完成度
chapter_list(novel_name=NOVEL_NAME) → 章节状态统计
foreshadow_list(novel_name=NOVEL_NAME) → 伏笔回收率
health_check(novel_name=NOVEL_NAME) → 健康指标
```

输出格式：简洁表格 + 一句话总结（如"已完成 3/15 卷，当前卷进度 60%"）

## Step 5: 素材入库

```
memory_store(content, tags=["project:{NOVEL_NAME}", "material"])
```

素材需包含来源标注（用户口述/参考XX/灵感），不可无来源直接入库。

</what-to-do>

<supporting-info>

## 子技能速查

| Skill | 阶段 | 核心输出 | 状态 |
|-------|------|---------|------|
| novel-setup | A1/A2 | 项目创建+世界观 | ✅ 可用 |
| novel-character | A3 | 人物蒸馏+入库 | ✅ 可用 |
| abilitycraft | A3(能力) | 能力设计+命名 | ✅ 可用（替代已废弃的 novel-ability-designer） |
| lorecraft | 术语 | 命名词汇层 | ✅ 可用 |
| novel-planner | B1(全书) | 框架+脉络+卷级目标卡 | ✅ 可用 |
| novel-planner-volume | B1(卷级) | 逐章大纲+事件架构 | ✅ 可用 |
| novel-chapter-writer | B2 | 正文(Multi-Agent Pipeline) | ✅ 可用 |
| novel-qa | B3/C2/C3/C4 | 审阅+诊断+级联更新 | ✅ 可用 |
| novel-reviser | 修订 | 批量修复+润色 | ✅ 可用 |

## 当前项目

由 Step 0 动态检测，不再硬编码。默认查找 `novels/` 下的项目目录。

</supporting-info>
