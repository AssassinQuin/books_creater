# 卷级大纲模板

> 权威源：文件 `设定/大纲/V{N}-{卷名}.md`。DB `volumes` 表存摘要。

## DB 字段映射

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| number | number | INT | ✅ | 卷号 |
| title | title | TEXT | ✅ | 卷名 |
| main_plotlines | main_plotlines | JSON | ✅ | 主线脉络数组 |
| notes | notes | TEXT | 可选 | 卷级备注 |

## 文件格式（`设定/大纲/V{N}-{卷名}.md`）

```markdown
# V{N} {卷名}

## 卷级信息
- **number**: {卷号}
- **title**: {卷名}
- **main_plotlines**: {JSON数组}

## 卷级环境先行设计
{本卷主要场景的感官基线/灵能状态/势力格局}

## 明线
{主角推进的主线剧情}

## 暗线
{隐藏真相/暗线递进}

## 逐章大纲
### Ch{NNN} {章节标题}
- **chapter_type**: normal/transition/climax/filler/daily
- **outline**: 章节大纲
- **volume_id**: {卷ID}

## 伏笔操作
### 埋设
- {伏笔描述}

### 回收
- {伏笔描述}

## 互动矩阵
{角色互动设计}

## 角色状态变化
{本卷角色状态变化汇总}
```

---

## 扩展机制

新增维度时：
1. 在文件格式中追加新节
2. 如需 DB 支持，在 `volumes` 表新增列
3. 在 `volume_update` MCP 工具中新增对应参数
