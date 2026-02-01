@echo off
chcp 65001 >nul
echo ========================================
echo   ECHUU Web 控制台 - 启动脚本
echo ========================================
echo.

echo [0/3] 检查后端依赖...
cd /d %~dp0..
if exist "requirements.txt" (
    echo 检测到 requirements.txt，检查依赖...
    python -c "import fastapi" >nul 2>&1
    if errorlevel 1 (
        echo [提示] 检测到依赖未安装，正在安装...
        echo       这可能需要几分钟时间，请耐心等待...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [错误] 依赖安装失败，请检查网络连接和 Python 环境
            echo [提示] 可以手动运行: pip install -r requirements.txt
            pause
            exit /b 1
        )
        echo [成功] 依赖安装完成！
    ) else (
        echo [成功] 后端依赖已就绪
    )
) else (
    echo [警告] 未找到 requirements.txt，跳过依赖检查
)

echo.
echo [1/3] 启动后端服务...
cd /d %~dp0
start "ECHUU Backend" cmd /k "cd /d %~dp0backend && python main.py"
timeout /t 3 /nobreak >nul

echo [2/3] 检查前端依赖...
cd /d %~dp0frontend
if not exist "node_modules" (
    echo 检测到依赖未安装，正在安装...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络连接和 Node.js 环境
        pause
        exit /b 1
    )
    echo 依赖安装完成！
) else (
    echo 依赖已存在，跳过安装
)

echo [3/3] 启动前端服务...
if not exist "%~dp0frontend\package.json" (
    echo [错误] 前端目录或 package.json 不存在
    pause
    exit /b 1
)
start "ECHUU Frontend" cmd /k "cd /d %~dp0frontend && echo 启动前端开发服务器... && npm run dev"
if errorlevel 1 (
    echo [警告] 前端启动可能失败，请检查新窗口中的错误信息
    echo [提示] 可以手动运行: cd frontend ^&^& npm run dev
) else (
    echo [成功] 前端服务已启动（新窗口）
)
timeout /t 2 /nobreak >nul

cd /d %~dp0

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo 后端: http://localhost:8000
echo 前端: http://localhost:5173
echo.
echo 按任意键关闭此窗口...
pause >nul
