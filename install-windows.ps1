$ErrorActionPreference = 'Stop'

# 中文说明：Windows 安装器只把 Python 包安装到项目 .venv，不修改全局 site-packages。
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RootDir '.venv'
$RequirementsFile = Join-Path $RootDir 'requirements.txt'

function Write-Header {
    Write-Host '========================================================' -ForegroundColor Green
    Write-Host '       M3U8 下载助手环境一键安装（Windows）' -ForegroundColor Green
    Write-Host '========================================================' -ForegroundColor Green
}

function Fail([string] $Message) {
    Write-Host "`n[错误] $Message" -ForegroundColor Red
    exit 1
}

function Refresh-ProcessPath {
    # 中文说明：winget 修改 PATH 后，当前 PowerShell 进程不会自动刷新。
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $env:Path = "$userPath;$machinePath"
}

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }

    return $null
}

function Test-PythonSupported([string] $PythonCommand) {
    if (-not $PythonCommand) { return $false }
    try {
        & $PythonCommand -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-PythonPackages([string] $PythonCommand) {
    & $PythonCommand -c 'import fastapi, uvicorn, requests' 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Install-WingetPackage([string] $PackageId, [string] $DisplayName) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail '未找到 winget，请先通过 Microsoft Store 安装“应用安装程序（App Installer）”。'
    }

    Write-Host "正在通过 winget 安装 $DisplayName..." -ForegroundColor Yellow
    & winget install --id $PackageId --exact --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Fail "$DisplayName 安装失败，请检查网络、权限或 winget 输出后重试。"
    }
}

Write-Header
if (-not (Test-Path $RequirementsFile)) { Fail "找不到依赖文件：$RequirementsFile" }

Write-Host '[1/4] 检测 Python 3.9+' -ForegroundColor Cyan
$PythonCommand = Get-PythonCommand
if (-not (Test-PythonSupported $PythonCommand)) {
    Install-WingetPackage 'Python.Python.3.12' 'Python 3.12'
    Refresh-ProcessPath
    $PythonCommand = Get-PythonCommand
}
if (-not (Test-PythonSupported $PythonCommand)) {
    Fail 'Python 安装后仍无法找到 3.9+，请关闭当前窗口并重新运行安装脚本。'
}
Write-Host "[OK] Python：$(& $PythonCommand --version 2>&1)" -ForegroundColor Green

Write-Host '[2/4] 检测 ffmpeg' -ForegroundColor Cyan
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Install-WingetPackage 'Gyan.FFmpeg.Shared' 'ffmpeg'
    Refresh-ProcessPath
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Fail 'ffmpeg 安装后仍无法找到，请关闭当前窗口并重新运行安装脚本。'
}
Write-Host '[OK] ffmpeg 已就绪。' -ForegroundColor Green

Write-Host "[3/4] 创建项目虚拟环境：$VenvDir" -ForegroundColor Cyan
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path $VenvPython)) {
    & $PythonCommand -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Fail '创建虚拟环境失败，请检查 Python 安装。' }
}

Write-Host '[4/4] 安装 Python 依赖，请稍候...' -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Fail '升级 pip 失败，请检查网络连接。' }
& $VenvPython -m pip install -r $RequirementsFile
if ($LASTEXITCODE -ne 0) { Fail '安装 requirements.txt 失败，请检查网络连接。' }
if (-not (Test-PythonPackages $VenvPython)) {
    Fail 'Python 依赖导入失败，请检查 pip 输出并重新运行本安装脚本。'
}

Write-Host "`n[完成] 环境安装成功。" -ForegroundColor Green
Write-Host "现在可以执行：$RootDir\start.bat" -ForegroundColor Green
