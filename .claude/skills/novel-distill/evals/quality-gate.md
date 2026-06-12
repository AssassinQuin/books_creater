# V1V2V3 三重验证质量门

借鉴 cangjie-skill 的 Triple Verification。每条 borrowable 写入 DB 前必须通过三项。

## V1 — 跨域（cross_domain）

**问题**：该技法在原作**至少 2 个独立场景/章节**出现？

### 通过条件
- 独立 = 不同章节 + 不同对象 + 不同结论
- 同一案例换说法算 1 处（不是 2 处）

### 字段
```yaml
quality.v1_cross_domain:
  passed: true|false
  evidence:
    - "Ch3: 主角初遇 X 时使用"
    - "Ch11: 配角 Y 在另一场景复用"
```

### 不通过处理
降级到 `rejected/{dim}.json`，标 `failed_at: V1`，附 `salvage_hint`（如"再读 Ch15-20 看是否有第三处佐证"）。

---

## V2 — 预测力（predictive_power）

**问题**：能用 adaptation_map 处理一个**原作没写过的场景**吗？

### 通过条件
- 设计一个原作没讨论过的场景
- 用该 borrowable 的 adaptation_map 推导出非平庸结论
- 不能只会复述原作案例

### 字段
```yaml
quality.v2_predictive_power:
  passed: true|false
  novel_question: "如果主角不是孤儿而是有完整家庭，这个模式还成立吗？"
  derived_answer: "成立但变体不同：家庭提供保护网，弧线从'外部寻找归属'转为'内部守护已有'"
```

### 不通过信号
- 只能产出"努力就会成功"级别的废话
- 答案等于复述原作案例

---

## V3 — 独特性（exclusivity）

**问题**：不是"任何小说都有的套路"吗？

### 通过条件
- 抹掉作者名字，一个对类型毫无了解的聪明人说不出 → 通过
- 必须是作者**独特视角 / 反直觉见解 / 独特术语体系**

### 字段
```yaml
quality.v3_exclusivity:
  passed: true|false
  why_not_common: "反直觉：暖色弧应纯粹温暖，但作者坚持埋暗线钩子——这是反读者预期的独特手法"
```

### 自动检测（脚本兜底）
`validate-distill.py` 内置常识模式黑名单：
- "主角需要有动机" / "冲突推动剧情"
- "角色要有成长" / "世界观要自洽"
- "节奏要有起伏" / "情感要真实"
- "细节要扎实" / "伏笔要回收"

命中即标 `V3 不通过`。

---

## 评分锚点

| 通过项数 | 处理 |
|---------|------|
| 3/3 | 进入主 borrowable，写入 DB |
| 2/3 | 边界——降级到 rejected，但保留 salvage_hint |
| 1/3 或 0/3 | 移入 rejected，标记 `weak_candidate` |

## 数量预期

- 方法论密集的作品（如权游/神墓）通过率约 40-60%
- 散文化作品可能仅 15-25%
- 通过率 < 10% → extractor 可能漏读，重跑
- 通过率 > 80% → V3 标准太松，复核
