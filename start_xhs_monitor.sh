#!/bin/bash
# 小红书监控器快速启动脚本

echo "============================================================"
echo "小红书监控器 v2.0"
echo "============================================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3"
    exit 1
fi

# 检查依赖
echo "正在检查依赖..."
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  警告：tkinter 未安装"
    echo ""
    echo "macOS 用户请运行：brew install python-tk"
    echo "Linux 用户请运行：sudo apt-get install python3-tk"
    echo ""
    read -p "是否继续？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 启动程序
echo ""
echo "正在启动小红书监控器..."
echo ""

python3 main.py --xhs-gui

echo ""
echo "程序已退出"
