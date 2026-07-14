#!/usr/bin/env bash

# 中文说明：macOS 双击入口，保留终端窗口以便查看服务日志。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

"$SCRIPT_DIR/start.sh"
status=$?
printf '\n服务已退出，退出码：%s\n' "$status"
read -r -p '按 Enter 键关闭窗口……' _
exit "$status"
