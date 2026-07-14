#!/usr/bin/env bash
set -euo pipefail

# 中文说明：本脚本为 macOS/Linux 初始化项目运行环境，不污染系统 Python 包。
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
VENV_DIR="$ROOT_DIR/.venv"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
PYTHON_BIN=""

print_header() {
  printf '\n========================================================\n'
  printf '       M3U8 下载助手环境一键安装（macOS/Linux）\n'
  printf '========================================================\n\n'
}

fail() {
  printf '\n[错误] %s\n' "$1" >&2
  exit 1
}

python_is_supported() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
    >/dev/null 2>&1
}

find_supported_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && python_is_supported "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

run_privileged() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "当前用户不是 root，且未找到 sudo，无法安装系统依赖。"
  fi
}

load_homebrew() {
  if command -v brew >/dev/null 2>&1; then
    return 0
  fi

  printf '[1/4] 未找到 Homebrew，正在尝试自动安装。可能需要输入 macOS 密码。\n'
  command -v curl >/dev/null 2>&1 || fail '未找到 curl，无法自动安装 Homebrew。'
  NONINTERACTIVE=1 /bin/bash -c \
    "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi

  command -v brew >/dev/null 2>&1 || fail 'Homebrew 安装后仍无法找到 brew，请重新打开终端后重试。'
}

install_python_linux() {
  if command -v apt-get >/dev/null 2>&1; then
    run_privileged apt-get update
    run_privileged apt-get install -y python3 python3-pip python3-venv
  elif command -v dnf >/dev/null 2>&1; then
    run_privileged dnf install -y python3 python3-pip
  elif command -v pacman >/dev/null 2>&1; then
    run_privileged pacman -Sy --noconfirm python python-pip
  else
    fail '未找到 apt-get、dnf 或 pacman，请先安装 Python 3.9+ 后重试。'
  fi
}

ensure_python() {
  local python_bin
  python_bin="$(find_supported_python || true)"
  if [[ -n "$python_bin" ]]; then
    printf '[1/4] Python 已就绪：%s\n' "$($python_bin --version 2>&1)"
    PYTHON_BIN="$python_bin"
    return 0
  fi

  printf '[1/4] 未检测到 Python 3.9+，正在尝试安装。\n'
  if [[ "$(uname -s)" == "Darwin" ]]; then
    load_homebrew
    brew install python
  else
    install_python_linux
  fi

  python_bin="$(find_supported_python || true)"
  [[ -n "$python_bin" ]] || fail 'Python 安装后仍不可用，请重新打开终端后重试。'
  printf '[OK] Python 已安装：%s\n' "$($python_bin --version 2>&1)"
  PYTHON_BIN="$python_bin"
}

ensure_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1; then
    printf '[2/4] ffmpeg 已就绪：%s\n' "$(ffmpeg -version 2>&1 | head -n 1)"
    return 0
  fi

  printf '[2/4] 未检测到 ffmpeg，正在尝试安装。\n'
  if [[ "$(uname -s)" == "Darwin" ]]; then
    load_homebrew
    brew install ffmpeg
  elif command -v apt-get >/dev/null 2>&1; then
    run_privileged apt-get update
    run_privileged apt-get install -y ffmpeg
  elif command -v dnf >/dev/null 2>&1; then
    run_privileged dnf install -y ffmpeg
  elif command -v pacman >/dev/null 2>&1; then
    run_privileged pacman -Sy --noconfirm ffmpeg
  else
    fail '未找到可用的系统包管理器，请手动安装 ffmpeg 后重试。'
  fi

  command -v ffmpeg >/dev/null 2>&1 || fail 'ffmpeg 安装后仍不可用，请重新打开终端后重试。'
  printf '[OK] ffmpeg 已安装。\n'
}

verify_python_packages() {
  "$1" -c 'import fastapi, uvicorn, requests' \
    || fail 'Python 依赖导入失败，请检查 pip 输出并重新运行本安装脚本。'
}

print_header
[[ -f "$REQUIREMENTS_FILE" ]] || fail "找不到依赖文件：$REQUIREMENTS_FILE"

ensure_python
ensure_ffmpeg

printf '[3/4] 创建项目虚拟环境：%s\n' "$VENV_DIR"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR" \
    || fail '创建虚拟环境失败，请确认当前 Python 包含 venv 模块。'
fi

VENV_PYTHON="$VENV_DIR/bin/python"
printf '[4/4] 安装 Python 依赖，请稍候……\n'
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE"
verify_python_packages "$VENV_PYTHON"

printf '\n[完成] 环境安装成功。\n'
printf '现在可以执行：%s\n' "$ROOT_DIR/start.sh"
