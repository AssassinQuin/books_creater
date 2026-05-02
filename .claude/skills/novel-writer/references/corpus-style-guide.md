# 语料库风格学习指南

> 从91Writing 的 CorpusManager + generatePersonalizedContent 机制优化而来。用 Memory 系统实现语料库风格学习。

---

## 概念

语料库（Corpus）= 用户喜欢的写作片段集合。系统从中提取风格特征，写作时参考，使输出风格更接近用户偏好。

91Writing 的实现方式：Vue 组件上传文本 → 存 localStorage → 生成时拼接 `参考以下写作风格：{corpus_text}`。

我们的优化：存入 Memory MCP → 按标签分类 → 写作时按需检索 → 只注入风格特征（不注入原文，节省 context）。

---

## 语料入库

### 入口

用户说"加素材"或提供文本片段。

### 分类入库

| 内容类型 | tags | 说明 |
|---------|------|------|
| 喜欢的文风片段 | `shared,style-profile` | 用来学习风格 |
| 拆书提取的技巧 | `shared,technique` | 可复用的具体手法 |
| 通用素材 | `shared,material` | 情节灵感/设定参考 |
| 拆书笔记 | `shared,analysis` | 完整的拆书分析 |
| AI味黑名单 | `shared,anti-ai-pattern` | 禁用词/句式 |

### 入库操作

```
memory_store(
  content="{文本内容}",
  metadata={tags: "shared,style-profile", type: "reference"}
)
```

---

## 风格提取

当用户入库 style-profile 类型内容时，自动提取以下特征并存为结构化描述：

### 提取维度

| 维度 | 提取方法 | 示例输出 |
|------|---------|---------|
| **句长分布** | 统计每句字数，分短(<10)/中(10-20)/长(>20) | 短40% / 中45% / 长15% |
| **对话占比** | 引号内字数 / 总字数 | 35% |
| **描写密度** | 描写段落 / 总段落数 | 每3段有1段描写 |
| **五感偏好** | 感官词频统计 | 视觉为主，听觉为辅 |
| **情绪基调** | 情绪词统计 | 克制内敛 / 外放热血 |
| **独特用词** | 高频但非常见的词 | "倒也""罢了""且慢" |

### 提取结果存入

```
memory_store(
  content="风格特征：{句式偏好}，对话占比{N}%，描写密度{N}，五感偏好{...}，基调{...}，独特用词{...}",
  metadata={tags: "shared,style-profile", type: "reference"}
)
```

---

## 写作时引用

### 触发条件

`novel-chapter-writer` 写前检查：`memory_search(query="style-profile", tags=["shared,style-profile"])`

### 引用方式

**不要**拼接语料原文到 prompt（太长）。

**而是**读取风格特征描述，在写作规则中加入：

```
本次写作参考风格：{风格特征描述}
具体要求：
- 句式分布偏向：{短/中/长占比}
- 对话占比目标：{N}%
- 描写风格：{感官偏好}
- 用词偏好：{独特用词列表}
```

### 多风格管理

用户可以有多套风格语料。通过 `memory_search` 的 query 区分：
- `memory_search(query="热血风格")` → 找到对应风格特征
- `memory_search(query="细腻风格")` → 找到另一套

用户在写作时可以说"用热血风格写"或"参考XX风格"。

---

## 与91Writing的对比优化

| 方面 | 91Writing | 我们 |
|------|-----------|------|
| 存储 | localStorage（浏览器限定） | Memory MCP（跨会话持久化） |
| 风格提取 | 无（直接拼接原文） | 自动提取特征（句式/占比/用词） |
| Context消耗 | 拼接全部语料原文 | 只注入特征摘要 |
| 检索方式 | 全量拼接 | 按标签/语义检索 |
| 多风格 | 无区分 | 按query区分多套风格 |
| 与写作集成 | 硬编码在生成prompt | skill自动检查+引用 |
