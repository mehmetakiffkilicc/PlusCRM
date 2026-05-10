Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Sunucular Durduruluyor" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

Write-Host "`nPython ve Node.js processleri durduruluyor..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Stop-Process -Name node -Force -ErrorAction SilentlyContinue

Write-Host "Port 5000 ve 3002 temizleniyor..." -ForegroundColor Yellow
$port5000 = (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess
$port3002 = (Get-NetTCPConnection -LocalPort 3002 -ErrorAction SilentlyContinue).OwningProcess
if($port5000) { Stop-Process -Id $port5000 -Force -ErrorAction SilentlyContinue }
if($port3002) { Stop-Process -Id $port3002 -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 2

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "  Sunucular durduruldu!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
