#!/bin/bash
# V3 内容污染检测脚本（shell wrapper）
# 调用 Python 实现，处理 UTF-8 中文关键词
# 用法: bash auto-reject-content-pollution.sh <target_file>

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "${SCRIPT_DIR}/auto-reject-content-pollution.py" "$@"
