Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Sunucular Yeniden Baslatiyor" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

Write-Host "`nSunucular durduruluyor..." -ForegroundColor Yellow
& "$PSScriptRoot\stop_servers.ps1"

Write-Host "`n3 saniye bekleniyor..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "`nSunucular baslatiyor..." -ForegroundColor Yellow
& "$PSScriptRoot\start_servers.ps1"
