# 阶段指令目录 (phases/)

> 每个阶段指令文件只包含该阶段的具体执行指令，不含通用方法论。
> 方法论在 `engines/` 中按需加载。

## 命名规则

`{workflow-phase}-{step}.md`

| 阶段 | 文件 | 说明 |
|------|------|------|
| A1 头脑风暴 | `a1-brainstorm.md` | 灵感收集→决策卡 |
| A2 世界观 | `a2-worldbuilding.md` | 6维度建模→交叉验证 |
| A3 人物 | `a3-character.md` | 蒸馏7步→外观→对话→关系 |
| B1 卷规划 | `b1-volume.md` | 环境先行→事件架构→章节设计→验证 |
| B2 章节写作 | `b2-chapter.md` | 4Agent流水线→正文→存盘 |
| B3 审阅 | `b3-review.md` | 大纲审计+正文审计 |
| C2 诊断 | `c2-diagnose.md` | 健康检查→破局策略 |
| C3 更新 | `c3-update.md` | 改设定→影响分析→级联同步 |

## 加载协议

```
skill_loader(skill="novel-planner", level="phase", resource="b1-volume")
→ 读取 phases/b1-volume.md
→ 注入当前 Agent 上下文
→ 执行完毕即丢弃
```

## 与 engines/ 的关系

```
phases/b1-volume.md          # "做什么"——阶段流程
  ├─ 需要环境设计 → 加载 engines/environment.md    # "怎么做"——方法论
  ├─ 需要因果链 → 加载 engines/causality.md
  ├─ 需要反AI检查 → 加载 engines/anti-ai.md
  └─ 需要示例 → 加载 examples/scene-templates.md
```
