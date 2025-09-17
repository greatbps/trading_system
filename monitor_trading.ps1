# Trading System Monitoring Script
# Monitors logs, performance, and system health

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("status", "logs", "performance", "health", "all")]
    [string]$Mode = "status",
    
    [Parameter(Mandatory=$false)]
    [int]$Days = 7
)

$LogDir = "D:\trading_system\logs"
$TaskName = "AutoTradingSystem"

function Get-TradingSystemStatus {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Trading System Status Dashboard" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    # Scheduler Status
    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
        
        Write-Host "`n📋 Scheduler Status:" -ForegroundColor Cyan
        Write-Host "  Status: $($task.State)" -ForegroundColor Yellow
        if ($taskInfo.NextRunTime) {
            Write-Host "  Next Run: $($taskInfo.NextRunTime)" -ForegroundColor Yellow
        }
        if ($taskInfo.LastRunTime) {
            Write-Host "  Last Run: $($taskInfo.LastRunTime)" -ForegroundColor Yellow
        }
        
        $resultText = if ($taskInfo.LastTaskResult -eq 0) { "Success ✅" } else { "Failed ($($taskInfo.LastTaskResult)) ❌" }
        Write-Host "  Last Result: $resultText" -ForegroundColor Yellow
        
    } catch {
        Write-Host "❌ Scheduler task not found" -ForegroundColor Red
    }
    
    # Log Files Status
    Write-Host "`n📁 Log Files:" -ForegroundColor Cyan
    if (Test-Path $LogDir) {
        $logFiles = Get-ChildItem -Path $LogDir -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
        foreach ($log in $logFiles) {
            $size = [math]::Round($log.Length / 1KB, 1)
            Write-Host "  $($log.Name) - ${size}KB - $($log.LastWriteTime)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  No log directory found" -ForegroundColor Red
    }
    
    # System Resources
    Write-Host "`n💾 System Resources:" -ForegroundColor Cyan
    $cpu = Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average
    $memory = Get-WmiObject -Class Win32_OperatingSystem
    $memoryUsed = [math]::Round((($memory.TotalVisibleMemorySize - $memory.FreePhysicalMemory) / $memory.TotalVisibleMemorySize) * 100, 1)
    
    Write-Host "  CPU Usage: $([math]::Round($cpu.Average, 1))%" -ForegroundColor Yellow
    Write-Host "  Memory Usage: $memoryUsed%" -ForegroundColor Yellow
    
    # Disk Space
    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='D:'"
    if ($disk) {
        $diskUsed = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 1)
        Write-Host "  Disk Usage (D:): $diskUsed%" -ForegroundColor Yellow
    }
}

function Get-RecentLogs {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Recent Trading Logs (Last $Days days)" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    $cutoffDate = (Get-Date).AddDays(-$Days)
    
    # Auto trading schedule log
    $scheduleLog = "$LogDir\auto_trading_schedule.log"
    if (Test-Path $scheduleLog) {
        Write-Host "`n📋 Schedule Execution Log:" -ForegroundColor Cyan
        Get-Content $scheduleLog | Where-Object { 
            $_ -match '\[(\d{4}-\d{2}-\d{2})' -and [DateTime]::ParseExact($matches[1], 'yyyy-MM-dd', $null) -gt $cutoffDate 
        } | Select-Object -Last 10
    }
    
    # Main trading log
    $tradingLogs = Get-ChildItem -Path $LogDir -Filter "trading_*.log" | 
                   Where-Object { $_.LastWriteTime -gt $cutoffDate } |
                   Sort-Object LastWriteTime -Descending
    
    foreach ($log in $tradingLogs) {
        Write-Host "`n📊 $($log.Name):" -ForegroundColor Cyan
        $content = Get-Content $log.FullName | Select-Object -Last 20
        $errorLines = $content | Where-Object { $_ -match "(ERROR|FAILED|Exception)" }
        $successLines = $content | Where-Object { $_ -match "(SUCCESS|완료|거래)" }
        
        if ($errorLines) {
            Write-Host "  Errors found:" -ForegroundColor Red
            $errorLines | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
        }
        
        if ($successLines) {
            Write-Host "  Recent activities:" -ForegroundColor Green
            $successLines | Select-Object -Last 3 | ForEach-Object { Write-Host "    $_" -ForegroundColor Green }
        }
    }
}

function Get-PerformanceMetrics {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Performance Metrics" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    # Analyze log patterns for performance
    $tradingLogs = Get-ChildItem -Path $LogDir -Filter "trading_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 7
    
    $executionTimes = @()
    $errorCounts = @()
    
    foreach ($log in $tradingLogs) {
        $content = Get-Content $log.FullName
        
        # Count errors
        $errors = ($content | Where-Object { $_ -match "(ERROR|FAILED|Exception)" }).Count
        $errorCounts += $errors
        
        # Extract execution time if logged
        $timePattern = $content | Where-Object { $_ -match "실행.*완료.*(\d+).*초" }
        if ($timePattern) {
            # Extract time from pattern
            $executionTimes += [int]($timePattern -replace '.*(\d+).*초.*', '$1')
        }
    }
    
    Write-Host "`n⏱️ Execution Performance:" -ForegroundColor Cyan
    if ($executionTimes.Count -gt 0) {
        $avgTime = [math]::Round(($executionTimes | Measure-Object -Average).Average, 1)
        $maxTime = ($executionTimes | Measure-Object -Maximum).Maximum
        Write-Host "  Average execution time: ${avgTime}s" -ForegroundColor Yellow
        Write-Host "  Maximum execution time: ${maxTime}s" -ForegroundColor Yellow
    } else {
        Write-Host "  No execution time data available" -ForegroundColor Yellow
    }
    
    Write-Host "`n❌ Error Statistics:" -ForegroundColor Cyan
    if ($errorCounts.Count -gt 0) {
        $avgErrors = [math]::Round(($errorCounts | Measure-Object -Average).Average, 1)
        $totalErrors = ($errorCounts | Measure-Object -Sum).Sum
        Write-Host "  Average errors per run: $avgErrors" -ForegroundColor Yellow
        Write-Host "  Total errors (last $($errorCounts.Count) runs): $totalErrors" -ForegroundColor Yellow
    } else {
        Write-Host "  No error data available" -ForegroundColor Yellow
    }
}

function Get-SystemHealth {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "System Health Check" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    $issues = @()
    
    # Check Python installation
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
    } catch {
        $issues += "Python not found or not accessible"
        Write-Host "❌ Python: Not found" -ForegroundColor Red
    }
    
    # Check main.py exists
    if (Test-Path "D:\trading_system\main.py") {
        Write-Host "✅ main.py: Found" -ForegroundColor Green
    } else {
        $issues += "main.py not found"
        Write-Host "❌ main.py: Not found" -ForegroundColor Red
    }
    
    # Check batch file
    if (Test-Path "D:\trading_system\run_auto_trading.bat") {
        Write-Host "✅ Batch file: Found" -ForegroundColor Green
    } else {
        $issues += "run_auto_trading.bat not found"
        Write-Host "❌ Batch file: Not found" -ForegroundColor Red
    }
    
    # Check log directory
    if (Test-Path $LogDir) {
        Write-Host "✅ Log directory: Found" -ForegroundColor Green
        $logSpace = Get-ChildItem -Path $LogDir -Recurse | Measure-Object -Property Length -Sum
        $logSizeMB = [math]::Round($logSpace.Sum / 1MB, 1)
        Write-Host "  Total log size: ${logSizeMB}MB" -ForegroundColor Yellow
    } else {
        $issues += "Log directory not found"
        Write-Host "❌ Log directory: Not found" -ForegroundColor Red
    }
    
    # Check scheduled task
    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        Write-Host "✅ Scheduled task: Configured" -ForegroundColor Green
    } catch {
        $issues += "Scheduled task not configured"
        Write-Host "❌ Scheduled task: Not found" -ForegroundColor Red
    }
    
    # Summary
    Write-Host "`n🏥 Health Summary:" -ForegroundColor Cyan
    if ($issues.Count -eq 0) {
        Write-Host "  System is healthy ✅" -ForegroundColor Green
    } else {
        Write-Host "  Issues found: $($issues.Count) ⚠️" -ForegroundColor Yellow
        foreach ($issue in $issues) {
            Write-Host "    - $issue" -ForegroundColor Red
        }
    }
}

# Main execution
switch ($Mode) {
    "status" { Get-TradingSystemStatus }
    "logs" { Get-RecentLogs }
    "performance" { Get-PerformanceMetrics }
    "health" { Get-SystemHealth }
    "all" { 
        Get-TradingSystemStatus
        Get-SystemHealth
        Get-PerformanceMetrics
        Get-RecentLogs
    }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Monitoring complete - $(Get-Date)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green