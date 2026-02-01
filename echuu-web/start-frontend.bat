@echo off
chcp 65001 >nul
echo ========================================
echo   启动前端服务
echo ========================================
echo.

cd /d %~dp0frontend

if not exist "node_modules" (
    echo [提示] 检测到依赖未安装，正在安装...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [成功] 启动前端开发服务器...
echo 前端地址: http://localhost:5173
echo.

npm run dev

pause
