#!/bin/bash
# V3 内容污染检测脚本（shell wrapper）
# 调用 Python 实现，处理 UTF-8 中文关键词
# 用法:
#   bash auto-reject-content-pollution.sh              # 无参数：扫描整个 skill 目录
#   bash auto-reject-content-pollution.sh <file>       # 单文件
#   bash auto-reject-content-pollution.sh <dir>        # 目录批量
#   bash auto-reject-content-pollution.sh <f1> <f2>    # 多文件

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/auto-reject-content-pollution.py"

scan_file() {
    python3 "$PY_SCRIPT" "$1" || true  # 单文件 FAIL 不中断批量
}

scan_dir() {
    local dir="$1"
    find "$dir" -name "*.md" -not -path "*/.evolve/*" -print0 | while IFS= read -r -d '' f; do
        scan_file "$f"
    done
}

if [ $# -eq 0 ]; then
    # 无参数：扫描 skill 根目录（脚本上级目录）
    SKILL_DIR="$(dirname "$SCRIPT_DIR")"
    echo "扫描 skill 目录: $SKILL_DIR"
    scan_dir "$SKILL_DIR"
else
    for target in "$@"; do
        if [ -d "$target" ]; then
            scan_dir "$target"
        else
            scan_file "$target"
        fi
    done
fi
