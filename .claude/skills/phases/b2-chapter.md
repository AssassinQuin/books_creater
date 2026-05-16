# B2 章节写作阶段指令

> 本文件只包含章节写作阶段的执行指令。
> 需要时加载：engines/loading.md, engines/environment.md, engines/dialogue.md, engines/action.md, engines/item.md, engines/anti-ai.md

## 输入

- 章节号（用户提供）
- 状态总线.event（卷规划+事件架构）
- 状态总线.setting（人物档案+世界观）
- 状态总线.text（前3章摘要）

## 执行步骤

### Step 0: 断点检测

`chapter_list` 检查已有数据 → `get_chapter_context` 加载上下文。

### Step 1: 启动 Agent 1 (Context Curator)

加载 `engines/loading.md` → 清洗压缩原始数据 → 产出上下文包。

### Step 2: 启动 Agent 2 (Creative Director)

加载 `engines/environment.md` → 场景设计
加载 `engines/causality.md` → 因果链确认
加载 `engines/dialogue.md` → 对话设计（如需要）
加载 `engines/action.md` → 动作设计（如需要）
→ 产出创意蓝图。

### Step 3: 启动 Agent 3 (Engine Coordinator)

根据场面类型，按需加载：
- 对话场面 → `engines/dialogue.md`
- 动作场面 → `engines/action.md`
- 环境场面 → `engines/environment.md`
- 物品场面 → `engines/item.md`
→ 产出引擎指令包。

### Step 4: 启动 Agent 4 (Text Generator)

加载 `engines/anti-ai.md` → 反AI自检
→ 逐场面生成正文。

### Step 5: 校验存盘

`validate_chapter` → `writing_finish` → 写文件。

## 输出

- 状态总线.text.chapters[{章节号}] 更新
- 文件: `novels/{小说名}/正文/第{NNN}章-{标题}.md`
