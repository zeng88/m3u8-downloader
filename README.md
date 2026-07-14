# M3U8 下载助手

一个运行在本地的单页 Web 工具，输入视频网址后自动提取 m3u8 流媒体链接，生成高效的 ffmpeg 下载命令，支持一键执行并实时显示下载进度。

![界面预览](https://img.shields.io/badge/界面-深色主题-0f1117?style=flat-square) ![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)

---

## 功能特性

- **自动提取 m3u8 链接** — 抓取视频页面 HTML，通过多条正则匹配各类 m3u8 地址（直接 URL、JSON 字段、转义格式均支持）
- **多链接选择** — 若页面包含多个画质版本（如 1080p / 720p），以单选列表展示，手动选择
- **高效 ffmpeg 命令** — `-threads 0` 多线程 + `-c copy` 无转码封装，速度最快；网络断开自动重连
- **Referer / Origin 支持** — 针对 CDN 鉴权（auth_key）或防盗链导致的 403，自动填充来源网址并注入 `-referer` / `-headers` 参数
- **系统文件夹选择器** — 点击"选择"按钮弹出 macOS 原生文件夹对话框，无需手动输入路径
- **一键执行 + 实时进度** — 后端异步启动 ffmpeg，通过 SSE 实时推送 stderr 输出，进度条自动更新
- **复制命令** — 一键复制完整 ffmpeg 命令，方便在终端手动执行或二次修改
- **启动自动打开浏览器** — 运行后 0.8 秒自动打开 `http://localhost:8888`

---

## 系统要求

| 依赖 | 版本 | 安装方式 |
|------|------|----------|
| Python | 3.9+ | [python.org](https://www.python.org) |
| ffmpeg | 任意 | `brew install ffmpeg` |
| tkinter | 内置 | Python 标准库，无需额外安装 |

安装脚本会把 Python 包安装到项目根目录的 `.venv`，不会污染系统 Python 环境。

---

## 快速开始

### macOS

1. 双击 `install-mac.command`，或在终端执行：

```bash
./install.sh
```

2. 安装完成后双击 `start.command`，或执行：

```bash
./start.sh
```

### Windows

1. 双击 `install-windows.bat`，脚本会通过 winget 检测/安装 Python 和 ffmpeg，并创建 `.venv`。
2. 安装完成后双击 `start.bat`。

### 手动安装

```bash
# 1. 克隆项目
git clone https://github.com/zeng88/m3u8-downloader.git
cd m3u8-downloader

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# 3. 手动启动
.venv/bin/python app.py
```

启动脚本会检查 Python 3.9+、`.venv` 中的 `fastapi`/`uvicorn`/`requests` 和系统 `ffmpeg`。如果缺少依赖，请先运行对应平台的安装脚本。

启动成功后浏览器会自动打开 `http://localhost:8888`。如果 8888 端口已经是本项目服务，启动脚本只会打开已有服务；如果被其他程序占用，脚本会提示释放端口，不会强制结束未知进程。

如需手动安装系统工具：

```bash
# macOS
brew install python ffmpeg

# Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg
```

---

## 一键安装与启动脚本

脚本均位于项目根目录。首次使用先运行安装脚本，之后直接运行启动脚本即可。

| 平台 | 安装依赖 | 启动项目 |
|------|----------|----------|
| macOS 双击 | `install-mac.command` | `start.command` |
| macOS/Linux 终端 | `./install.sh` | `./start.sh` |
| Windows 双击 | `install-windows.bat` | `start.bat` |

### 安装脚本做什么

- macOS/Linux 检查 Python 3.9+ 和 ffmpeg；缺少时尝试使用 Homebrew、apt、dnf 或 pacman 安装。
- Windows 通过 winget 检查/安装 Python 3.12 和 ffmpeg；如果找不到 winget，请先安装 Microsoft Store 中的“应用安装程序（App Installer）”。
- 所有平台都会创建项目根目录 `.venv`，并将 `requirements.txt` 安装到虚拟环境中。
- 安装脚本可以重复运行，已经满足要求的依赖会复用，不会安装到系统全局 Python 环境。

### 启动脚本做什么

- 启动前检查 `.venv`、FastAPI 依赖、Python 版本和 ffmpeg；检查失败时请先重新运行安装脚本。
- 检查 `http://localhost:8888/status`：如果本项目已经运行，只打开浏览器，不重复启动服务。
- 如果 8888 被其他程序占用，会提示释放端口，不会强制终止未知进程。
- 服务就绪后自动打开 `http://localhost:8888`；关闭启动窗口会停止由该窗口启动的服务。

### 常见问题

**macOS 提示“无法打开”或“没有执行权限”**

在终端执行：

```bash
chmod +x install.sh install-mac.command start.sh start.command
```

然后重新运行对应脚本。

**Windows 安装后仍找不到 Python 或 ffmpeg**

关闭当前命令窗口，重新打开项目目录，再运行 `install-windows.bat`。winget 安装程序修改环境变量后，旧窗口通常不会自动刷新。

**启动提示 8888 端口被占用**

先确认是否已有本项目服务；如果不是本项目，请手动关闭占用程序后再启动。macOS/Linux 可执行：

```bash
lsof -nP -iTCP:8888 -sTCP:LISTEN
```

确认占用端口的不是需要保留的服务后，可强制释放 8888 端口，再重新启动：

```bash
lsof -ti:8888 | xargs kill -9
```

---

## 使用说明

### 基本流程

1. **① 输入视频网址** — 粘贴包含视频的页面地址，点击「分析链接」
2. **② 选择 m3u8 链接** — 从检测到的链接列表中选择目标画质
3. **③ 下载配置** — 选择保存目录、填写文件名
4. **④ 执行下载** — 点击「开始下载」一键执行，或「复制命令」手动运行

### 遇到 403 怎么办

部分视频平台的 CDN 会验证请求来源（Referer），直接用 ffmpeg 下载会报 `403 Forbidden`。

解决方法：在③区域的「来源网址」框中填入你打开这个视频的网页地址，工具会自动将其注入 ffmpeg 的 `-referer` 和 `-headers Origin` 参数。**分析链接成功后会自动填入，通常无需手动操作。**

### m3u8 链接找不到怎么办

部分网站的 m3u8 地址由 JavaScript 动态生成，页面 HTML 中不包含，工具无法自动检测。此时：

1. 打开浏览器开发者工具（F12）
2. 切换到 **Network** 标签页
3. 播放视频，过滤 `m3u8`
4. 复制请求 URL，粘贴到③区域直接使用

---

## 项目结构

```
m3u8-downloader/
├── app.py            # 全部源码（FastAPI 后端 + 内嵌前端）
├── requirements.txt  # Python 依赖
├── test_app.py       # 单元测试
├── test_launch_scripts.py # 启动/安装脚本静态测试
├── install.sh        # macOS/Linux 终端安装
├── install-mac.command # macOS 双击安装
├── install-windows.bat  # Windows 双击安装入口
├── install-windows.ps1  # Windows 安装实现
├── start.sh          # macOS/Linux 终端启动
├── start.command     # macOS 双击启动
├── start.bat         # Windows 双击启动入口
├── start-windows.ps1 # Windows 启动实现
└── README.md

```

单文件业务设计，无需构建工具；首次运行使用平台安装脚本，之后可直接使用一键启动脚本。

---

## 架构说明

```
浏览器（localhost:8888）
    │
    ├── GET  /            返回内嵌 HTML/CSS/JS 前端页面
    ├── POST /analyze     requests 抓取页面 → 正则提取 m3u8 链接
    ├── POST /pick-dir    asyncio 子进程启动 tkinter 文件夹选择器
    ├── POST /execute     subprocess.Popen 异步启动 ffmpeg
    ├── GET  /progress    SSE 实时推送 ffmpeg stderr 输出
    ├── POST /stop        终止 ffmpeg 进程
    └── GET  /status      检测 ffmpeg 是否已安装
```

**前端**：纯 HTML/CSS/JS，无框架，无构建步骤，内嵌在 `app.py` 的字符串中。

**进度推送**：使用 [Server-Sent Events (SSE)](https://developer.mozilla.org/zh-CN/docs/Web/API/Server-sent_events)，ffmpeg 退出后推送 `event: done` 事件，前端恢复按钮状态。

**安全设计**：
- ffmpeg 通过参数列表调用（非 `shell=True`），避免命令注入
- 链接渲染使用 `data-url` 属性而非内联 JS 字符串，避免 XSS

---

## ffmpeg 命令参数说明

工具生成的完整命令：

```bash
ffmpeg -threads 0 \
  -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 \
  -user_agent "Mozilla/5.0 ..." \
  [-referer "来源网址" -headers "Origin: 来源域名"] \
  -i "M3U8_URL" \
  -c copy -bsf:a aac_adtstoasc -y \
  "输出路径.mp4"
```

| 参数 | 说明 |
|------|------|
| `-threads 0` | 自动使用全部 CPU 核心 |
| `-reconnect` 系列 | 网络中断自动重连，最多等待 5 秒 |
| `-user_agent` | 伪装浏览器 UA，避免服务端拒绝 |
| `-referer` / `-headers` | 注入来源信息，解决 CDN 防盗链 |
| `-c copy` | 直接封装，不转码，速度最快 |
| `-bsf:a aac_adtstoasc` | 修复 AAC 音频时间戳，保证 MP4 兼容性 |
| `-y` | 输出文件已存在时自动覆盖 |

---

## 运行测试

```bash
python3 -m pip install pytest
python3 -m pytest test_app.py test_launch_scripts.py -v
```

---

## License

MIT
