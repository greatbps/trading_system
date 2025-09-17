# 자동 거래 시스템 스케줄 관리 스크립트

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("status", "start", "stop", "remove", "test")]
    [string]$Action = "status"
)

$TaskName = "AutoTradingSystem"

Write-Host "========================================" -ForegroundColor Green
Write-Host "자동 거래 시스템 스케줄 관리" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

switch ($Action) {
    "status" {
        Write-Host "📊 현재 스케줄 상태 확인 중..." -ForegroundColor Cyan
        try {
            $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
            Write-Host "✅ 작업이 등록되어 있습니다." -ForegroundColor Green
            Write-Host "상태: $($task.State)" -ForegroundColor Yellow
            
            # 다음 실행 시간 확인
            $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
            if ($taskInfo.NextRunTime) {
                Write-Host "다음 실행 시간: $($taskInfo.NextRunTime)" -ForegroundColor Cyan
            }
            
            # 마지막 실행 결과
            if ($taskInfo.LastTaskResult -eq 0) {
                Write-Host "마지막 실행: 성공 ✅" -ForegroundColor Green
            } elseif ($taskInfo.LastTaskResult -ne $null) {
                Write-Host "마지막 실행: 실패 (코드: $($taskInfo.LastTaskResult)) ❌" -ForegroundColor Red
            }
            
        } catch {
            Write-Host "❌ 작업이 등록되어 있지 않습니다." -ForegroundColor Red
        }
    }
    
    "start" {
        Write-Host "▶️  스케줄 활성화 중..." -ForegroundColor Cyan
        try {
            Enable-ScheduledTask -TaskName $TaskName
            Write-Host "✅ 스케줄이 활성화되었습니다." -ForegroundColor Green
        } catch {
            Write-Host "❌ 스케줄 활성화 실패: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    "stop" {
        Write-Host "⏸️  스케줄 비활성화 중..." -ForegroundColor Cyan
        try {
            Disable-ScheduledTask -TaskName $TaskName
            Write-Host "✅ 스케줄이 비활성화되었습니다." -ForegroundColor Yellow
        } catch {
            Write-Host "❌ 스케줄 비활성화 실패: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    "remove" {
        Write-Host "🗑️  스케줄 제거 중..." -ForegroundColor Yellow
        try {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
            Write-Host "✅ 스케줄이 제거되었습니다." -ForegroundColor Green
        } catch {
            Write-Host "❌ 스케줄 제거 실패: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    "test" {
        Write-Host "🧪 테스트 실행 중..." -ForegroundColor Cyan
        try {
            Start-ScheduledTask -TaskName $TaskName
            Write-Host "✅ 테스트 실행이 시작되었습니다." -ForegroundColor Green
            Write-Host "실행 상태를 확인하려면: .\manage_schedule.ps1 status" -ForegroundColor Yellow
        } catch {
            Write-Host "❌ 테스트 실행 실패: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "`n사용법:" -ForegroundColor Yellow
Write-Host "  .\manage_schedule.ps1 status   - 현재 상태 확인" -ForegroundColor Cyan
Write-Host "  .\manage_schedule.ps1 start    - 스케줄 활성화" -ForegroundColor Cyan
Write-Host "  .\manage_schedule.ps1 stop     - 스케줄 비활성화" -ForegroundColor Cyan
Write-Host "  .\manage_schedule.ps1 test     - 수동 테스트 실행" -ForegroundColor Cyan
Write-Host "  .\manage_schedule.ps1 remove   - 스케줄 완전 제거" -ForegroundColor Cyan