#!/bin/bash
# 抖音直播间监控 - 启动配置面板
# 运行此脚本会自动启动 Web 服务并打开浏览器。
# 在浏览器中配置品牌后，切换到 Claude Code 输入「看直播间」开始采集。

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SKILL_DIR/frontend"

echo "🚀 抖音直播间监控 - 配置面板"
echo "================================"
echo ""

# Check Python
PYTHON=""
if command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    echo "❌ 错误: 未找到 python3，请先安装 Python"
    exit 1
fi

# Start server
cd "$FRONTEND_DIR"
echo "📋 正在打开浏览器配置面板..."
echo ""
echo "💡 配置完成后，在 Claude Code 中输入: 看直播间"
echo ""
$PYTHON server.py
