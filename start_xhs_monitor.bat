@echo off
chcp 65001 >nul
echo ============================================================
echo 小红书监控器 v2.0
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到 Python
    echo 请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

echo 正在启动小红书监控器...
echo.

REM 启动程序
python main.py --xhs-gui

echo.
echo 程序已退出
pause
