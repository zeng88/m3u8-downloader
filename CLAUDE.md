# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 提供在此仓库中工作的指导。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用（自动打开浏览器 http://localhost:8888）
python app.py

# 运行全部测试
pip install pytest
pytest test_app.py -v

# 运行单个测试
pytest test_app.py::test_extract_direct_url -v

# 端口 8888 被占用时，强制释放
lsof -ti:8888 | xargs kill -9
```

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

## 已知问题

`test_app.py` 中的 `test_build_ffmpeg_cmd_flags` 断言 ffmpeg 命令包含 `-bsf:a` / `aac_adtstoasc`，但 `build_ffmpeg_cmd()` 实际不含这两个参数，该测试目前会失败。
