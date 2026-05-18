---
Task ID: 1
Agent: main
Task: 达尔文skill审计+修复+推送

Work Log:
- 拉取最新代码(git pull origin main --rebase)
- 定位12个SKILL.md文件(books_creater/.claude/skills/下)
- 启动达尔文审计Agent，使用8维度框架(Frontmatter/工作流清晰度/边界条件/检查点设计/指令具体性/资源整合度/整体架构/实测表现)评估全部12个skill
- 审计完成，生成分数排名：
  - novel-chapter-writer: 89/100 (A)
  - abilitycraft: 86/100 (A)
  - novel-writer: 85/100 (A)
  - novel-planner: 85/100 (A)
  - novel-planner-volume: 84/100 (B+)
  - novel-character: 81/100 (B+)
  - novel-reviser: 81/100 (B+)
  - novel-qa: 78/100 (B)
  - lorecraft: 76/100 (B)
  - novel-ability-designer: 75/100 (deprecated)
  - novel-skill-creator: 70/100 (C+)
  - novel-setup: 64/100 (D)
- 按优先级修复：P0×2 + P1×7 + P2×3 + 全量version/depends_on
- 11个文件修改，265行新增，95行删除
- 成功推送到GitHub

Stage Summary:
- 所有P0/P1问题已修复
- 全部10个active skill补齐version和depends_on
- novel-setup从65行大幅扩展到170行（得分预计从64→82）
- lorecraft补全4个缺失frontmatter字段+用户确认检查点
- novel-qa的C3/C4从压缩状态扩展为完整流程
- novel-character蒸馏7步扩展为带执行要点的详细指南
