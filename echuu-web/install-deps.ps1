# 安装后端依赖脚本
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  安装后端依赖" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$requirementsPath = Join-Path $PSScriptRoot ".." "requirements.txt"
$requirementsPath = Resolve-Path $requirementsPath -ErrorAction SilentlyContinue

if (-not $requirementsPath) {
    Write-Host "[✗] 未找到 requirements.txt" -ForegroundColor Red
    Write-Host "    请确保在 echuu-web 目录下运行此脚本" -ForegroundColor Yellow
    exit 1
}

Write-Host "找到 requirements.txt: $requirementsPath" -ForegroundColor Green
Write-Host ""
Write-Host "开始安装依赖..." -ForegroundColor Yellow
Write-Host "这可能需要几分钟时间，请耐心等待..." -ForegroundColor Gray
Write-Host ""

pip install -r $requirementsPath

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[✓] 依赖安装完成！" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[✗] 依赖安装失败" -ForegroundColor Red
    Write-Host "    请检查网络连接和 Python 环境" -ForegroundColor Yellow
    exit 1
}
