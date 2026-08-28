#!/usr/bin/env node
"use strict";

// story-flow MCP server — 网文创作流程的文件流编排与知识检索权威。
// 零第三方依赖：stdio 上跑 JSON-RPC 2.0（MCP 协议）。
// 职责边界：
//   - 书目/大纲/正文/追踪 = 只读聚合视图 + tracking_commit.py 事务透传
//   - 参考资料 = ref_route 确定性路由 + ref_search 全文检索（不生成内容，只定位权威文件）
//   - prose_pack = 写前强制打包（题材卡/文风/情绪模块/节奏/禁词/细纲/状态卡）并记录 checkout 账本
//   - ai_check = 复用内置检测脚本（.zcode/mcp/story-flow/scripts/），输出问题清单
// 禁止：本服务不写任何创作内容，不绕过 tracking_commit.py 手改状态。

const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const readline = require("node:readline");
const { spawnSync } = require("node:child_process");

const SERVER_NAME = "story-flow";
const SERVER_VERSION = "1.0.0";

// ---------- 根目录与书目 ----------

function projectRoot() {
  for (const env of ["STORY_FLOW_ROOT", "ZCODE_PROJECT_DIR"]) {
    if (process.env[env] && fs.existsSync(process.env[env])) return path.resolve(process.env[env]);
  }
  // server.js 位于 {root}/.zcode/mcp/story-flow/
  const fromHere = path.resolve(__dirname, "..", "..", "..");
  if (fs.existsSync(path.join(fromHere, ".zcode"))) return fromHere;
  return process.cwd();
}

const ROOT = projectRoot();
const NOVELS_DIR = path.join(ROOT, "novels");

function insideRoot(p) {
  const rel = path.relative(ROOT, path.resolve(p));
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}

function listBooks() {
  if (!fs.existsSync(NOVELS_DIR)) return [];
  return fs.readdirSync(NOVELS_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !e.name.startsWith("_") && !e.name.startsWith("."))
    .map((e) => e.name)
    .sort();
}

function bookDir(book) {
  const name = String(book || "").trim();
  if (!name) return activeBook();
  const candidate = path.join(NOVELS_DIR, name);
  if (!insideRoot(candidate) || !fs.existsSync(candidate)) return null;
  return candidate;
}

function activeBook() {
  const marker = path.join(ROOT, ".active-book");
  try {
    const first = fs.readFileSync(marker, "utf8").split(/\r?\n/, 1)[0].trim();
    if (first) {
      const candidate = path.resolve(ROOT, first);
      if (insideRoot(candidate) && fs.existsSync(candidate)) return candidate;
    }
  } catch {}
  const books = listBooks();
  if (!books.length) return null;
  // 优先有 追踪/正文/大纲 的书，其次最近修改
  const scored = books.map((name) => {
    const dir = path.join(NOVELS_DIR, name);
    let score = 0;
    for (const [sub, w] of [["追踪", 4], ["正文", 3], ["大纲", 2], ["设定", 1]]) {
      if (fs.existsSync(path.join(dir, sub))) score += w;
    }
    let mtime = 0;
    try { mtime = fs.statSync(dir).mtimeMs } catch {}
    return { dir, score, mtime };
  });
  scored.sort((a, b) => (b.score - a.score) || (b.mtime - a.mtime));
  return scored[0].dir;
}

// ---------- 通用工具 ----------

function readText(p, capBytes) {
  try {
    let text = fs.readFileSync(p, "utf8");
    if (capBytes && Buffer.byteLength(text, "utf8") > capBytes) {
      text = Buffer.from(text, "utf8").subarray(0, capBytes).toString("utf8") + "\n…(已截断)";
    }
    return text;
  } catch { return null }
}

function chapterFiles(dir) {
  // 返回 [{num, file, name}] 按 num 升序
  try {
    return fs.readdirSync(dir)
      .map((name) => {
        const m = name.match(/^第(\d+)章/);
        return m ? { num: Number(m[1]), file: path.join(dir, name), name } : null;
      })
      .filter(Boolean)
      .sort((a, b) => a.num - b.num);
  } catch { return [] }
}

function outlineFiles(dir) {
  try {
    return fs.readdirSync(dir)
      .map((name) => {
        const m = name.match(/^细纲_第(\d+)章/);
        return m ? { num: Number(m[1]), file: path.join(dir, name), name } : null;
      })
      .filter(Boolean)
      .sort((a, b) => a.num - b.num);
  } catch { return [] }
}

function wordCount(text) {
  const cjk = (text.match(/[\u3400-\u4dbf\u4e00-\u9fff]/g) || []).length;
  const latin = (text.match(/[A-Za-z0-9]+/g) || []).length;
  return cjk + latin;
}

function findFileByGlob(dir, prefix) {
  try {
    const hit = fs.readdirSync(dir).find((n) => n.startsWith(prefix));
    return hit ? path.join(dir, hit) : null;
  } catch { return null }
}

// ---------- 追踪账本（参考消费门禁） ----------

function checkoutFile(book) { return path.join(book, "追踪", "_ref-checkout.json") }

function readLedger(book) {
  try { return JSON.parse(fs.readFileSync(checkoutFile(book), "utf8")) } catch { return { entries: [] } }
}

function writeLedger(book, ledger) {
  fs.mkdirSync(path.dirname(checkoutFile(book)), { recursive: true });
  const tmp = checkoutFile(book) + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(ledger, null, 2), "utf8");
  fs.renameSync(tmp, checkoutFile(book));
}

// ---------- 知识检索 ----------

const LEGACY = path.join(ROOT, ".zcode", "knowledge", "legacy");
const CRAFT_REFS = path.join(ROOT, ".zcode", "knowledge", "craft");
const SCRIPTS_DIR = path.join(ROOT, ".zcode", "mcp", "story-flow", "scripts");

// 主题 → 权威文件确定性路由。路径相对 ROOT；priority: 必读/按需。
const ROUTES = [
  {
    topic: "人物设计",
    keywords: ["人物", "角色", "人设", "配角", "反派", "主角", "路人", "npc", "采访"],
    files: [
      ["必读", ".zcode/knowledge/craft/character-design-methods.md", "人物设计方法论（弧光/缺陷/欲望-恐惧轴）"],
      ["必读", ".zcode/knowledge/craft/character-basics.md", "人物基础要素与常见病"],
      ["按需", ".zcode/knowledge/craft/character-relations.md", "关系网与利益绑定"],
      ["按需", ".zcode/knowledge/legacy/novel-writer/references/character-design.md", "历史加强版：257行深度人物指南（含采访法/工具人检测）"],
      ["按需", ".zcode/knowledge/legacy/novel-character/SKILL.md", "历史独立人物 skill 全流程"],
    ],
  },
  {
    topic: "头脑风暴",
    keywords: ["头脑风暴", "灵感", "点子", "创意", "想法", "开脑洞", "选题"],
    files: [
      ["必读", ".zcode/knowledge/legacy/novel-writer/references/brainstorm-guide.md", "引导式头脑风暴五轮话术（画面感→主角→读者情绪→反派→独特规则）"],
      ["按需", ".zcode/knowledge/craft/genre-core-mechanics.md", "核心梗提炼与微创新"],
      ["按需", ".zcode/knowledge/craft/genre-catalog.md", "题材速查定位"],
    ],
  },
  {
    topic: "世界观设定",
    keywords: ["世界观", "设定", "力量体系", "等级", "势力", "地理", "经济", "货币", "体系"],
    files: [
      ["必读", ".zcode/knowledge/legacy/novel-writer/references/worldbuilding-template.md", "六维世界观建模模板（种族/势力/地理/能力/经济/日常）"],
      ["按需", ".zcode/knowledge/craft/genre-core-mechanics.md", "题材核心机制"],
      ["按需", ".zcode/knowledge/craft/genre-writing-formulas.md", "题材写作公式"],
    ],
  },
  {
    topic: "大纲卷纲",
    keywords: ["大纲", "卷纲", "剧情单元", "结构", "三幕", "主线", "支线"],
    files: [
      ["必读", ".zcode/knowledge/craft/outline-methods.md", "大纲创建法/结构分级/节点设计/细纲实操"],
      ["必读", ".zcode/knowledge/craft/outline-structure-theory.md", "大纲结构理论"],
      ["按需", ".zcode/knowledge/craft/plot-frameworks.md", "情节框架库"],
      ["按需", ".zcode/knowledge/craft/outline-conflict.md", "矛盾与主线/支线冲突结构"],
    ],
  },
  {
    topic: "细纲与单章钩子",
    keywords: ["细纲", "单章", "钩子", "章首", "章尾", "段落钩子"],
    files: [
      ["必读", ".zcode/knowledge/craft/hooks-chapter.md", "章首/章尾钩子设计（三翻四震）"],
      ["按需", ".zcode/knowledge/craft/hooks-paragraph.md", "段落级钩子"],
      ["按需", ".zcode/knowledge/craft/outline-rhythm.md", "节奏与升级感"],
      ["按需", ".zcode/knowledge/legacy/novel-writer/references/scene-type-guide.md", "场景类型指南（145行：战斗/日常/谈判等场景配方）"],
    ],
  },
  {
    topic: "线索伏笔悬念",
    keywords: ["线索", "伏笔", "悬念", "铺垫", "回收", "埋线", "误导"],
    files: [
      ["必读", ".zcode/knowledge/craft/hooks-suspense.md", "悬念体系与多线悬念周期"],
      ["必读", ".zcode/knowledge/craft/outline-conflict.md", "冲突结构（伏笔依附于冲突）"],
      ["按需", ".zcode/knowledge/craft/reversal-toolkit.md", "反转与误导工具箱"],
    ],
  },
  {
    topic: "情绪爽点节奏",
    keywords: ["情绪", "爽点", "节奏", "期待感", "打脸", "压抑", "爆发", "情绪弧线"],
    files: [
      ["必读", ".zcode/knowledge/craft/emotional-arc-design.md", "情绪弧线设计与期待感管理"],
      ["必读", ".zcode/knowledge/craft/plot-emotion-system.md", "情绪系统"],
      ["按需", ".zcode/knowledge/craft/genre-writing-formulas.md", "题材爽点公式"],
      ["按需", ".zcode/knowledge/craft/reversal-toolkit.md", "打脸节奏"],
    ],
  },
  {
    topic: "对话台词",
    keywords: ["对话", "台词", "潜台词", "说话", "口语"],
    files: [
      ["必读", ".zcode/knowledge/craft/dialogue-mastery.md", "对话功底（潜台词/白话/信息效率）"],
    ],
  },
  {
    topic: "文笔文风画面感",
    keywords: ["文笔", "文风", "画面", "描写", "白话", "句式", "镜头", "叙事手法"],
    files: [
      ["必读", ".zcode/knowledge/craft/writing-craft.md", "写作功底总纲"],
      ["必读", ".zcode/knowledge/craft/style-craft.md", "文笔工艺"],
      ["按需", ".zcode/knowledge/craft/style-genre-modules.md", "题材风格模块"],
      ["按需", ".zcode/knowledge/craft/style-combat-face.md", "战斗/脸谱化描写"],
      ["按需", ".zcode/knowledge/legacy/novel-writer/references/corpus-style-guide.md", "历史语料风格指南（110行：从真作品提炼的文风规范）"],
      ["按需", ".zcode/knowledge/legacy/novel-writer/references/writing-style.md", "白话接地气文风规范"],
    ],
  },
  {
    topic: "反AI味",
    keywords: ["反ai", "ai味", "去味", "禁词", "套路化", "模板腔", "检测"],
    files: [
      ["必读", ".zcode/knowledge/craft/anti-ai-writing.md", "反AI写作规范"],
      ["必读", ".zcode/knowledge/craft/banned-words.md", "禁用词黑名单"],
      ["按需", ".zcode/knowledge/legacy/novel-writer/references/anti-ai-patterns.md", "历史AI味黑名单（104行，含代价/反噬类设定禁令）"],
      ["工具", "mcp:ai_check", "写完正文后运行 ai_check 得到逐条指纹清单"],
    ],
  },
  {
    topic: "题材定位与读者",
    keywords: ["题材", "流派", "定位", "读者", "平台", "对标"],
    files: [
      ["必读", ".zcode/knowledge/craft/genre-catalog.md", "题材目录"],
      ["必读", ".zcode/knowledge/craft/genre-readers.md", "题材读者画像"],
      ["按需", ".zcode/knowledge/craft/genre-prose-cards.md", "题材文笔卡索引（37张卡的路由表）"],
      ["按需", ".zcode/knowledge/craft/reader-contract-and-progression.md", "读者契约与升级感"],
    ],
  },
  {
    topic: "网文作者思路借鉴",
    keywords: ["借鉴", "作者思路", "拆书", "大神", "成熟作品", "borrowable"],
    files: [
      ["必读", "素材库/借鉴库/", "12部成熟作品的 borrowable 蒸馏（全职法师/将夜/诡秘之主/权游/第一序列等587文件：世界观/人物/叙事手法/能力体系/节奏结构/高光段落）"],
      ["按需", "拆文库/", "拆文分析产出（黄金三章/结构/爽点）"],
      ["按需", ".zcode/knowledge/legacy/novel-writer/references/book-analysis-guide.md", "拆书方法指南"],
    ],
  },
  {
    topic: "作者思维与写作逻辑",
    keywords: ["作者思维", "写作逻辑", "写手", "故事观", "期待感", "满足性弃书", "两短一长", "留白", "创作逻辑", "网文作者思路"],
    files: [
      ["必读", "参考资料/网文写手写作逻辑/研报告.md", "2026-08-27 深度调研：落差模型/期待感经济学/六道坎/AI区别（36 源）"],
      ["按需", ".zcode/knowledge/legacy/novel-writer/references/shared-conventions.md", "达尔文版共享铁律"],
    ],
  },
  {
    topic: "平台上架",
    keywords: ["上架", "发布", "番茄", "起点", "晋江", "合规", "排版", "签约"],
    files: [
      ["必读", ".zcode/knowledge/legacy/novel-writer/references/platform-rules.md", "平台规则（番茄/起点/纵横：字数/章节长度/敏感词）"],
      ["按需", ".zcode/knowledge/craft/anti-ai-writing.md", "降 AI 率处理（novel-chapter-writer 步骤8-9 + novel-doctor B线）"],
    ],
  },
  {
    topic: "开书前三章",
    keywords: ["开书", "前三章", "黄金三章", "开局", "第一章"],
    files: [
      ["必读", ".zcode/knowledge/craft/opening-design.md", "开书与前三章设计"],
      ["按需", ".zcode/knowledge/craft/genre-prose-cards.md", "题材文笔卡索引"],
    ],
  },
  {
    topic: "写作流程日更",
    keywords: ["流程", "日更", "单章流程", "修订", "回炉"],
    files: [
      ["必读", ".zcode/skills/novel-chapter-writer/SKILL.md", "单章序列+日更批量纪律+修订流程（权威）"],
      ["按需", ".zcode/knowledge/craft/tracking-transaction.md", "追踪事务 JSON schema 权威"],
    ],
  },
];

function refRoute(topic) {
  const q = String(topic || "").trim().toLowerCase();
  if (!q) return { error: "topic 不能为空。可用主题见 tools/list 的 ref_route 描述。" };
  const hits = [];
  for (const route of ROUTES) {
    const matched = route.keywords.filter((k) => q.includes(k.toLowerCase()) || k.toLowerCase().includes(q));
    if (matched.length) hits.push({ route, matched });
  }
  if (!hits.length) {
    return {
      topic,
      matched: false,
      hint: `未命中路由表。可用主题：${ROUTES.map((r) => r.topic).join("、")}。或改用 ref_search 做全文检索。`,
    };
  }
  // 精确度排序：topic 完全包含 query 的大幅加权，其次关键词总长度（越长越精确），最后命中数
  const rank = (h) => (h.route.topic.toLowerCase().includes(q) ? 100 : 0)
    + h.matched.reduce((s, k) => s + k.length, 0) * 2
    + h.matched.length;
  const best = hits.sort((a, b) => rank(b) - rank(a))[0].route;
  const files = best.files.map(([priority, rel, why]) => {
    const abs = rel.startsWith("mcp:") ? null : path.join(ROOT, rel);
    return {
      priority, path: rel, why,
      exists: abs ? fs.existsSync(abs) : true,
      bytes: abs && fs.existsSync(abs) && fs.statSync(abs).isFile() ? fs.statSync(abs).size : null,
    };
  });
  return {
    topic: best.topic,
    matched: true,
    instruction: "按 priority 顺序 Read 存在的文件（必读全部 + 按需按场景）。exists=false 的条目报告缺失，不要臆造替代内容。",
    files,
  };
}

// ---- 全文检索 ----

function searchRoots(scope, book) {
  const S = String(scope || "all");
  const roots = [];
  if (S === "all" || S === "craft") {
    // 自持方法论库：craft（现役收编）+ legacy（达尔文版）
    roots.push(CRAFT_REFS, LEGACY);
  }
  if (S === "all" || S === "borrow") roots.push(path.join(ROOT, "素材库"));
  if (S === "all" || S === "market") roots.push(path.join(ROOT, "拆文库"));
  if (S === "all" || S === "research") roots.push(path.join(ROOT, "参考资料"));
  if (S === "all" || S === "book") {
    const b = book || activeBook();
    if (b) for (const sub of ["设定", "大纲", "追踪"]) {
      const d = path.join(b, sub);
      if (fs.existsSync(d)) roots.push(d);
    }
  }
  return roots;
}

function cjkBigrams(q) {
  const cleaned = Array.from(q).filter((ch) => /[\u3400-\u4dbf\u4e00-\u9fff]/.test(ch)).join("");
  const grams = [];
  for (let i = 0; i + 1 < cleaned.length; i++) grams.push(cleaned.slice(i, i + 2));
  if (!grams.length && cleaned.length) grams.push(cleaned);
  // 附带原始词（拉丁/数字）
  const latin = q.match(/[A-Za-z0-9]{2,}/g) || [];
  return [...grams, ...latin.map((w) => w.toLowerCase())];
}

function walkMd(dir, out, depth) {
  if (depth <= 0 || out.length > 4000) return;
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }) } catch { return }
  for (const e of entries) {
    if (e.name.startsWith(".") || e.name === "node_modules" || e.name === "__pycache__") continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) walkMd(full, out, depth - 1);
    else if (e.isFile() && /\.md$/i.test(e.name)) out.push(full);
  }
}

function refSearch(query, scope, book, limit) {
  const grams = cjkBigrams(String(query || ""));
  if (!grams.length) return { error: "query 需要包含中文或至少2个字母数字字符" };
  const N = Math.min(Number(limit) || 12, 30);
  const results = [];
  for (const rootDir of searchRoots(scope, book)) {
    const files = [];
    walkMd(rootDir, files, 8);
    for (const file of files) {
      const rel = path.relative(ROOT, file).replace(/\\/g, "/");
      const nameHit = grams.some((g) => path.basename(file, ".md").toLowerCase().includes(g));
      const text = readText(file, 400_000);
      if (text === null) continue;
      let score = nameHit ? 8 : 0;
      const lines = text.split(/\r?\n/);
      const hitLines = [];
      for (let i = 0; i < lines.length && hitLines.length < 3; i++) {
        const low = lines[i].toLowerCase();
        if (grams.some((g) => low.includes(g))) {
          score += 2;
          hitLines.push(`L${i + 1}: ${lines[i].trim().slice(0, 120)}`);
        }
      }
      if (score > 0) results.push({ score: score + (nameHit ? 0 : 0), path: rel, hits: hitLines });
    }
  }
  results.sort((a, b) => b.score - a.score);
  return {
    query, scope: scope || "all", grams,
    total: results.length,
    results: results.slice(0, N),
    hint: "结果按相关度排序。Read 高分文件获取权威内容；写正文前的强制打包用 prose_pack。",
  };
}

// ---------- 书目视图 ----------

function bookList() {
  const active = activeBook();
  return listBooks().map((name) => {
    const dir = path.join(NOVELS_DIR, name);
    const chapters = chapterFiles(path.join(dir, "正文"));
    const words = chapters.reduce((sum, c) => sum + wordCount(readText(c.file) || ""), 0);
    return {
      name,
      active: path.resolve(dir) === path.resolve(active || ""),
      chapters: chapters.length,
      latest_chapter: chapters.length ? chapters[chapters.length - 1].name : null,
      words,
      has_tracking: fs.existsSync(path.join(dir, "追踪", "_tracking-state.json")),
      has_outline: fs.existsSync(path.join(dir, "大纲")),
      has_setting: fs.existsSync(path.join(dir, "设定")),
    };
  });
}

function bookUse(book) {
  const dir = bookDir(book);
  if (!dir) return { error: `书目不存在：${book}。可先 book_list 查看。` };
  fs.writeFileSync(path.join(ROOT, ".active-book"), path.relative(ROOT, dir).replace(/\\/g, "/"), "utf8");
  return { ok: true, active_book: path.relative(ROOT, dir).replace(/\\/g, "/"), note: "已写入 .active-book" };
}

function bookStatus(book) {
  const dir = bookDir(book);
  if (!dir) return { error: "没有活跃书目。先 book_use 或 book_list。" };
  const chapters = chapterFiles(path.join(dir, "正文"));
  const outlines = outlineFiles(path.join(dir, "大纲"));
  const words = chapters.reduce((sum, c) => sum + wordCount(readText(c.file) || ""), 0);
  const writtenNums = new Set(chapters.map((c) => c.num));
  const nextOutline = outlines.find((o) => !writtenNums.has(o.num));
  const state = readText(path.join(dir, "追踪", "_tracking-state.json"), 60_000);
  let foreshadow = null;
  if (state) {
    try {
      const s = JSON.parse(fs.readFileSync(path.join(dir, "追踪", "_tracking-state.json"), "utf8"));
      const map = s.foreshadow && typeof s.foreshadow === "object" ? s.foreshadow : {};
      const list = Object.values(map);
      const open = list.filter((f) => f.status === "已埋");
      foreshadow = { total: list.length, open: open.length };
    } catch {}
  }
  return {
    book: path.relative(ROOT, dir).replace(/\\/g, "/"),
    chapters: chapters.length,
    words,
    latest_chapter: chapters.length ? chapters[chapters.length - 1].name : null,
    outlines: outlines.length,
    next_outline: nextOutline ? { chapter: nextOutline.num, file: nextOutline.name } : null,
    next_outline_missing_note: !nextOutline && outlines.length
      ? "所有细纲章节均已写完正文；写新章前需先补细纲（novel-planner / plot-planner 补纲流程）"
      : (!outlines.length ? "尚无细纲；先走大纲流程" : null),
    tracking: { initialized: !!state, foreshadow },
    context_card: fs.existsSync(path.join(dir, "追踪", "上下文.md")),
  };
}

function outlineNext(book) {
  const dir = bookDir(book);
  if (!dir) return { error: "没有活跃书目。" };
  const chapters = chapterFiles(path.join(dir, "正文"));
  const outlines = outlineFiles(path.join(dir, "大纲"));
  const writtenNums = new Set(chapters.map((c) => c.num));
  const next = outlines.find((o) => !writtenNums.has(o.num));
  if (!next) {
    return {
      error: outlines.length ? "细纲已全部写完正文，需要先补细纲。" : "尚无细纲文件。",
      repair: "走 story-flow 补纲阶段（story-architect agent），产出 大纲/细纲_第N章*.md 后再写正文。",
    };
  }
  const content = readText(next.file, 30_000);
  return {
    chapter: next.num,
    outline_file: path.relative(ROOT, next.file).replace(/\\/g, "/"),
    content,
    previous_chapter: chapters.length ? chapters[chapters.length - 1].name : null,
  };
}

// ---------- prose_pack：写前强制打包 ----------

function resolveGenreCard(book) {
  // 1) 设定/题材正文提示卡.md 2) 题材定位→题材文笔卡 3) null
  const card = path.join(book, "设定", "题材正文提示卡.md");
  if (fs.existsSync(card)) return { file: card, source: "项目提示卡" };
  const pos = path.join(book, "设定", "题材定位.md");
  const text = readText(pos, 20_000);
  if (text) {
    const idx = path.join(CRAFT_REFS, "genre-prose-cards.md");
    const indexText = readText(idx, 40_000) || "";
    // 从题材定位文本里抓题材词，到索引里找对应卡片文件名
    for (const line of indexText.split(/\r?\n/)) {
      const m = line.match(/\[([^\]]+)\]\(([^)]+\.md)\)/);
      if (!m) continue;
      const genre = m[1];
      if (genre && text.includes(genre)) {
        const abs = path.join(CRAFT_REFS, m[2]);
        if (fs.existsSync(abs)) return { file: abs, source: `题材定位命中「${genre}」文笔卡` };
      }
    }
  }
  return null;
}

function mainBenchmark(book) {
  // 主对标书：设定/题材定位.md 的 主对标书 字段 → 对标/{名}/
  const text = readText(path.join(book, "设定", "题材定位.md"), 20_000) || "";
  const m = text.match(/主对标书[：:]\s*([^\n\r]+)/);
  if (!m) return null;
  const name = m[1].trim().split(/[，,、\s]/)[0];
  const dir = path.join(book, "对标", name);
  if (fs.existsSync(dir)) return { name, dir };
  const fallback = path.join(ROOT, "拆文库", name);
  if (fs.existsSync(fallback)) return { name, dir: fallback, note: "项目内无对标视图，回退拆文库" };
  return null;
}

function customStyleBook(book) {
  // story 规则：设定/文风.md 含实质内容（去空白≥200字或含可执行小节）才算自定义文风
  const p = path.join(book, "设定", "文风.md");
  const text = readText(p, 100_000);
  if (!text) return null;
  const dense = text.replace(/\s/g, "");
  if (dense.length < 200 && !/(句长|标点|对话|锚点|笔调)/.test(text)) return null;
  if (/待补充|___/.test(dense.slice(0, 100)) && dense.length < 220) return null;
  return p;
}

function characterSnapshotsForOutline(book, outlineText) {
  // story 规则：久别核心角色读 追踪/角色状态/{名}.md 小快照；按细纲涉及筛选
  const dir = path.join(book, "追踪", "角色状态");
  const out = [];
  try {
    for (const name of fs.readdirSync(dir)) {
      if (!/\.md$/.test(name)) continue;
      const stem = name.replace(/\.md$/, "");
      if (outlineText && outlineText.includes(stem)) {
        out.push({ name: stem, head: (readText(path.join(dir, name), 2_500) || "").slice(0, 1_200) });
      }
      if (out.length >= 6) break;
    }
  } catch {}
  return out;
}

function matchedBenchmarkChapter(bench, targetMood) {
  // story 规则：按基调从 章节/*_摘要.md 挑同情绪章 K（爽点/字数/最小章号），必读摘要+可选深度拆解
  if (!bench || !targetMood) return null;
  const dir = path.join(bench.dir, "章节");
  let entries;
  try { entries = fs.readdirSync(dir) } catch { return null }
  const summaries = entries.filter((n) => /^第\d+章.*摘要\.md$/.test(n));
  if (!summaries.length) return null;
  const moodWords = String(targetMood).split(/[·,，/、\s]+/).filter(Boolean);
  const candidates = [];
  for (const name of summaries) {
    const text = readText(path.join(dir, name), 60_000) || "";
    const m = text.match(/基调[：:]\s*([^\n\r]+)/);
    const tone = m ? m[1].trim() : "";
    if (tone && moodWords.some((w) => tone.includes(w) || w.includes(tone))) {
      const km = name.match(/^第(\d+)章/);
      candidates.push({ k: Number(km ? km[1] : 0), name, tone, text });
    }
  }
  if (!candidates.length) return null;
  candidates.sort((a, b) => a.k - b.k);
  const pick = candidates[0];
  const deep = entries.find((n) => new RegExp(`^第0*${pick.k}章.*深度拆解\\.md$`).test(n));
  return {
    chapter: pick.k,
    summary_file: `对标/${path.basename(bench.dir)}/章节/${pick.name}`,
    tone: pick.tone,
    excerpt: pick.text.split(/\r?\n/).slice(0, 18).join("\n").slice(0, 1_600),
    deep_dive_file: deep || null,
    note: deep ? "含同章深度拆解" : "无同章深度拆解，已回退摘要",
  };
}

function prosePack(chapter, book) {
  const dir = bookDir(book);
  if (!dir) return { error: "没有活跃书目。先 book_use。" }
  const num = Number(chapter);
  if (!Number.isInteger(num) || num < 1) return { error: "chapter 必须是正整数章号。" }

  const outlines = outlineFiles(path.join(dir, "大纲"));
  const outline = outlines.find((o) => o.num === num);
  if (!outline) {
    return {
      error: `第 ${num} 章没有细纲。hook 会拦截无细纲的正文写入。`,
      repair: `先产出 大纲/细纲_第${String(num).padStart(3, "0")}章*.md（plot-planner 补纲），再调 prose_pack。`,
    };
  }
  const outlineText = readText(outline.file, 30_000) || "";
  const moodMatch = outlineText.match(/情绪[：:]\s*([^\n\r（(·|，,]+)/);
  const targetMood = moodMatch ? moodMatch[1].trim() : null;

  // 细纲三要素质检（调研结论：目标/阻碍/爆点定章纲，写正文=做选择题）
  const outlineGaps = [];
  if (!/目标/.test(outlineText)) outlineGaps.push("目标（主角这章要做什么）");
  if (!/阻碍|冲突/.test(outlineText)) outlineGaps.push("阻碍（什么人/环境/规则挡路）");
  if (!/爆点|爽点|高潮|钩子/.test(outlineText)) outlineGaps.push("爆点（怎么破局/获得什么）");
  if (!/字数目标/.test(outlineText)) outlineGaps.push("字数目标（缺省按3000代入）");
  if (!targetMood) outlineGaps.push("情绪（本章主情绪词）");

  const sections = [];
  const loaded = [];
  const gaps = { no_benchmark: false, missing_primary_contract: false, repair_action: null, custom_style: false, mood: targetMood };
  const missing = [];
  const push = (title, abs, cap, source) => {
    if (abs && fs.existsSync(abs)) {
      sections.push(`## ${title}\n（${source}）\n\n${readText(abs, cap)}`);
      loaded.push(path.relative(ROOT, abs).replace(/\\/g, "/"));
      return true;
    }
    missing.push(`${title}: ${abs ? path.relative(ROOT, abs).replace(/\\/g, "/") : "(未解析)"}`);
    return false;
  };

  push(`细纲·第${num}章`, outline.file, 30_000, "权威：本章施工图");
  push("续写状态卡（7栏）", path.join(dir, "追踪", "上下文.md"), 14_000, "权威：当前状态");
  const card = resolveGenreCard(dir);
  if (card) push("题材文笔卡", card.file, 20_000, card.source);
  else missing.push("题材文笔卡: 无提示卡且题材定位未命中 genre-prose-cards 索引（软缺失：按细纲+题材定位即时生成短卡）");

  // 自定义文风判定（story 规则：实质内容才算，权威风格基；否则对标文风，再缺失 fail-fast）
  const customStyle = customStyleBook(dir);
  if (customStyle) {
    gaps.custom_style = true;
    push("自定义文风（权威风格基）", customStyle, 20_000, "用户自写，优先级最高");
  }

  const bench = mainBenchmark(dir);
  if (bench) {
    const hasEmotion = push("对标·情绪模块", path.join(bench.dir, "剧情", "情绪模块.md"), 8_000, `权威：${bench.name}`);
    const hasRhythm = push("对标·节奏", path.join(bench.dir, "剧情", "节奏.md"), 8_000, `权威：${bench.name}`);
    if (!customStyle) push("对标·文风", path.join(bench.dir, "文风.md"), 12_000, `${bench.name}${bench.note ? "（" + bench.note + "）" : ""}`);
    // story 规则：对标存在而情绪模块/节奏缺失 = 硬阻塞（missing_primary_contract），自定义文风不豁免
    if (!hasEmotion || !hasRhythm) {
      gaps.missing_primary_contract = true;
      gaps.repair_action = `主对标书 ${bench.name} 缺 ${[!hasEmotion && "剧情/情绪模块.md", !hasRhythm && "剧情/节奏.md"].filter(Boolean).join(" 和 ")}：走 story-flow「对标拆书」采集流程补齐（参考 .zcode/knowledge/legacy/novel-writer/references/book-analysis-guide.md），从拆文库同步或重拆；不得用摘要文件假装召回，也不得进入正文生成`;
    }
    const matched = matchedBenchmarkChapter(bench, targetMood);
    if (matched) {
      sections.push(`## 对标·匹配章（第${matched.chapter}章，基调${matched.tone}）\n${matched.note}\n\n${matched.excerpt}`);
      if (matched.deep_dive_file) {
        const deep = readText(path.join(bench.dir, "章节", matched.deep_dive_file), 4_000);
        if (deep) sections.push(`### 同章深度拆解\n\n${deep}`);
      }
    }
  } else {
    gaps.no_benchmark = true;
    missing.push("对标包: 无主对标书（题材定位.md 缺 主对标书 字段）——软缺失：本章情绪/节奏目标改从细纲「情绪」、卷纲、题材定位内部材料取");
  }

  push("禁用词黑名单", path.join(CRAFT_REFS, "banned-words.md"), 8_000, "硬约束");
  push("反AI写作规范", path.join(CRAFT_REFS, "anti-ai-writing.md"), 8_000, "硬约束");

  // 久别角色快照（story 规则：按细纲涉及角色筛选，只读小文件）
  const snaps = characterSnapshotsForOutline(dir, outlineText);
  if (snaps.length) {
    sections.push(`## 角色当前快照（本章涉及）\n\n` + snaps.map((s) => `### ${s.name}\n${s.head}`).join("\n\n"));
  }

  // 前章结尾（衔接语感）
  const chapters = chapterFiles(path.join(dir, "正文"));
  const prev = chapters.filter((c) => c.num === num - 1)[0] || (chapters.length ? chapters[chapters.length - 1] : null);
  if (prev) {
    const tail = (readText(prev.file) || "").slice(-700);
    sections.push(`## 前章结尾（${prev.name}，取尾部）\n\n${tail}`);
    loaded.push(path.relative(ROOT, prev.file).replace(/\\/g, "/"));
  }
  push("伏笔当前视图", path.join(dir, "追踪", "伏笔.md"), 6_000, "权威：未回收清单");

  // 账本
  const ledger = readLedger(dir);
  ledger.entries = (ledger.entries || []).filter((e) => !(e.chapter === num));
  ledger.entries.push({
    chapter: num,
    ts: new Date().toISOString(),
    files: loaded,
    missing,
    gaps: { no_benchmark: gaps.no_benchmark, missing_primary_contract: gaps.missing_primary_contract, custom_style: gaps.custom_style },
  });
  writeLedger(dir, ledger);

  return {
    book: path.relative(ROOT, dir).replace(/\\/g, "/"),
    chapter: num,
    outline_file: path.relative(ROOT, outline.file).replace(/\\/g, "/"),
    target_mood: targetMood,
    outline_gaps: outlineGaps,
    outline_gaps_note: outlineGaps.length
      ? `细纲缺要素：${outlineGaps.join("、")}——建议先回 plot-planner 补齐再写（缺省可继续，但正文更易跑偏/欠账）`
      : "细纲三要素齐备",
    loaded_files: loaded,
    gaps,
    missing_optional: missing,
    checkout: "已记录到 追踪/_ref-checkout.json；hook 以此放行正文写入",
    instruction: gaps.missing_primary_contract
      ? "⛔ missing_primary_contract=true：先按 repair_action 修复，禁止进入正文生成"
      : gaps.no_benchmark
        ? "无对标项目：本章情绪/节奏目标从细纲「情绪」、卷纲、题材定位内部材料取，selected_emotion_module / rhythm_reference 记为「无」，意图确认标注「无对标参考」"
        : "写前准备：①从「对标·情绪模块」选 1 个与本章目标情绪最贴近的 selected_emotion_module；②从「对标·节奏」选 1 条 rhythm_reference；③用一句话写清本章意图后再动笔",
    pack: sections.join("\n\n---\n\n"),
  };
}

function checkoutStatus(chapter, book) {
  const dir = bookDir(book);
  if (!dir) return { error: "没有活跃书目。" };
  const ledger = readLedger(dir);
  const entry = (ledger.entries || []).filter((e) => e.chapter === Number(chapter)).pop();
  return entry
    ? { ok: true, entry }
    : { ok: false, note: `第 ${chapter} 章无参考消费记录。写正文前必须先调 prose_pack(chapter=${chapter})。` };
}

// ---------- tracking 与 ai_check 透传 ----------

const TRACKING_SCRIPT = path.join(SCRIPTS_DIR, "tracking_commit.py");

function runTracking(sub, book, input) {
  const dir = bookDir(book);
  if (!dir) return { error: "没有活跃书目。" };
  if (!fs.existsSync(TRACKING_SCRIPT)) return { error: `tracking_commit.py 不存在：${TRACKING_SCRIPT}` };
  const args = [TRACKING_SCRIPT, sub, "--project", dir];
  let tmp = null;
  if (input !== undefined) {
    tmp = path.join(os.tmpdir(), `story-flow-${Date.now()}.json`);
    fs.writeFileSync(tmp, typeof input === "string" ? input : JSON.stringify(input), "utf8");
    args.push("--input", tmp);
  }
  try {
    const r = spawnSync(process.env.STORY_PYTHON || "python", args, {
      cwd: dir, encoding: "utf8", timeout: 25_000,
      env: { ...process.env, PYTHONIOENCODING: "utf8" },
    });
    const out = `${r.stdout || ""}${r.stderr ? "\n[stderr]\n" + r.stderr : ""}`.trim();
    return { exit: r.status, output: out || "(无输出)" };
  } catch (e) {
    return { error: String(e) };
  } finally {
    if (tmp) try { fs.unlinkSync(tmp) } catch {}
  }
}

function resolveProseTarget(target, book) {
  // 章号 → 正文文件；否则当作 root 内相对路径
  const dir = bookDir(book);
  const n = Number(target);
  if (Number.isInteger(n) && n >= 1) {
    if (!dir) return null;
    const hit = chapterFiles(path.join(dir, "正文")).filter((c) => c.num === n)[0];
    return hit ? hit.file : null;
  }
  const p = path.resolve(ROOT, String(target));
  return insideRoot(p) && fs.existsSync(p) ? p : null;
}

function aiCheck(target, book) {
  const file = resolveProseTarget(target, book);
  if (!file) return { error: `找不到目标：${target}（章号或 root 内相对路径）` };
  const scripts = [
    ["ai-patterns", path.join(SCRIPTS_DIR, "check-ai-patterns.js")],
    ["degeneration", path.join(SCRIPTS_DIR, "check-degeneration.js")],
  ];
  const reports = {};
  for (const [key, script] of scripts) {
    if (!fs.existsSync(script)) { reports[key] = { note: "脚本缺失" }; continue }
    try {
      const r = spawnSync("node", [script, "--json", file], { encoding: "utf8", timeout: 20_000 });
      let parsed = null;
      try { parsed = JSON.parse(r.stdout) } catch {}
      reports[key] = parsed !== null ? parsed : { exit: r.status, raw: `${r.stdout || ""}\n${r.stderr || ""}`.trim().slice(0, 4000) };
    } catch (e) { reports[key] = { error: String(e) } }
  }
  return { file: path.relative(ROOT, file).replace(/\\/g, "/"), words: wordCount(readText(file) || ""), reports };
}

// ---------- MCP 工具注册表 ----------

const TOOLS = [
  {
    name: "book_list",
    description: "列出 novels/ 下所有书目及进度（章数/字数/追踪/大纲/设定是否就绪）。",
    inputSchema: { type: "object", properties: {} },
    handler: () => bookList(),
  },
  {
    name: "book_use",
    description: "切换活跃书目（写 .active-book）。参数为 novels/ 下的目录名。",
    inputSchema: { type: "object", properties: { book: { type: "string", description: "书目目录名，如 aa" } }, required: ["book"] },
    handler: (a) => bookUse(a.book),
  },
  {
    name: "book_status",
    description: "活跃书目（或指定书目）仪表盘：章数/字数/下一章细纲/伏笔/状态卡。",
    inputSchema: { type: "object", properties: { book: { type: "string" } } },
    handler: (a) => bookStatus(a.book),
  },
  {
    name: "outline_next",
    description: "取下一个未写正文章节的细纲全文；无细纲时给出补纲修复指引。",
    inputSchema: { type: "object", properties: { book: { type: "string" } } },
    handler: (a) => outlineNext(a.book),
  },
  {
    name: "context_pack",
    description: "组装某章写作上下文（细纲+状态卡+伏笔+前章尾部），比 prose_pack 轻，不含文笔/对标包。恢复上下文/审查时用。",
    inputSchema: { type: "object", properties: { chapter: { type: "integer" }, book: { type: "string" } }, required: ["chapter"] },
    handler: (a) => {
      const dir = bookDir(a.book);
      if (!dir) return { error: "没有活跃书目。" };
      const outlines = outlineFiles(path.join(dir, "大纲"));
      const outline = outlines.find((o) => o.num === Number(a.chapter));
      if (!outline) return { error: `第 ${a.chapter} 章无细纲。` };
      const parts = [];
      parts.push(`## 细纲·第${a.chapter}章\n\n${readText(outline.file, 30_000)}`);
      const ctx = path.join(dir, "追踪", "上下文.md");
      if (fs.existsSync(ctx)) parts.push(`## 续写状态卡\n\n${readText(ctx, 14_000)}`);
      const fs_ = path.join(dir, "追踪", "伏笔.md");
      if (fs.existsSync(fs_)) parts.push(`## 伏笔视图\n\n${readText(fs_, 6_000)}`);
      const chapters = chapterFiles(path.join(dir, "正文"));
      const prev = chapters.filter((c) => c.num === Number(a.chapter) - 1)[0];
      if (prev) parts.push(`## 前章结尾\n\n${(readText(prev.file) || "").slice(-700)}`);
      return { chapter: Number(a.chapter), pack: parts.join("\n\n---\n\n") };
    },
  },
  {
    name: "ref_route",
    description: `参考资料确定性路由：按主题返回权威文件清单（含优先级与缺失标记）。可用主题：${ROUTES.map((r) => r.topic).join("、")}。设计/写文前先路由再 Read，禁止脱离参考自由发挥。`,
    inputSchema: { type: "object", properties: { topic: { type: "string", description: "主题关键词，如 人物设计 / 线索伏笔悬念 / 反AI味 / 文笔文风画面感" } }, required: ["topic"] },
    handler: (a) => refRoute(a.topic),
  },
  {
    name: "ref_search",
    description: "跨知识库全文检索（CJK 二元组打分）。scope: craft=skill方法论+历史知识库, borrow=素材库借鉴库(12作品蒸馏), market=拆文库, research=参考资料, book=当前书设定/大纲/追踪, all=全部。",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string" },
        scope: { type: "string", enum: ["all", "craft", "borrow", "market", "research", "book"] },
        limit: { type: "integer", minimum: 1, maximum: 30 },
        book: { type: "string" },
      },
      required: ["query"],
    },
    handler: (a) => refSearch(a.query, a.scope, a.book, a.limit),
  },
  {
    name: "prose_pack",
    description: "写正文前的强制打包：细纲+状态卡+题材文笔卡+文风(自定义优先)+对标情绪模块/节奏+对标匹配章+禁词+反AI规范+角色快照+前章结尾+伏笔，并记录 checkout 账本（hook 依据账本放行正文写入）。gaps.missing_primary_contract=true 时禁止写正文，按 repair_action 修复。每章写前必调。",
    inputSchema: { type: "object", properties: { chapter: { type: "integer", description: "章号" }, book: { type: "string" } }, required: ["chapter"] },
    handler: (a) => prosePack(a.chapter, a.book),
  },
  {
    name: "checkout_status",
    description: "查询某章的参考消费账本（hook 门禁依据）。",
    inputSchema: { type: "object", properties: { chapter: { type: "integer" }, book: { type: "string" } }, required: ["chapter"] },
    handler: (a) => checkoutStatus(a.chapter, a.book),
  },
  {
    name: "tracking_init",
    description: "初始化 追踪/_tracking-state.json（透传 tracking_commit.py init）。input 为该脚本的 init JSON 文档。",
    inputSchema: { type: "object", properties: { book: { type: "string" }, input: { type: "object" } }, required: ["input"] },
    handler: (a) => runTracking("init", a.book, a.input),
  },
  {
    name: "tracking_commit",
    description: "提交章节事务（透传 tracking_commit.py commit）：唯一合法的状态写入通道。input 为事务 JSON（character_snapshots/foreshadow/timeline/context 等）。",
    inputSchema: { type: "object", properties: { book: { type: "string" }, input: { type: "object" } }, required: ["input"] },
    handler: (a) => runTracking("commit", a.book, a.input),
  },
  {
    name: "tracking_check",
    description: "校验追踪状态一致性（透传 tracking_commit.py check）。",
    inputSchema: { type: "object", properties: { book: { type: "string" } } },
    handler: (a) => runTracking("check", a.book, undefined),
  },
  {
    name: "ai_check",
    description: "对正文文件运行 AI 味与退化检测（包 check-ai-patterns.js + check-degeneration.js）。target 为章号或 root 内相对路径。写完每章后必调。",
    inputSchema: { type: "object", properties: { target: { type: "string", description: "章号（如 3）或相对路径" }, book: { type: "string" } }, required: ["target"] },
    handler: (a) => aiCheck(a.target, a.book),
  },
];

// ---------- JSON-RPC / MCP stdio ----------

function send(obj) { process.stdout.write(JSON.stringify(obj) + "\n") }

function result(id, value) { send({ jsonrpc: "2.0", id, result: value }) }
function failure(id, code, message) { send({ jsonrpc: "2.0", id, error: { code, message } }) }

function handleRequest(msg) {
  const { id, method, params } = msg;
  switch (method) {
    case "initialize":
      result(id, {
        protocolVersion: (params && params.protocolVersion) || "2024-11-05",
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
        instructions: "网文创作流程编排与知识检索。写正文前必调 prose_pack；状态只经 tracking_commit 写入；查资料用 ref_route/ref_search，不要凭空生成方法论。",
      });
      break;
    case "ping":
      result(id, {});
      break;
    case "tools/list":
      result(id, {
        tools: TOOLS.map((t) => ({
          name: t.name,
          description: t.description,
          inputSchema: t.inputSchema,
        })),
      });
      break;
    case "tools/call": {
      const name = params && params.name;
      const tool = TOOLS.find((t) => t.name === name);
      if (!tool) { failure(id, -32602, `unknown tool: ${name}`); break }
      try {
        const value = tool.handler((params && params.arguments) || {});
        const isError = value && typeof value === "object" && value.error;
        result(id, {
          content: [{ type: "text", text: JSON.stringify(value, null, 2) }],
          isError: !!isError,
        });
      } catch (e) {
        result(id, {
          content: [{ type: "text", text: `tool ${name} crashed: ${e && e.stack || e}` }],
          isError: true,
        });
      }
      break;
    }
    case "resources/list":
      result(id, { resources: [] });
      break;
    case "prompts/list":
      result(id, { prompts: [] });
      break;
    default:
      if (id !== undefined) failure(id, -32601, `method not found: ${method}`);
  }
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on("line", (line) => {
  const text = line.trim();
  if (!text) return;
  let msg;
  try { msg = JSON.parse(text) } catch { process.stderr.write(`[story-flow] non-JSON line ignored\n`); return }
  if (msg && msg.method && typeof msg.method === "string") handleRequest(msg);
});
rl.on("close", () => process.exit(0));

process.stderr.write(`[story-flow] server up. root=${ROOT}\n`);
