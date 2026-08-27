#!/usr/bin/env node
"use strict"

// ZCode hook adapter for oh-story writing projects. It has no third-party
// dependencies and emits only fields accepted by ZCode 3.3.4's strict hook
// output schema. Diagnostics go to stderr; a healthy no-op keeps stdout empty.

const fs = require("node:fs")
const path = require("node:path")
const { spawnSync } = require("node:child_process")
const core = require("./story_hook_core.js")
const {
  existingDir,
  safeRelative,
  resolveTarget,
  firstLine,
  findFirst,
  discoverActiveBook,
  discoverAllBooks,
  continuityFindings,
  extractProseTargets,
  extractPatchTargets,
  proseBlockReason,
  isProsePath,
  wordcountFinding,
  duplicateTitleFindings,
  proseAfterWrite,
  shellWords,
  isGitCommitCommand,
  stagedMarkdownWarnings,
  skippableLine,
  proseNetFindings,
} = core

let hookInput = {}
try {
  const raw = fs.readFileSync(0, "utf8")
  if (raw.trim()) {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) hookInput = parsed
  }
} catch {
  hookInput = {}
}

function emit(value) {
  if (value && typeof value === "object") process.stdout.write(JSON.stringify(value))
}

function hookContext(event, text) {
  return {
    hookSpecificOutput: {
      hookEventName: event,
      additionalContext: text,
    },
  }
}

function deployedWorkspaceRoot() {
  try {
    const hooksDir = __dirname
    if (path.basename(hooksDir) === "hooks" && path.basename(path.dirname(hooksDir)) === ".zcode") {
      return path.dirname(path.dirname(hooksDir))
    }
  } catch {}
  return null
}

function projectRoot() {
  for (const name of ["ZCODE_PROJECT_DIR", "CLAUDE_PROJECT_DIR"]) {
    const candidate = existingDir(process.env[name])
    if (candidate) return candidate
  }
  const deployed = deployedWorkspaceRoot()
  if (deployed) return deployed
  const inputCwd = existingDir(hookInput.cwd)
  const cwd = inputCwd || process.cwd()
  try {
    const result = spawnSync("git", ["rev-parse", "--show-toplevel"], {
      cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    })
    if (result.status === 0 && result.stdout.trim()) return path.resolve(result.stdout.trim())
  } catch {}
  return path.resolve(cwd)
}

function sessionStart() {
  const root = projectRoot()
  const messages = []
  const book = discoverActiveBook(root)
  if (book) {
    const context = path.join(book, "追踪", "上下文.md")
    if (fs.existsSync(context)) {
      messages.push(`[novel-flow] 当前书目：${safeRelative(root, book)}。继续长篇写作前先读取 ${safeRelative(root, context)}。`)
    } else {
      messages.push(`[novel-flow] 检测到写作项目：${safeRelative(root, book)}。`)
    }
  }
  messages.push(...continuityFindings(root))
  if (messages.length) emit(hookContext("SessionStart", messages.join("\n")))
}

// UserPromptSubmit：用户消息带写作意图时，注入当前书目一行进度提示。
// 只在读到明确意图词时发声，无书目/无进度时静默，失败 fail-open。
function userPromptStatus() {
  const raw = typeof hookInput.prompt === "string" ? hookInput.prompt
    : typeof hookInput.user_prompt === "string" ? hookInput.user_prompt
    : ""
  if (!raw || !/(写|日更|续写|开书|细纲|大纲|回炉|重写|正文|章节|小说|流水线|story)/i.test(raw)) return
  const root = projectRoot()
  const book = discoverActiveBook(root)
  if (!book) return
  const lines = [`[novel-flow] 当前书目：${safeRelative(root, book)}。`]
  const body = path.join(book, "正文")
  try {
    const chapters = fs.readdirSync(body)
      .filter((name) => /^第\d{3}/.test(name))
      .sort()
    if (chapters.length) lines.push(`已写正文 ${chapters.length} 章，最新：${chapters[chapters.length - 1]}。`)
    else lines.push("尚无正文。")
  } catch {}
  const context = path.join(book, "追踪", "上下文.md")
  if (fs.existsSync(context)) lines.push(`续写前先读 ${safeRelative(root, context)}，或调 mcp__story-flow__book_status / context_pack。`)
  emit(hookContext("UserPromptSubmit", lines.join("\n")))
}

function toolName(input) {
  return String(input.tool_name || input.toolName || input.tool || input.name || "")
}

function toolPayload(input) {
  for (const key of ["tool_input", "toolInput", "input", "parameters", "args"]) {
    const value = input[key]
    if (value && typeof value === "object" && !Array.isArray(value)) return value
  }
  return {}
}

function isPathInside(root, candidate, pathApi = path) {
  const relation = pathApi.relative(root, candidate)
  return relation === "" || (
    !pathApi.isAbsolute(relation)
    && relation !== ".."
    && !relation.startsWith(`..${pathApi.sep}`)
  )
}

function targetPaths(input) {
  const root = projectRoot()
  const inputCwd = existingDir(input.cwd)
  const base = inputCwd && isPathInside(root, inputCwd) ? inputCwd : root
  const name = toolName(input)
  const payload = toolPayload(input)
  const rawTargets = []
  for (const key of ["file_path", "filePath", "path", "target", "filename"]) {
    if (typeof payload[key] === "string") rawTargets.push(payload[key])
  }
  const command = typeof payload.command === "string" ? payload.command : ""
  if (command) {
    if (/bash/i.test(name)) rawTargets.push(...extractProseTargets(command))
    else rawTargets.push(...extractPatchTargets(command), ...extractProseTargets(command))
  }
  for (const key of ["patch", "content", "text"]) {
    if (typeof payload[key] === "string" && /applypatch|patch/i.test(name)) rawTargets.push(...extractPatchTargets(payload[key]))
  }
  return [...new Set(rawTargets.filter(Boolean).map((value) => resolveTarget(root, value, base)))]
}

// 参考消费门禁：新建长篇正文章节文件前，必须有 prose_pack 留下的 checkout 账本。
// 豁免与 core 的细纲守卫保持一致：拆文库导书窗口（无 tracking state）放行。
function refCheckoutBlockReason(root, absolute) {
  const base = path.basename(absolute)
  const parent = path.basename(path.dirname(absolute))
  if (parent !== "正文" || !/^第.*章.*\.md$/.test(base)) return null
  const match = base.match(/^第0*(\d+)章/)
  if (!match) return null
  const chapter = Number(match[1])
  const book = path.dirname(path.dirname(absolute))
  if (fs.existsSync(absolute)) return null
  const state = path.join(book, "追踪", "_tracking-state.json")
  if (fs.existsSync(path.join(root, "拆文库", path.basename(book))) && !fs.existsSync(state)) return null
  const ledgerPath = path.join(book, "追踪", "_ref-checkout.json")
  let entry = null
  try {
    const ledger = JSON.parse(fs.readFileSync(ledgerPath, "utf8"))
    entry = (ledger.entries || []).filter((e) => Number(e.chapter) === chapter).pop() || null
  } catch {}
  if (!entry) {
    return `⛔ 写正文被拦截：第 ${chapter} 章没有参考消费记录。写前必须先调 mcp__story-flow__prose_pack(chapter=${chapter}) 打包细纲/题材文笔卡/文风/对标情绪模块/禁词并记账，禁止脱离参考资料直接生成正文。`
  }
  return null
}

// 写后 AI 味检查：对刚落盘的正文章节跑 check-ai-patterns，blocking 项进 additionalContext。
function aiPatternNotes(root, absolute) {
  const base = path.basename(absolute)
  const parent = path.basename(path.dirname(absolute))
  if (parent !== "正文" || !/^第.*章.*\.md$/.test(base)) return null
  let stat
  try { stat = fs.statSync(absolute) } catch { return null }
  if (!stat.isFile() || stat.size < 300) return null
  const script = path.join(root, ".zcode", "mcp", "story-flow", "scripts", "check-ai-patterns.js")
  if (!fs.existsSync(script)) return null
  try {
    const r = spawnSync("node", [script, "--json", absolute], { encoding: "utf8", timeout: 9000 })
    if (!r.stdout) return null
    const report = JSON.parse(r.stdout)
    const blocking = (report.findings || []).filter((f) => f.severity === "blocking")
    if (!blocking.length) return null
    const lines = blocking.slice(0, 12).map((f) =>
      `L${f.line} [${f.type}] ${String(f.excerpt || "").slice(0, 40)} — ${String(f.message || "").split("；")[0]}`
    )
    return `[novel ai-check] ${safeRelative(root, absolute)} 检出 ${blocking.length} 条 blocking AI 味指纹，先修复再继续（修复后可调 mcp__story-flow__ai_check 复核）：\n` + lines.join("\n")
  } catch { return null }
}

function preToolProseGuard() {
  const root = projectRoot()
  for (const target of targetPaths(hookInput)) {
    const reason = proseBlockReason(root, target) || refCheckoutBlockReason(root, target)
    if (reason) {
      emit({
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: reason,
        },
      })
      return
    }
  }
}

function preToolCommitAdvisory() {
  const payload = toolPayload(hookInput)
  const command = typeof payload.command === "string" ? payload.command : ""
  if (!command || !isGitCommitCommand(command)) return
  const warnings = stagedMarkdownWarnings(projectRoot())
  if (warnings) emit(hookContext("PreToolUse", warnings))
}

function postToolProseCheck() {
  const root = projectRoot()
  const notes = []
  for (const target of targetPaths(hookInput)) {
    const after = proseAfterWrite(root, target)
    if (after) notes.push(after)
    const ai = aiPatternNotes(root, target)
    if (ai) notes.push(ai)
  }
  if (notes.length) emit(hookContext("PostToolUse", notes.join("\n\n")))
}

function main() {
  const event = process.argv[2] || ""
  try {
    if (event === "session-start") sessionStart()
    else if (event === "user-prompt-status") userPromptStatus()
    else if (event === "pre-tool-prose-guard") preToolProseGuard()
    else if (event === "pre-tool-commit-advisory") preToolCommitAdvisory()
    else if (event === "post-tool-prose-check") postToolProseCheck()
    else {
      process.stderr.write(`unknown oh-story ZCode hook event: ${event}\n`)
      process.exitCode = 2
    }
  } catch (error) {
    // Hook checks are defensive guardrails. Unexpected parse/filesystem failures
    // fail open and are diagnosable without corrupting strict stdout JSON.
    process.stderr.write(`[oh-story zcode hook] ${error instanceof Error ? error.message : String(error)}\n`)
  }
}

if (require.main === module) main()

module.exports = {
  continuityFindings,
  proseNetFindings,
  extractProseTargets,
  extractPatchTargets,
  isGitCommitCommand,
  isPathInside,
}
