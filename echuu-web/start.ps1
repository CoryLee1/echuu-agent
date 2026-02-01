# ECHUU Web 控制台 - PowerShell 启动脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ECHUU Web 控制台 - 启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[✓] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[✗] 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 检查 Node.js
try {
    $nodeVersion = node --version
    Write-Host "[✓] Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[✗] 未找到 Node.js，请先安装 Node.js 16+" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[0/3] 检查后端依赖..." -ForegroundColor Yellow
$requirementsPath = Join-Path $PSScriptRoot ".." "requirements.txt"
$requirementsPath = Resolve-Path $requirementsPath -ErrorAction SilentlyContinue

if ($requirementsPath) {
    Write-Host "检测到 requirements.txt，检查依赖..." -ForegroundColor Gray
    # 检查关键依赖是否已安装
    $checkFastAPI = python -c "import fastapi" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] 检测到依赖未安装，正在安装..." -ForegroundColor Yellow
        Write-Host "    这可能需要几分钟时间，请耐心等待..." -ForegroundColor Gray
        pip install -r $requirementsPath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[✗] 依赖安装失败，请检查网络连接和 Python 环境" -ForegroundColor Red
            Write-Host "[提示] 可以手动运行: pip install -r requirements.txt" -ForegroundColor Yellow
            exit 1
        }
        Write-Host "[✓] 依赖安装完成！" -ForegroundColor Green
    } else {
        Write-Host "[✓] 后端依赖已就绪" -ForegroundColor Green
    }
} else {
    Write-Host "[!] 未找到 requirements.txt，跳过依赖检查" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[1/3] 启动后端服务..." -ForegroundColor Yellow
$backendPath = Join-Path $PSScriptRoot "backend"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; python main.py" -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "[2/3] 检查前端依赖..." -ForegroundColor Yellow
$frontendPath = Join-Path $PSScriptRoot "frontend"
$nodeModulesPath = Join-Path $frontendPath "node_modules"

if (-not (Test-Path $nodeModulesPath)) {
    Write-Host "检测到依赖未安装，正在安装..." -ForegroundColor Yellow
    Push-Location $frontendPath
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[✗] 依赖安装失败，请检查网络连接和 Node.js 环境" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host "[✓] 依赖安装完成！" -ForegroundColor Green
    Pop-Location
} else {
    Write-Host "[✓] 依赖已存在，跳过安装" -ForegroundColor Green
}

Write-Host "[3/3] 启动前端服务..." -ForegroundColor Yellow
try {
    # 验证前端目录存在
    if (-not (Test-Path $frontendPath)) {
        Write-Host "[✗] 前端目录不存在: $frontendPath" -ForegroundColor Red
        exit 1
    }
    
    # 验证 package.json 存在
    $packageJson = Join-Path $frontendPath "package.json"
    if (-not (Test-Path $packageJson)) {
        Write-Host "[✗] package.json 不存在" -ForegroundColor Red
        exit 1
    }
    
    # 启动前端（在新窗口中）
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; Write-Host '启动前端开发服务器...' -ForegroundColor Cyan; npm run dev" -WindowStyle Normal
    
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        Write-Host "[✗] 前端启动失败，错误代码: $LASTEXITCODE" -ForegroundColor Red
        Write-Host "[提示] 请手动运行: cd frontend && npm run dev" -ForegroundColor Yellow
    } else {
        Write-Host "[✓] 前端服务已启动（新窗口）" -ForegroundColor Green
    }
} catch {
    Write-Host "[✗] 启动前端时出错: $_" -ForegroundColor Red
    Write-Host "[提示] 请手动运行: cd frontend && npm run dev" -ForegroundColor Yellow
}

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "后端: http://localhost:8000" -ForegroundColor Cyan
Write-Host "前端: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "按任意键关闭此窗口..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
