# Auto Trading System Schedule Setup Script
# Must be run as Administrator

Write-Host "========================================" -ForegroundColor Green
Write-Host "Auto Trading System Scheduler Setup" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Task Scheduler configuration
$TaskName = "AutoTradingSystem"
$Description = "Daily automated trading system execution at 08:30"
$ScriptPath = "D:\trading_system\run_auto_trading.bat"

# Remove existing task if exists
try {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
} catch {
    Write-Host "No existing task found. Creating new one." -ForegroundColor Cyan
}

# Create trigger: Daily at 08:30
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:30"

# Create action: Execute batch file
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ScriptPath`""

# Settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Principal: Run as current user
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# Register task
try {
    Register-ScheduledTask -TaskName $TaskName -Description $Description -Trigger $Trigger -Action $Action -Settings $Settings -Principal $Principal
    Write-Host "Task registered successfully!" -ForegroundColor Green
    Write-Host "Schedule: Daily at 08:30" -ForegroundColor Cyan
    Write-Host "Script: $ScriptPath" -ForegroundColor Cyan
    
    # Show registered task info
    Write-Host "`nRegistered task info:" -ForegroundColor Yellow
    Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State, Description
    
} catch {
    Write-Host "Failed to register task: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure you are running as Administrator." -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup complete. Trading will start daily at 08:30." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Manual test option
Write-Host "`nTo test manually, run:" -ForegroundColor Yellow
Write-Host "Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan