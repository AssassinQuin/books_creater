#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const USAGE = `Usage: node normalize-enums.js [--check] <file...> | <dir...>

Deterministically fix out-of-enum 基调/主题标签 values in chapter-extractor 摘要.
chapter-extractor (haiku) systematically drifts to synonyms outside the enum
(好奇/期待/震撼 as 基调; 紧张/恐怖/日常 as 主题标签, etc.). This script maps
them back to the nearest legal value, avoiding per-chapter sonnet retries.

Legal 基调 (10): 紧张 轻松 悲伤 热血 爽 甜 温馨 恐怖 压抑 其他
Legal 主题标签 (12): 爱情 亲情 友情 权力 金钱 成长 复仇 悬念 搞笑 热血 日常 其他

Rules:
  - known out-of-range value → mapped nearest legal value (see tables below)
  - unknown out-of-range value → fallback "其他" (reported as ⚠️)
  - already-legal value → untouched

Options:
  --check   report only, do not modify files
`;

const LEGAL_TONE = new Set(['紧张', '轻松', '悲伤', '热血', '爽', '甜', '温馨', '恐怖', '压抑', '其他']);
const LEGAL_THEME = new Set(['爱情', '亲情', '友情', '权力', '金钱', '成长', '复仇', '悬念', '搞笑', '热血', '日常', '其他']);

// out-of-range → legal (nearest). Unlisted values fallback to 其他.
const TONE_FIX = {
  '好奇': '其他', '期待': '紧张', '期待感': '紧张', '震撼': '热血', '震撼感': '热血',
  '震惊': '紧张', '惊讶': '其他', '兴奋': '热血', '激动': '热血',
  '害怕': '恐怖', '恐惧': '恐怖', '焦虑': '压抑', '焦急': '紧张', '急切': '紧张',
  '燃': '热血', '痛': '悲伤', '难受': '悲伤', '心酸': '悲伤',
  // 主题标签词误填进基调位
  '日常': '轻松', '亲情': '温馨', '爱情': '甜', '友情': '温馨',
  '权力': '压抑', '金钱': '其他', '成长': '其他', '复仇': '压抑',
  '悬念': '紧张', '搞笑': '轻松',
};
const THEME_FIX = {
  // 基调词误填进主题标签位
  '紧张': '悬念', '恐怖': '悬念', '压抑': '其他', '温馨': '亲情',
  '甜': '爱情', '悲伤': '其他', '轻松': '日常', '爽': '热血',
  '害怕': '悬念', '恐惧': '悬念',
  // 近义词
  '震撼': '热血', '好奇': '悬念', '期待': '悬念', '震惊': '悬念', '燃': '热血', '燃情': '热血',
  '悬疑': '悬念', '悬疑感': '悬念', '疑案': '悬念', '谜团': '悬念',
  // 情节点类型词误填进主题标签位（无主题意义→其他）
  '行动': '其他', '对话': '其他', '转折点': '其他', '信息揭示': '其他',
  '冲突': '其他', '解决': '其他', '状态变化': '其他', '铺垫': '其他',
};

// 末行格式：主题标签{X} | 基调：{Y}
const LINE_RE = /^(主题标签)([^：|\n]+?)\s*\|\s*(基调：)(\S+?)\s*$/;

function fixText(text) {
  const fixes = [];
  const unknownTones = new Set();
  const unknownThemes = new Set();
  const lines = text.split('\n').map((line, idx) => {
    const mm = LINE_RE.exec(line);
    if (!mm) return line;
    const pre = mm[1], theme = mm[2].trim(), tonePre = mm[3], tone = mm[4].trim();
    let nt = theme, no = tone;
    if (!LEGAL_THEME.has(theme)) {
      nt = Object.prototype.hasOwnProperty.call(THEME_FIX, theme) ? THEME_FIX[theme] : '其他';
      if (!Object.prototype.hasOwnProperty.call(THEME_FIX, theme)) unknownThemes.add(theme);
      fixes.push({ ln: idx + 1, field: '主题标签', old: theme, neu: nt });
    }
    if (!LEGAL_TONE.has(tone)) {
      no = Object.prototype.hasOwnProperty.call(TONE_FIX, tone) ? TONE_FIX[tone] : '其他';
      if (!Object.prototype.hasOwnProperty.call(TONE_FIX, tone)) unknownTones.add(tone);
      fixes.push({ ln: idx + 1, field: '基调', old: tone, neu: no });
    }
    return `${pre}${nt} | ${tonePre}${no}`;
  });
  return { newText: lines.join('\n'), fixes, unknownTones, unknownThemes };
}

function collectFiles(args) {
  const out = [];
  for (const a of args) {
    const st = fs.statSync(a);
    if (st.isDirectory()) {
      for (const f of fs.readdirSync(a).sort()) {
        if (f.endsWith('_摘要.md')) out.push(path.join(a, f));
      }
    } else {
      out.push(a);
    }
  }
  return out;
}

function main() {
  const args = [];
  let check = false;
  for (let i = 2; i < process.argv.length; i += 1) {
    const a = process.argv[i];
    if (a === '--check') check = true;
    else if (a === '-h' || a === '--help') { process.stdout.write(USAGE); process.exit(0); }
    else if (a.startsWith('-')) { console.error(`Unknown option: ${a}`); process.exit(1); }
    else args.push(a);
  }
  if (!args.length) { process.stdout.write(USAGE); process.exit(1); }
  const files = collectFiles(args);
  let totalFixes = 0;
  const totalUnknown = new Set();
  for (const f of files) {
    const text = fs.readFileSync(f, 'utf8');
    const { newText, fixes, unknownTones, unknownThemes } = fixText(text);
    if (!fixes.length) {
      console.log(`✓ ${path.basename(f)}: 无越界值`);
      continue;
    }
    const tag = check ? '[check]' : '[fix]';
    console.log(`${tag} ${path.basename(f)}: 修正 ${fixes.length} 处`);
    for (const x of fixes) console.log(`   L${x.ln} ${x.field}: ${x.old} → ${x.neu}`);
    if (unknownTones.size) console.log(`   ⚠️ 未知基调值(回退其他): ${[...unknownTones].join(', ')}`);
    if (unknownThemes.size) console.log(`   ⚠️ 未知主题标签值(回退其他): ${[...unknownThemes].join(', ')}`);
    if (!check) fs.writeFileSync(f, newText, 'utf8');
    totalFixes += fixes.length;
    [...unknownTones, ...unknownThemes].forEach(v => totalUnknown.add(v));
  }
  console.log(`\n汇总: ${files.length} 文件, ${totalFixes} 处修正${totalUnknown.size ? `, 未知值 ${[...totalUnknown].join(', ')}` : ''}`);
}

main();
