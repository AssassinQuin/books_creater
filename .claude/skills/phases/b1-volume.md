# B1 卷规划阶段指令

> 本文件只包含卷规划阶段的执行指令。
> 需要时加载：engines/environment.md, engines/causality.md, engines/anti-ai.md

## 输入

- 卷号 + 卷主题（用户提供）
- 状态总线.setting（世界观+人物库）
- 状态总线.event（已有卷规划）

## 执行步骤

### Step 1: 环境先行

加载 `engines/environment.md` → 识别 2-5 个场景 → 设计环境5要素。

### Step 2: 事件架构

加载 `engines/causality.md` → 设计因果链 → 判断是否需要超级事件 → 设计支线（三检验）。

### Step 3: 章节设计

将事件映射到章节 → 每章 ≥6 条微事件 → 分配伏笔。

### Step 4: 验证

加载 `engines/outline-review.md` → 执行10项检查 → P0必须修复。

## 输出

- 状态总线.event.volumes[{卷号}] 更新
- 文件: `novels/{小说名}/设定/章节大纲/V{卷号}-事件大纲.md`
