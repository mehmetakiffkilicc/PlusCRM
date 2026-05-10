Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Backend ve Frontend Baslatiyor" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Port temizleme
Write-Host "`nPort 5000 ve 3002 temizleniyor..." -ForegroundColor Yellow
$port5000 = (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess
$port3002 = (Get-NetTCPConnection -LocalPort 3002 -ErrorAction SilentlyContinue).OwningProcess
if($port5000) { Stop-Process -Id $port5000 -Force -ErrorAction SilentlyContinue }
if($port3002) { Stop-Process -Id $port3002 -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# Backend baslat
Write-Host "`nBackend baslatiyor (Port 5000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; .\.venv\Scripts\Activate.ps1; cd backend; python manage.py runserver 5000"
Start-Sleep -Seconds 3

# Frontend baslat
Write-Host "Frontend baslatiyor (Port 3001)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "  Sunucular baslatildi!" -ForegroundColor Green
Write-Host "  Backend: http://localhost:5000" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3002" -ForegroundColor White
Write-Host "================================" -ForegroundColor Cyan
