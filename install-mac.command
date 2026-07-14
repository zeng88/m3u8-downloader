#!/usr/bin/env bash

# 中文说明：macOS 双击入口，安装完成后保留结果提示。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

"$SCRIPT_DIR/install.sh"
status=$?
printf '\n安装脚本已退出，退出码：%s\n' "$status"
read -r -p '按 Enter 键关闭窗口……' _
exit "$status"
