# P0修复循环详解

## 问题分级

| 级别 | 判定标准 | 处理要求 |
|------|---------|---------|
| P0 | 因果链断裂/三视角冲突/角色OOC | **必须修复**，阻断保存 |
| P1 | 节奏断层/伏笔遗漏 | **本轮验证结束前**完成修复 |
| P2 | 微调建议 | **下一轮迭代**开始前完成 |

## 交叉检查

- [ ] 读者vs作者无冲突（结构服务读者体验）
- [ ] 读者vs人物无冲突（人物选择优先，但有动机）
- [ ] 作者vs人物无冲突（人物逻辑>结构需求）

**核心原则**：人物 > 读者 > 作者

## 修复循环

```python
MAX_FIX_ROUNDS = 3
fix_rounds = 0

while p0_issues_exist:
    fix_rounds += 1
    if fix_rounds > MAX_FIX_ROUNDS:
        # 升级为用户决策
        user_choice = await user_input()
        if user_choice == "①接受": break       # 标记已知风险
        elif user_choice == "②回退": rollback_to_pre_fix_state(); return
        elif user_choice == "③手动修复": return  # 暂停等待手动修复
    fix_p0_issues(p0_issues)
    validation_result = run_step5_validation()
    p0_issues = validation_result.p0_issues
```

## 修复流程说明

1. 发现P0 → 回到对应Step修复
2. 修复后重跑 Step 5 验证
3. 最多3轮修复循环
4. 超出3轮 → 升级为用户决策（①接受风险 / ②回退到修复前 / ③暂停手动修复）
5. 无P0 → 进入 Step 6 保存
