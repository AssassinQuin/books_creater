# DB 保存协议

## 适用场景
任何 skill 在完成创作/审查后，需要将结构化数据同步到 DB 时使用。

## 核心原则
- 每个 MCP 调用后必须检查返回值
- 失败即中止，不执行 git commit
- DB 是权威源，文件是人可读副本

## 执行步骤

1. 执行 MCP 写入操作（按实体类型分批）
2. 每个调用检查返回值
3. 收集所有错误
4. 有错误 → 中止，无错误 → sync(action="db_to_files") + git commit

## 通用保存模板

```python
errors = []

def check_result(op_name, result):
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"{op_name} 失败: {result}")

# 1. 卷级数据
result = volume_update(novel_name="NOVEL_NAME", number=N, ...)
check_result("volume_save", result)

# 2. 章节数据
for chapter in chapters:
    result = chapter_plan(novel_name="NOVEL_NAME", ...)
    check_result(f"chapter_plan Ch{chapter.number}", result)

# 3. 伏笔
for f in foreshadows:
    result = foreshadow(action="plant", novel_name="NOVEL_NAME", ...)
    check_result("foreshadow(action="plant")", result)

# 4. 世界观
for item in world_items:
    result = world(action="upsert", novel_name="NOVEL_NAME", ...)
    check_result(f"world(action="upsert")-{item.name}", result)

# 5. 角色
for char in characters:
    result = character_create(novel_name="NOVEL_NAME", ...)
    check_result(f"character_create-{char.name}", result)

# 6. 关系
for rel in relations:
    result = relation_create_by_name(novel_name="NOVEL_NAME", ...)
    check_result(f"relation(action="create")-{rel.from_name}", result)

# 🔒 结果校验
if errors:
    print(f"⚠️ DB保存失败（{len(errors)}个错误）：")
    for e in errors:
        print(f"  - {e}")
    print("文件已写入但DB未完全同步。请修复后重试，不执行 git commit。")
    return
else:
    print(f"✅ 全部 DB 操作成功")
    sync(action="db_to_files", novel_name="NOVEL_NAME")
```

## 失败处理

| 场景 | 处理 |
|------|------|
| 单个 MCP 调用失败 | 记录错误，继续其余调用，最后汇总 |
| 批量失败（>50%） | 中止，提示检查 DB 连接 |
| sync(action="db_to_files") 失败 | DB 数据已保存，文件同步可手动重试 |
| git commit 失败 | DB 已同步，手动 commit 即可 |
