# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 提供在此仓库中工作的指导。

## 常用命令

```bash
# 推荐：按平台一键安装依赖
./install.sh                         # macOS/Linux 终端
# macOS 也可以双击 install-mac.command
# Windows 双击 install-windows.bat

# 推荐：按平台一键启动
./start.sh                           # macOS/Linux 终端
# macOS 也可以双击 start.command
# Windows 双击 start.bat

# 手动安装依赖到项目虚拟环境
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# 手动启动应用（自动打开浏览器 http://localhost:8888）
.venv/bin/python app.py

# 运行全部测试
pip install pytest
pytest test_app.py test_launch_scripts.py -v

# 运行单个测试
pytest test_app.py::test_extract_direct_url -v

# 查看 8888 端口占用者；启动脚本不会强制杀掉未知进程
lsof -nP -iTCP:8888 -sTCP:LISTEN
```

一键安装脚本会创建项目根目录 `.venv`，并安装 `requirements.txt` 中的 Python 依赖和系统 `ffmpeg`。一键启动脚本只检查依赖；如果缺少依赖，会提示重新运行安装脚本，不会自动修改全局 Python 环境。

## 架构说明

这是一个**单文件应用**（`app.py`），无需任何构建步骤。

**后端**：FastAPI 由 uvicorn 在 8888 端口提供服务。API 一览：

| 接口 | 用途 |
|---|---|
| `GET /` | 返回完整前端页面（HTML 字符串内嵌在 `app.py` 中） |
| `GET /status` | 检测系统是否已安装 `ffmpeg` |
| `POST /analyze` | 用 `requests` 抓取目标页面，调用 `extract_m3u8_links()` 正则提取 m3u8 链接 |
| `POST /pick-dir` | 启动 `python3` 子进程，弹出 `tkinter` 原生文件夹选择对话框 |
| `POST /execute` | 通过 `subprocess.Popen` 启动 `ffmpeg`，引用存入全局变量 `ffmpeg_process` |
| `GET /progress` | SSE 流：逐行读取 `ffmpeg_process.stderr`，推送 `data:` 事件；进程结束后推送 `event: done` |
| `POST /stop` | 调用 `ffmpeg_process.terminate()` 终止下载 |

**前端**：纯 HTML/CSS/JS，以 `HTML_CONTENT` 字符串常量内嵌在 `app.py` 中，无框架、无构建工具。通过 `fetch()` 和 `EventSource`（SSE）与后端通信。

**关键设计细节**：
- `ffmpeg_process` 是模块级全局变量，由 `ffmpeg_lock`（`threading.Lock`）保护，同一时刻只允许一个下载任务运行。
- `ffmpeg` 始终以参数列表方式调用（不使用 `shell=True`），防止命令注入。
- `extract_m3u8_links()` 先规范化 `/` 和 `\/` 转义、反转义 HTML 实体，再用三条正则分别匹配裸 URL、JSON 字段值、单引号字符串。
- `build_ffmpeg_cmd()` 在提供 referer 时注入 `-referer` 和 `-headers Origin:`，用于绕过 CDN 防盗链（403）。
- `/pick-dir` 将 `tkinter` 放在独立 `python3` 子进程中运行，因为 tkinter 与 asyncio 事件循环不兼容。

## 运行约定

`build_ffmpeg_cmd()` 会为 AAC 音频注入 `-bsf:a aac_adtstoasc`，保证 MP4 封装兼容性；启动/安装脚本不会强制杀掉未知端口进程。
