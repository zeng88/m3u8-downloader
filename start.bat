@echo off
chcp 65001 >nul
setlocal

REM 中文说明：Windows 双击入口只负责切换目录和调用 PowerShell 启动器。
cd /d "%~dp0"
echo 正在启动 M3U8 下载助手...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1"
if errorlevel 1 (
  echo.
  echo 启动失败，请根据上面的中文提示处理后重试。
  pause
)
endlocal
