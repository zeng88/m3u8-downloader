# M3U8 下载助手一键启动与依赖安装设计

## 目标

为 M3U8 下载助手增加类似 ContextForge 的跨平台一键启动与依赖安装能力，覆盖 Windows、macOS 和 macOS/Linux 终端场景，降低首次使用和日常启动成本。

## 现状

- 项目是单文件 FastAPI 应用，入口为 `app.py`。
- 服务监听 `127.0.0.1:8888`，应用自身会在启动后自动打开浏览器。
- Python 运行依赖记录在 `requirements.txt`。
- `ffmpeg` 是运行下载功能所需的外部命令行依赖。
- 当前项目没有虚拟环境初始化、平台安装脚本或启动前依赖检查。

## 方案

采用分平台入口脚本与平台专用实现：

| 文件 | 作用 |
| --- | --- |
| `start.sh` | macOS/Linux 终端启动入口，负责目录定位、依赖检查、端口检查、服务启动和浏览器打开 |
| `start.command` | macOS 双击入口，调用 `start.sh` 并在结束时保留终端窗口 |
| `start.bat` | Windows 双击入口，调用 PowerShell 启动实现 |
| `start-windows.ps1` | Windows 启动实现，负责依赖检查、端口检查、服务启动和浏览器打开 |
| `install.sh` | macOS/Linux 终端安装入口，负责系统工具检测、虚拟环境创建和 Python 依赖安装 |
| `install-mac.command` | macOS 双击安装入口，调用 `install.sh` |
| `install-windows.bat` | Windows 双击安装入口，调用 PowerShell 安装实现 |
| `install-windows.ps1` | Windows 安装实现，负责 winget、Python、ffmpeg、虚拟环境和 Python 依赖 |

Unix 脚本共用 `install.sh` 建立的 `.venv`。Windows 使用 `.venv\\Scripts\\python.exe`。启动脚本只做检查，不在用户未明确执行安装入口时修改系统环境；检查失败时输出对应安装脚本和手工命令。

## 安装流程

### macOS/Linux

1. 定位项目根目录。
2. 检查 Python 版本是否为 3.9 或更高。
3. macOS 优先使用 Homebrew 检查或安装 `ffmpeg`；Linux 根据可用的 `apt-get`、`dnf` 或 `pacman` 提供自动安装路径，无法自动判断时输出手工命令。
4. 创建项目根目录 `.venv`。
5. 使用虚拟环境 Python 升级 pip，并执行 `pip install -r requirements.txt`。
6. 输出后续启动命令和安装结果。

### Windows

1. 检查 `winget` 是否可用。
2. 检查 Python 3.9+；缺失时使用 winget 安装 Python 3.12。
3. 检查 `ffmpeg`；缺失时使用 winget 安装 `Gyan.FFmpeg.Shared`。
4. 刷新当前 PowerShell 进程的 PATH，并再次验证 Python 与 ffmpeg。
5. 创建 `.venv`，升级 pip，安装 `requirements.txt`。
6. 输出重新打开终端或直接执行启动脚本的提示。

安装脚本可重复执行：已有满足条件的工具和虚拟环境会复用，不重复安装；依赖安装失败立即退出并保留 pip 错误信息。

## 启动流程

1. 进入项目根目录。
2. 检查项目虚拟环境、Python 版本、Python 包和 ffmpeg。
3. 检查 `127.0.0.1:8888` 是否已经有可访问的服务；若已有服务，直接打开浏览器并退出，不重复启动。
4. 启动 `app.py`。
5. 等待服务响应后打开 `http://localhost:8888`；等待超时则输出日志检查建议。
6. 保持启动窗口运行，用户关闭窗口时服务随之结束。

Python 包检查使用虚拟环境 Python 执行实际导入验证（`fastapi`、`uvicorn`、`requests`），避免只检查文件是否存在。浏览器打开优先使用系统 `open`、`xdg-open` 或 Windows `Start-Process`，不可用时只提示访问地址。

## 错误处理

- 找不到 Python：提示运行对应安装脚本或访问 Python 官方安装页面。
- Python 版本过低：显示当前版本和最低要求。
- 找不到包：提示重新运行安装脚本，并显示虚拟环境路径。
- 找不到 ffmpeg：显示平台对应安装命令。
- 端口被其他程序占用但不是本项目：提示释放端口或修改 `app.py` 端口后重试，不强制杀进程。
- 服务启动超时：退出启动等待逻辑，保留服务进程输出，并提示检查 Python/依赖错误。
- Windows 缺少 winget：明确提示通过 Microsoft Store 安装 App Installer，不静默失败。

## 验证

- Shell 脚本执行 `bash -n`。
- Windows 脚本检查 UTF-8、关键命令和入口引用，PowerShell 环境可用时执行解析检查。
- 运行现有 `pytest test_app.py -v`，并记录基线中已存在的测试问题，不把脚本变更与既有业务测试问题混淆。
- 使用临时 PATH 或静态检查覆盖缺少依赖、已有服务和安装入口等分支。
- 更新 README 和 CLAUDE，确保新用户能按平台找到安装与启动方式。

## 非目标

- 不修改 FastAPI 业务接口和页面功能。
- 不自动强制终止占用 8888 端口的未知进程。
- 不引入新的构建系统或第三方启动器。
- 不把 Python 依赖安装到系统全局环境。
