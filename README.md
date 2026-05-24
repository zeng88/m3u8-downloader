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

---

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/zeng88/m3u8-downloader.git
cd m3u8-downloader

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
python app.py
```

启动后浏览器自动打开 `http://localhost:8888`。

> 如果端口被占用，先执行 `lsof -ti:8888 | xargs kill -9` 再重启。

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
└── README.md
```

单文件设计，无需构建工具，`python app.py` 即可运行。

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
pip install pytest
pytest test_app.py -v
```

---

## License

MIT
