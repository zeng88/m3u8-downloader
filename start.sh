#!/usr/bin/env bash
set -euo pipefail

# 中文说明：启动脚本只检查环境，不自动修改系统依赖或终止未知进程。
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
HEALTH_URL="http://127.0.0.1:8888/status"
APP_URL="http://localhost:8888"
APP_PID=""

fail() {
  printf '\n[错误] %s\n' "$1" >&2
  exit 1
}

open_url() {
  if command -v open >/dev/null 2>&1; then
    open "$APP_URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$APP_URL" >/dev/null 2>&1 || true
  else
    printf '请手动打开：%s\n' "$APP_URL"
  fi
}

is_port_open() {
  "$VENV_PYTHON" - "$1" <<'PY'
import socket
import sys

# 中文说明：只探测端口，不对未知进程执行杀进程操作。
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.5)
    raise SystemExit(0 if sock.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)
PY
}

cleanup() {
  if [[ -n "$APP_PID" ]] && kill -0 "$APP_PID" >/dev/null 2>&1; then
    kill "$APP_PID" >/dev/null 2>&1 || true
    wait "$APP_PID" >/dev/null 2>&1 || true
  fi
}

printf '========================================================\n'
printf '                 M3U8 下载助手启动器\n'
printf '========================================================\n\n'

[[ -x "$VENV_PYTHON" ]] || fail "未找到项目虚拟环境，请先运行：$ROOT_DIR/install.sh"
"$VENV_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
  || fail '项目虚拟环境中的 Python 版本低于 3.9，请重新运行安装脚本。'
"$VENV_PYTHON" -c 'import fastapi, uvicorn, requests' \
  || fail "Python 依赖不完整，请先运行：$ROOT_DIR/install.sh"
command -v ffmpeg >/dev/null 2>&1 \
  || fail '未检测到 ffmpeg，请先运行安装脚本或手动安装 ffmpeg。'
command -v curl >/dev/null 2>&1 \
  || fail '未检测到 curl，启动脚本需要它检查服务状态；请先安装 curl 后重试。'

printf '[检查] 正在检查已有服务……\n'
if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
  printf '[提示] 服务已经运行，正在打开浏览器：%s\n' "$APP_URL"
  open_url
  exit 0
fi

if is_port_open 8888; then
  fail '8888 端口已被其他程序占用，未强制终止它；请释放端口后重试。'
fi

printf '[启动] 正在启动 FastAPI 服务……\n'
export M3U8_DOWNLOADER_NO_BROWSER=1
"$VENV_PYTHON" "$ROOT_DIR/app.py" &
APP_PID=$!
trap cleanup EXIT INT TERM

for _ in $(seq 1 60); do
  if ! kill -0 "$APP_PID" >/dev/null 2>&1; then
    fail '服务进程提前退出，请查看上方 Python 错误信息。'
  fi
  if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    printf '[完成] 服务已就绪，正在打开浏览器：%s\n' "$APP_URL"
    open_url
    printf '保持此窗口运行即可使用服务，按 Ctrl+C 可停止服务。\n'
    wait "$APP_PID"
    exit $?
  fi
  sleep 1
done

fail '服务在 60 秒内未就绪，请检查上方日志和 Python 依赖。'
