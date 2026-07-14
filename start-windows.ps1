$ErrorActionPreference = 'Stop'

# 中文说明：启动器只检查依赖，不强制终止占用 8888 端口的未知程序。
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RootDir '.venv\Scripts\python.exe'
$HealthUrl = 'http://127.0.0.1:8888/status'
$AppUrl = 'http://localhost:8888'

function Fail([string] $Message) {
    Write-Host "`n[错误] $Message" -ForegroundColor Red
    exit 1
}

function Test-PythonPackages([string] $PythonCommand) {
    & $PythonCommand -c 'import fastapi, uvicorn, requests' 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Test-ServiceReady {
    try {
        Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Test-PortOpen([int] $Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync('127.0.0.1', $Port)
        if (-not $task.Wait(500)) { return $false }
        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Open-AppUrl {
    Start-Process $AppUrl | Out-Null
}

Write-Host '========================================================'
Write-Host '                 M3U8 下载助手启动器（Windows）'
Write-Host '========================================================'
Write-Host ''

if (-not (Test-Path $VenvPython)) {
    Fail "未找到项目虚拟环境，请先运行：$RootDir\install-windows.bat"
}
& $VenvPython -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>$null
if ($LASTEXITCODE -ne 0) { Fail '项目虚拟环境中的 Python 版本低于 3.9，请重新运行安装脚本。' }
if (-not (Test-PythonPackages $VenvPython)) {
    Fail "Python 依赖不完整，请先运行：$RootDir\install-windows.bat"
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Fail '未检测到 ffmpeg，请先运行 install-windows.bat。'
}

Write-Host '[检查] 正在检查已有服务...' -ForegroundColor Cyan
if (Test-ServiceReady) {
    Write-Host "[提示] 服务已经运行，正在打开浏览器：$AppUrl" -ForegroundColor Green
    Open-AppUrl
    exit 0
}

if (Test-PortOpen 8888) {
    Fail '8888 端口已被其他程序占用，未强制终止它；请释放端口后重试。'
}

Write-Host '[启动] 正在启动 FastAPI 服务...' -ForegroundColor Cyan
$oldNoBrowser = $env:M3U8_DOWNLOADER_NO_BROWSER
$env:M3U8_DOWNLOADER_NO_BROWSER = '1'
# 中文说明：工作目录已经切到项目根目录，传入相对路径可避免 Windows 路径空格转义问题。
$Process = Start-Process -FilePath $VenvPython -ArgumentList @('app.py') `
    -WorkingDirectory $RootDir -PassThru -NoNewWindow
if ($null -eq $oldNoBrowser) {
    Remove-Item Env:M3U8_DOWNLOADER_NO_BROWSER -ErrorAction SilentlyContinue
} else {
    $env:M3U8_DOWNLOADER_NO_BROWSER = $oldNoBrowser
}

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    if ($Process.HasExited) { Fail '服务进程提前退出，请检查上方 Python 错误信息。' }
    if (Test-ServiceReady) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    Fail '服务在 60 秒内未就绪，请检查上方日志和 Python 依赖。'
}

Write-Host "[完成] 服务已就绪，正在打开浏览器：$AppUrl" -ForegroundColor Green
Open-AppUrl
Write-Host '保持此窗口运行即可使用服务，关闭窗口或按 Ctrl+C 可停止服务。'
Wait-Process -Id $Process.Id -ErrorAction SilentlyContinue
