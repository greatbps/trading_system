# Fix Schedule Timeout Issue
# Increase execution time limit for automated trading

$TaskName = "AutoTradingSystem"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Fixing Schedule Timeout Issue" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

try {
    # Get current task
    $task = Get-ScheduledTask -TaskName $TaskName
    
    # Create new settings with longer timeout
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
        -Priority 4
    
    # Update the task with new settings
    Set-ScheduledTask -TaskName $TaskName -Settings $settings
    
    Write-Host "Task timeout updated successfully!" -ForegroundColor Green
    Write-Host "New execution time limit: 2 hours" -ForegroundColor Cyan
    
    # Show updated task info
    $updatedTask = Get-ScheduledTask -TaskName $TaskName
    Write-Host "Task State: $($updatedTask.State)" -ForegroundColor Yellow
    
} catch {
    Write-Host "Failed to update task: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Schedule fix complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green