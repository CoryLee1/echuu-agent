#!/bin/bash

echo "========================================"
echo "  ECHUU Web 控制台 - 启动脚本"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 node"
    exit 1
fi

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: 未找到 npm"
    exit 1
fi

echo "[1/2] 启动后端服务..."
cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

sleep 3

echo "[2/2] 检查前端依赖..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "检测到依赖未安装，正在安装..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请检查网络连接和 Node.js 环境"
        exit 1
    fi
    echo "✅ 依赖安装完成！"
else
    echo "✅ 依赖已存在，跳过安装"
fi

echo "启动前端服务..."
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "  启动完成！"
echo "========================================"
echo ""
echo "后端: http://localhost:8000"
echo "前端: http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止服务..."
echo ""

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
