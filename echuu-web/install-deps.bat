@echo off
chcp 65001 >nul
echo ========================================
echo   安装后端依赖
echo ========================================
echo.

cd /d %~dp0..
if not exist "requirements.txt" (
    echo [错误] 未找到 requirements.txt
    echo [提示] 请确保在 echuu-web 目录下运行此脚本
    pause
    exit /b 1
)

echo 找到 requirements.txt
echo.
echo 开始安装依赖...
echo 这可能需要几分钟时间，请耐心等待...
echo.

pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [错误] 依赖安装失败
    echo [提示] 请检查网络连接和 Python 环境
    pause
    exit /b 1
) else (
    echo.
    echo [成功] 依赖安装完成！
)

pause
