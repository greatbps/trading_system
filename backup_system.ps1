# Trading System Backup and Recovery Script

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("backup", "restore", "list", "cleanup")]
    [string]$Action = "backup",
    
    [Parameter(Mandatory=$false)]
    [string]$BackupName = "",
    
    [Parameter(Mandatory=$false)]
    [int]$KeepDays = 30
)

$TradingDir = "D:\trading_system"
$BackupDir = "D:\trading_system_backups"
$ConfigFiles = @(
    "main.py",
    "config.py",
    "time_based_strategy_mapper.py",
    "run_auto_trading.bat",
    "*.ps1"
)

function New-TradingBackup {
    param([string]$Name)
    
    if (-not $Name) {
        $Name = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    }
    
    $BackupPath = Join-Path $BackupDir $Name
    
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Creating Trading System Backup" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    # Create backup directory
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    }
    
    if (Test-Path $BackupPath) {
        Write-Host "❌ Backup already exists: $Name" -ForegroundColor Red
        return
    }
    
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    
    # Backup core system files
    Write-Host "`n📁 Backing up core files..." -ForegroundColor Cyan
    foreach ($pattern in $ConfigFiles) {
        $files = Get-ChildItem -Path $TradingDir -Filter $pattern -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            Copy-Item $file.FullName -Destination $BackupPath -Force
            Write-Host "  ✅ $($file.Name)" -ForegroundColor Green
        }
    }
    
    # Backup important directories
    $ImportantDirs = @("core", "analyzers", "strategies", "data_collectors", "precision_analyzer")
    foreach ($dir in $ImportantDirs) {
        $sourcePath = Join-Path $TradingDir $dir
        if (Test-Path $sourcePath) {
            $destPath = Join-Path $BackupPath $dir
            Write-Host "`n📂 Backing up $dir directory..." -ForegroundColor Cyan
            Copy-Item $sourcePath -Destination $destPath -Recurse -Force
            $fileCount = (Get-ChildItem -Path $destPath -Recurse -File).Count
            Write-Host "  ✅ $fileCount files backed up" -ForegroundColor Green
        }
    }
    
    # Backup recent logs (last 7 days)
    $LogDir = Join-Path $TradingDir "logs"
    if (Test-Path $LogDir) {
        Write-Host "`n📋 Backing up recent logs..." -ForegroundColor Cyan
        $BackupLogDir = Join-Path $BackupPath "logs"
        New-Item -ItemType Directory -Path $BackupLogDir -Force | Out-Null
        
        $cutoffDate = (Get-Date).AddDays(-7)
        $recentLogs = Get-ChildItem -Path $LogDir -Filter "*.log" | 
                      Where-Object { $_.LastWriteTime -gt $cutoffDate }
        
        foreach ($log in $recentLogs) {
            Copy-Item $log.FullName -Destination $BackupLogDir -Force
            Write-Host "  ✅ $($log.Name)" -ForegroundColor Green
        }
    }
    
    # Create backup manifest
    $manifest = @{
        BackupName = $Name
        BackupDate = Get-Date
        TradingSystemVersion = "1.0"
        Files = @()
    }
    
    Get-ChildItem -Path $BackupPath -Recurse -File | ForEach-Object {
        $manifest.Files += @{
            Path = $_.FullName.Replace($BackupPath, "")
            Size = $_.Length
            LastModified = $_.LastWriteTime
        }
    }
    
    $manifestPath = Join-Path $BackupPath "backup_manifest.json"
    $manifest | ConvertTo-Json -Depth 3 | Out-File -FilePath $manifestPath -Encoding UTF8
    
    # Calculate backup size
    $backupSize = (Get-ChildItem -Path $BackupPath -Recurse | Measure-Object -Property Length -Sum).Sum
    $backupSizeMB = [math]::Round($backupSize / 1MB, 1)
    
    Write-Host "`n✅ Backup completed successfully!" -ForegroundColor Green
    Write-Host "📍 Location: $BackupPath" -ForegroundColor Yellow
    Write-Host "📊 Size: ${backupSizeMB}MB" -ForegroundColor Yellow
    Write-Host "📁 Files: $($manifest.Files.Count)" -ForegroundColor Yellow
}

function Restore-TradingBackup {
    param([string]$Name)
    
    if (-not $Name) {
        Write-Host "❌ Please specify a backup name to restore" -ForegroundColor Red
        Get-BackupList
        return
    }
    
    $BackupPath = Join-Path $BackupDir $Name
    if (-not (Test-Path $BackupPath)) {
        Write-Host "❌ Backup not found: $Name" -ForegroundColor Red
        return
    }
    
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Restoring Trading System Backup" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "⚠️ WARNING: This will overwrite current files!" -ForegroundColor Yellow
    
    $confirmation = Read-Host "Continue? (y/N)"
    if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
        Write-Host "❌ Restore cancelled" -ForegroundColor Red
        return
    }
    
    # Load manifest
    $manifestPath = Join-Path $BackupPath "backup_manifest.json"
    if (Test-Path $manifestPath) {
        $manifest = Get-Content $manifestPath | ConvertFrom-Json
        Write-Host "`n📋 Backup Info:" -ForegroundColor Cyan
        Write-Host "  Name: $($manifest.BackupName)" -ForegroundColor Yellow
        Write-Host "  Date: $($manifest.BackupDate)" -ForegroundColor Yellow
        Write-Host "  Files: $($manifest.Files.Count)" -ForegroundColor Yellow
    }
    
    # Restore files
    Write-Host "`n🔄 Restoring files..." -ForegroundColor Cyan
    Get-ChildItem -Path $BackupPath -Recurse -File | Where-Object { $_.Name -ne "backup_manifest.json" } | ForEach-Object {
        $relativePath = $_.FullName.Replace($BackupPath, "").TrimStart("\")
        $destPath = Join-Path $TradingDir $relativePath
        $destDir = Split-Path $destPath -Parent
        
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Recurse -Force | Out-Null
        }
        
        Copy-Item $_.FullName -Destination $destPath -Force
        Write-Host "  ✅ $relativePath" -ForegroundColor Green
    }
    
    Write-Host "`n✅ Restore completed successfully!" -ForegroundColor Green
    Write-Host "🔄 Please restart trading system to apply changes" -ForegroundColor Yellow
}

function Get-BackupList {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Available Backups" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    if (-not (Test-Path $BackupDir)) {
        Write-Host "❌ No backup directory found" -ForegroundColor Red
        return
    }
    
    $backups = Get-ChildItem -Path $BackupDir -Directory | Sort-Object Name -Descending
    
    if ($backups.Count -eq 0) {
        Write-Host "❌ No backups found" -ForegroundColor Red
        return
    }
    
    foreach ($backup in $backups) {
        $manifestPath = Join-Path $backup.FullName "backup_manifest.json"
        $size = (Get-ChildItem -Path $backup.FullName -Recurse | Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($size / 1MB, 1)
        
        Write-Host "`n📦 $($backup.Name)" -ForegroundColor Cyan
        Write-Host "  📅 Created: $($backup.CreationTime)" -ForegroundColor Yellow
        Write-Host "  📊 Size: ${sizeMB}MB" -ForegroundColor Yellow
        
        if (Test-Path $manifestPath) {
            $manifest = Get-Content $manifestPath | ConvertFrom-Json
            Write-Host "  📁 Files: $($manifest.Files.Count)" -ForegroundColor Yellow
        }
    }
    
    Write-Host "`nUsage:" -ForegroundColor Green
    Write-Host "  .\backup_system.ps1 restore -BackupName <name>" -ForegroundColor Cyan
}

function Remove-OldBackups {
    param([int]$Days)
    
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Cleaning Old Backups (older than $Days days)" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    if (-not (Test-Path $BackupDir)) {
        Write-Host "❌ No backup directory found" -ForegroundColor Red
        return
    }
    
    $cutoffDate = (Get-Date).AddDays(-$Days)
    $oldBackups = Get-ChildItem -Path $BackupDir -Directory | Where-Object { $_.CreationTime -lt $cutoffDate }
    
    if ($oldBackups.Count -eq 0) {
        Write-Host "✅ No old backups to clean" -ForegroundColor Green
        return
    }
    
    foreach ($backup in $oldBackups) {
        $size = (Get-ChildItem -Path $backup.FullName -Recurse | Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($size / 1MB, 1)
        
        Write-Host "🗑️ Removing: $($backup.Name) (${sizeMB}MB)" -ForegroundColor Yellow
        Remove-Item $backup.FullName -Recurse -Force
    }
    
    Write-Host "`n✅ Cleanup completed: $($oldBackups.Count) backups removed" -ForegroundColor Green
}

# Main execution
switch ($Action) {
    "backup" { New-TradingBackup -Name $BackupName }
    "restore" { Restore-TradingBackup -Name $BackupName }
    "list" { Get-BackupList }
    "cleanup" { Remove-OldBackups -Days $KeepDays }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Backup operation complete - $(Get-Date)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green