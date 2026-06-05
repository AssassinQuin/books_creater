# 检查点显示模板 + 新实体注册 + 声音适配规则

> novel-planner-volume 的检查点展示格式、新实体注册规范与声音适配详细规则。

## 检查点A显示模板

编排器展示：

```
【V{N}《{卷名}》事件架构】

情感曲线: {起点} → {转折} → {终点}

起承转合:
  起(Ch?): {概要}
  承(Ch?): {概要}
  转(Ch?): {概要}
  合(Ch?): {概要} → 下卷钩子: {类型}

因果链: {事件1} → {事件2} → ... → {终点}

人物弧光:
  {角色A}: {起点状态} → {触发事件} → {终点状态}
  {角色B}: 不变（理由：{ }）

悬念: 回答了[?] / 新提出[?]

螺旋结构:
  信息矩阵: L1[?] L2[?] L3[?] ✅/❌
  翻新型揭示: {模式} {翻新事件} ✅/❌
  回旋镖: ≥3个 ✅/❌

情节密度:
  并行活跃链: {N}条 (需≥3) ✅/❌
  NPC议程: {已追踪NPC数} ✅/❌
  复杂化: 每章≥1次 ✅/❌

🔒术语自检: 术语有文化根脉 ✅/❌

确认后进入章节设计。输入"OK"或修改意见。
```

## 检查点A2显示模板

编排器展示 Agent 2 输出的逐章大纲：

```
【V{N}《{卷名}》逐章大纲】（共{N}章）

Ch{1}: {标题} | {场景数}个场景 | {核心事件}
  - 场景类型: {对话/动作/氛围/心理/日常/混合} | 声音层: {类型}
  - 伏笔: {埋设/深化/回收}{N}条 | 费笔: {N}个
Ch{2}: ...
...
Ch{末}: {标题} | {场景数}个场景 | {章末钩子}
  - 下卷接口: {如何衔接V{N+1}}

【硬约束自检】
- 事件密度: ≥4/章 ✅/❌
- 费笔配额: ≥总章数×1.0 ✅/❌
- 罕见组合: ≥1个/卷 ✅/❌
- 伏笔场景化: 全部有具体场景 ✅/❌
- 主角在场: 占全卷章节数的一半以上 ✅/❌
- 事件弧节奏: 高潮事件多章展开，日常压缩，无按天填充 ✅/❌
- 🔒术语规范: 无需替换术语 ✅/❌
- 🔒螺旋结构: 信息钩子Lv2/Lv3≥60% ✅/❌ | 回旋锚已标注 ✅/❌
- 🔒情节密度: 每章≥2条链推进 ✅/❌ | 每章≥1次复杂化 ✅/❌

输入"OK"进入验证，或提修改意见（可指定某章修改）。
```

## 新实体注册

事件架构引入新实体时：**列出所有新实体** → 查重(world(action="query")+设定文件) → 术语验证 → 暂停等用户确认("OK") → 保存到文件+DB。

新实体需要经过查重、术语验证和用户确认才能确保世界观一致性。Agent 静默创建可能导致命名冲突、术语不一致或重复定义。

### 新实体类型与保存位置

| 新实体类型 | 保存文件 | DB操作 |
|-----------|---------|--------|
| 新地点 | 设定/地图.md | world(action="upsert", category='location') |
| 新物品 | 设定/物品.md | world(action="upsert", category='item') |
| 新NPC | 设定/角色总览.md | character_create() |
| 新能力/概念 | 设定/世界观.md | world(action="upsert", category='ability') |
| 新势力/组织 | 设定/世界观.md | world(action="upsert", category='faction') |

### 注册规范（参考 world-element-registry.md）

- 每个新实体必须包含：名称/类型/描述/关联元素/首次出现章节
- 新物品需定义：外观/功能/获取方式/限制条件
- 新地点需定义：位置/环境特征/势力归属/危险等级
- 新NPC需定义：身份/性格/动机/与现有角色的关系

## 声音适配规则

### 大纲侧（章节设计师）

编排器 Read(author-voice-{variant}.md, limit=5) 提取头部摘要，编译速查表注入 Agent 2。不加载全量 author-voice 引擎。

提取逻辑：
```python
voice_layer_headers = {}
files = {
    "battle":  ".claude/skills/engines/author-voice-battle.md",
    "emotion": ".claude/skills/engines/author-voice-emotion.md",
    "daily":   ".claude/skills/engines/author-voice-daily.md",
    "mystery": ".claude/skills/engines/author-voice-mystery.md",
}
for variant, path in files.items():
    lines = Read(path, limit=5)
    voice_layer_headers[variant] = lines
```

读取量仅 ~25 行（5文件×前5行），约 1.5 KB，替代 17.5 KB 全量加载。引擎源文件是唯一权威源，无需独立维护查表文件。

### 正文侧（novel-chapter-writer）

正文写作阶段按章内标注的声音层标签，加载对应的全量 author-voice 引擎文件：
- `engines/author-voice-emotion.md` — 情感场景的感性与克制平衡
- `engines/author-voice-daily.md` — 日常场景的松弛与真实感
- `engines/author-voice-battle.md` — 战斗场景的节奏与压迫感
- `engines/author-voice-mystery.md` — 悬疑场景的克制与信息释放
- `engines/author-voice.md` 项目层：`设定/作者声音.md`

Agent 2 为每章标记声音层，写入大纲供正文写作时加载。
