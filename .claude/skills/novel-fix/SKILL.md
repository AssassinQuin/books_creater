---
name: novel-fix
description: 文本修复与润色。触发词：修复/润色/改文/去重
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash
version: "2.0.0"
---

# 文本修复与润色

## 触发
用户说"修复""润色""改文""去重"。

## 模式（问用户）
1. **修复** — 针对审阅报告中的 P0/P1 问题逐项修复
2. **润色** — 提升文笔质量（不改变情节）
3. **术语修复** — 批量替换违规术语

## 执行
1. 定位问题段落
2. 修复
3. `validate_chapter` 重新校验
4. 用户确认 → 更新文件 + DB

## 完成后
问用户：继续修复 / 写正文 / 其他。
