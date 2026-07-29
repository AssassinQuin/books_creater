#!/usr/bin/env python3
"""foreshadow_schema.py — 伏笔台账 schema 校验（表头驱动，兼容多版本）。

被 validate-story-commit.sh 在 git commit 前调用，校验 追踪/伏笔.md。
违规时输出错误清单到 stdout 并 exit 1（阻断提交）；合规 exit 0。

设计：表头驱动，不硬编码列号。兼容两套在用 schema：
  - v3（这次不一样）：# / 伏笔 / 埋设卷 / 计划揭示 / 状态 / 分层 / 真实答案
  - 旧版（深渊拾荒人）：ID / 伏笔内容 / 埋设章节 / 预计回收章节 / 状态 / 重要度
状态合法集（语义等价的用词都接受）：未埋 / 待埋设 / 已埋 / 已回收。
阻断只抓真坏数据（状态非法、F编号格式错），不强推某套枚举或强迁旧书。
支持多表格台账（F1-F14 / F15-F22 各有表头行）：后续表头行跳过，不误判。
"""
import re
import sys

VALID_STATUS = {"未埋", "待埋设", "已埋", "已回收"}
FNUM_RE = re.compile(r"^F\d")
SEP_RE = re.compile(r"^\|[-\s|]+$")
HEADER_ID_TOKENS = ("#", "ID", "编号")


def find_header(lines):
    """返回首个表头 (header_idx, status_col, id_col)；无表头返回 None。

    status_col 必为 int（找到表头的前提）；id_col 可能为 None（表头无显式编号列）。
    """
    for i, line in enumerate(lines):
        if not (line.startswith("|") and "状态" in line):
            continue
        cols = [c.strip() for c in line.split("|")]
        status_col = None
        id_col = None
        for j, c in enumerate(cols):
            if c == "状态" and status_col is None:
                status_col = j
            elif c in HEADER_ID_TOKENS and id_col is None:
                id_col = j
        if status_col is not None:
            return i, status_col, id_col
    return None


def validate(path):
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except Exception:
        return []  # 读失败不阻断（编码/权限问题另查），避免误卡 commit

    found = find_header(lines)
    if found is None:
        return []  # 非表格伏笔文件，不校验
    header_idx, status_col, id_col = found

    errs = []
    for i in range(header_idx + 1, len(lines)):
        line = lines[i]
        if not line.startswith("|") or SEP_RE.match(line):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) <= status_col:
            continue
        status = cols[status_col]
        fnum = cols[id_col] if (id_col is not None and id_col < len(cols)) else ""
        # 空状态=非伏笔数据行（其他表如回收日志/密度表，或空行），跳过。
        # 「伏笔忘填状态」不在此阻断，由 detect-story-gaps advisory 兜底。
        if status == "":
            continue
        # 跳过后续表格的表头行（多表格台账：F1-F14 / F15-F22 各带表头）
        if status == "状态" or fnum in HEADER_ID_TOKENS:
            continue
        # 预留位豁免：ID 含「预留」/整行仅占位 — /状态为 —
        nonempty = {c for c in cols if c and c != "—"}
        if "预留" in fnum or not nonempty or status == "—":
            continue
        if status not in VALID_STATUS:
            legal = "/".join(sorted(VALID_STATUS))
            errs.append("  L%d [%s]: 状态「%s」非法（合法集: %s）" % (i + 1, fnum or "?", status, legal))
        if id_col is not None and not FNUM_RE.match(fnum):
            errs.append("  L%d: 编号「%s」非法（需 F 开头 + 数字，如 F1/F001）" % (i + 1, fnum))
    return errs


def main():
    if len(sys.argv) < 2:
        print("用法: foreshadow_schema.py <伏笔.md>", file=sys.stderr)
        sys.exit(2)
    errs = validate(sys.argv[1])
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
