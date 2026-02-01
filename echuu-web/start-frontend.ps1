# 单独启动前端的脚本
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  启动前端服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$frontendPath = Join-Path $PSScriptRoot "frontend"

if (-not (Test-Path $frontendPath)) {
    Write-Host "[✗] 前端目录不存在: $frontendPath" -ForegroundColor Red
    exit 1
}

Push-Location $frontendPath

# 检查 node_modules
if (-not (Test-Path "node_modules")) {
    Write-Host "[!] 检测到依赖未安装，正在安装..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[✗] 依赖安装失败" -ForegroundColor Red
        Pop-Location
        exit 1
    }
}

Write-Host "[✓] 启动前端开发服务器..." -ForegroundColor Green
Write-Host "前端地址: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""

npm run dev

Pop-Location
