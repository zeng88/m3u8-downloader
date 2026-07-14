@echo off
chcp 65001 >nul
setlocal

REM 中文说明：Windows 双击入口只负责切换目录和调用 PowerShell 安装器。
cd /d "%~dp0"
echo 正在启动 Windows 环境安装器...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1"
if errorlevel 1 (
  echo.
  echo 安装失败，请根据上面的中文提示处理后重试。
  pause
)
endlocal
