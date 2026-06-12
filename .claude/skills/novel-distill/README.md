# novel-distill

把已出版小说蒸馏成可检索、可适配、可组合的 borrowable 数据库，供写作时按需调用。

## Trigger

蒸馏XX / 分析小说 / 拆解小说 / 蒸馏参考 / 导入蒸馏 / 深化蒸馏

## Quick Start

```text
蒸馏 将夜                              # 全维度蒸馏
蒸馏 诡秘之主 — 仅叙事+人物             # 定向蒸馏
深化 将夜 narrative                    # 递进深化某维度
导入 distill/xxx.json                  # 已有数据导入
```

## Workflow

```
Phase 0  输入确认 + 项目方向检测
Phase 1  粗提取 + 作品画像
Phase 1.5 已有数据导入
Phase 2  精准蒸馏（6维度并行 agent）
  ├─ 2b.4 normalize（schema 修复 + trigger_signals/quality 自动填充）
  ├─ 2b.5 validate（schema + V1V2V3 内容质量）
  ├─ 2b.6 V1V2V3 失败分流 → rejected/
  └─ 2b.7 文件验证
Phase 2.5 递进深化（扫描 rejected/ 重新评估）
Phase 2c borrowable 存储
Phase 3  报告 + Zettelkasten INDEX.md
Phase 3.5 检索精度回归（可选）
```

## Directory Structure

```
novel-distill/
├── SKILL.md                       # 核心流程指令
├── README.md                      # 本文件
├── agents/
│   ├── claude-code.yaml           # 子agent 编排配置（v6.0）
│   ├── dim-world.md               # 维度 prompt 模块
│   ├── dim-ability.md
│   ├── dim-characters.md
│   ├── dim-narrative.md
│   ├── dim-rhythm.md
│   └── dim-highlight.md
├── references/
│   ├── agent-prompt.md            # 子agent prompt 模板 + V1V2V3 自检 + schema
│   ├── type-detection.md          # 类型识别 + 维度优先级
│   └── index-template.md          # Zettelkasten INDEX.md 模板（v6.0）
├── scripts/
│   ├── normalize-distill.py       # L1 规范化
│   ├── validate-distill.py        # L2 校验 + V1V2V3
│   └── retrieval-test.py          # L3 检索精度回归（v6.0）
└── evals/
    ├── quality-gate.md            # V1V2V3 rubric（v6.0）
    └── retrieval-cases.json       # 诱饵测试集（v6.0）
```

## Related Skills

- `novel-setup` — 借鉴 world 维度方法论
- `abilitycraft` — 借鉴 ability 维度方法论
- `novel-character` — 借鉴 characters 维度方法论
- `story-architecture` — 借鉴 narrative 维度方法论
- `novel-plan` — 借鉴 rhythm 维度方法论
- `novel-write` — borrowable 的主要消费方

## Version

v6.0.0 — 借鉴 cangjie-skill 引入 V1V2V3 质量门 + rejected 审计 + trigger_signals + 检索精度回归 + Zettelkasten 关系图。
