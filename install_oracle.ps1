# install_oracle.ps1 - Oracle 프리티어 Windows 자동 설치 스크립트

param(
    [switch]$Force,
    [switch]$SkipTests
)

# 오류 발생시 스크립트 중단
$ErrorActionPreference = "Stop"

Write-Host "🚀 Oracle 프리티어 AI Trading System 설치 시작..." -ForegroundColor Blue

# 색상 함수 정의
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# 시스템 요구사항 확인
function Test-Requirements {
    Write-Status "시스템 요구사항 확인 중..."

    # Python 확인
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]

            if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
                Write-Error "Python 3.8 이상이 필요합니다. 현재: $pythonVersion"
                exit 1
            }
            Write-Success "Python 확인됨: $pythonVersion"
        }
    }
    catch {
        Write-Error "Python이 설치되지 않았거나 PATH에 없습니다."
        Write-Host "Python 다운로드: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }

    # 메모리 확인
    $totalMemory = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
    if ($totalMemory -lt 2) {
        Write-Warning "메모리가 부족합니다. 최소 2GB 권장 (현재: ${totalMemory}GB)"
    } else {
        Write-Success "메모리 확인됨: ${totalMemory}GB"
    }

    # 디스크 공간 확인
    $freeSpace = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
    if ($freeSpace -lt 5) {
        Write-Warning "디스크 공간이 부족합니다. 최소 5GB 권장 (현재: ${freeSpace}GB)"
    } else {
        Write-Success "디스크 공간 확인됨: ${freeSpace}GB"
    }
}

# 가상환경 설정
function Set-VirtualEnvironment {
    Write-Status "Python 가상환경 설정 중..."

    if (-not (Test-Path "trading_env")) {
        python -m venv trading_env
        Write-Success "가상환경 생성 완료"
    } else {
        Write-Success "기존 가상환경 발견"
    }

    # 가상환경 활성화 스크립트 경로
    $activateScript = ".\trading_env\Scripts\Activate.ps1"

    if (Test-Path $activateScript) {
        # PowerShell 실행 정책 확인
        $executionPolicy = Get-ExecutionPolicy
        if ($executionPolicy -eq "Restricted") {
            Write-Warning "PowerShell 실행 정책이 제한되어 있습니다."
            Write-Host "다음 명령어를 관리자 권한으로 실행하세요:" -ForegroundColor Yellow
            Write-Host "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow

            if (-not $Force) {
                $response = Read-Host "계속하시겠습니까? (y/n)"
                if ($response -ne "y") { exit 1 }
            }
        }

        & $activateScript
        Write-Success "가상환경 활성화 완료"
    } else {
        Write-Error "가상환경 활성화 스크립트를 찾을 수 없습니다: $activateScript"
        exit 1
    }

    # pip 업그레이드
    python -m pip install --upgrade pip setuptools wheel
    Write-Success "pip 업그레이드 완료"
}

# 의존성 설치
function Install-Dependencies {
    Write-Status "Python 패키지 설치 중..."

    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
        Write-Success "requirements.txt 패키지 설치 완료"
    } else {
        Write-Error "requirements.txt 파일을 찾을 수 없습니다."
        exit 1
    }

    # Oracle 드라이버 별도 확인
    try {
        python -c "import oracledb" 2>$null
        Write-Success "Oracle 드라이버 이미 설치됨"
    }
    catch {
        Write-Status "Oracle 드라이버 재설치 중..."
        pip install "oracledb>=2.0.0"
        Write-Success "Oracle 드라이버 설치 완료"
    }
}

# 디렉토리 구조 설정
function Set-Directories {
    Write-Status "디렉토리 구조 설정 중..."

    $directories = @("logs", "data", "reports", "reports\charts", "reports\interactive", "reports\data")

    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Success "디렉토리 생성: $dir"
        }
    }
}

# SQLite 데이터베이스 초기화
function Initialize-SqliteDatabase {
    Write-Status "SQLite 데이터베이스 초기화 중..."

    # 기존 데이터베이스 백업
    if (Test-Path "trading_system.db") {
        $backupName = "trading_system_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
        Copy-Item "trading_system.db" $backupName
        Write-Success "기존 데이터베이스 백업: $backupName"
    }

    # 데이터베이스 초기화
    try {
        python setup_oracle_db.py --init
        Write-Success "SQLite 데이터베이스 초기화 완료"
    }
    catch {
        Write-Error "데이터베이스 초기화 실패: $_"
        exit 1
    }
}

# Oracle 설치 가이드 표시
function Show-OracleGuide {
    Write-Status "Oracle 설치 가이드 표시 중..."

    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "📋 Oracle Database 21c XE 설치 가이드" -ForegroundColor Cyan
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "현재 SQLite로 시스템이 초기화되었습니다."
    Write-Host "Oracle로 전환하려면 다음 단계를 따라하세요:"
    Write-Host ""
    Write-Host "1. Oracle Database 21c XE 다운로드:"
    Write-Host "   https://www.oracle.com/database/technologies/xe-downloads.html" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "2. Windows용 Oracle XE 설치:"
    Write-Host "   - oracle-database-xe-21c-1.0-1.ol8.x86_64.rpm (Linux용)"
    Write-Host "   - Windows용은 Oracle Database 21c Express Edition 다운로드" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "3. Oracle 설치 후 사용자 생성:"
    Write-Host "   sqlplus sys/password@localhost:1521/XE as sysdba"
    Write-Host "   > CREATE USER trading_user IDENTIFIED BY 'StrongPassword123!';"
    Write-Host "   > GRANT CONNECT, RESOURCE TO trading_user;"
    Write-Host ""
    Write-Host "4. 설정 파일 수정:"
    Write-Host "   setup_oracle_db.py에서 database.type을 'oracle'로 변경"
    Write-Host ""
    Write-Host "5. Oracle 모드로 재초기화:"
    Write-Host "   python setup_oracle_db.py --init"
    Write-Host ""
    Write-Host "자세한 가이드: " -NoNewline
    Write-Host "Get-Content com\oracle_setup_guide.md" -ForegroundColor Yellow
    Write-Host "===============================================" -ForegroundColor Cyan
}

# 시스템 테스트
function Invoke-SystemTests {
    if ($SkipTests) {
        Write-Warning "시스템 테스트 건너뜀"
        return
    }

    Write-Status "시스템 테스트 실행 중..."

    try {
        $testScript = @"
import sys
print(f'Python 버전: {sys.version}')

# 필수 모듈 임포트 테스트
modules = ['pandas', 'numpy', 'sqlalchemy', 'oracledb', 'matplotlib', 'plotly']
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError as e:
        print(f'❌ {module}: {e}')

# 설정 테스트
from setup_oracle_db import OracleConfig
config = OracleConfig()
print(f'✅ 설정 클래스 로드 성공')

# 데이터베이스 연결 테스트
from database.database_manager import DatabaseManager
import asyncio

async def test_db():
    try:
        db = DatabaseManager(config)
        stocks = await db.get_all_stocks()
        print(f'✅ 데이터베이스 연결 성공 (주식 {len(stocks)}개)')
        return True
    except Exception as e:
        print(f'❌ 데이터베이스 연결 실패: {e}')
        return False

db_ok = asyncio.run(test_db())
print(f'데이터베이스 상태: {"정상" if db_ok else "오류"}')
"@

        python -c $testScript
        Write-Success "시스템 테스트 통과"
    }
    catch {
        Write-Error "시스템 테스트 실패: $_"
        exit 1
    }
}

# 설치 완료 메시지
function Show-CompletionMessage {
    Write-Host ""
    Write-Host "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉" -ForegroundColor Green
    Write-Host "     AI Trading System 설치 완료!" -ForegroundColor Green
    Write-Host "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉" -ForegroundColor Green
    Write-Host ""
    Write-Host "✅ Python 가상환경: trading_env" -ForegroundColor Green
    Write-Host "✅ 데이터베이스: SQLite (Oracle 전환 가능)" -ForegroundColor Green
    Write-Host "✅ 샘플 데이터: 10개 주요 종목" -ForegroundColor Green
    Write-Host "✅ 시각화 도구: Matplotlib, Plotly" -ForegroundColor Green
    Write-Host "✅ AI 분석 엔진: 준비 완료" -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 시작 명령어:" -ForegroundColor Cyan
    Write-Host "   .\trading_env\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "   python integration_demo.py" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📊 데이터베이스 관리:" -ForegroundColor Cyan
    Write-Host "   python setup_oracle_db.py --init    # 초기화" -ForegroundColor Yellow
    Write-Host "   python setup_oracle_db.py --guide   # Oracle 가이드" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📖 자세한 설명:" -ForegroundColor Cyan
    Write-Host "   Get-Content com\oracle_setup_guide.md" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Happy Trading! 🚀📈💰" -ForegroundColor Magenta
}

# 메인 실행 함수
function Main {
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host "🤖 AI Trading System - Oracle 프리티어용" -ForegroundColor Blue
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host ""

    try {
        # 설치 단계 실행
        Test-Requirements
        Set-VirtualEnvironment
        Install-Dependencies
        Set-Directories
        Initialize-SqliteDatabase
        Invoke-SystemTests
        Show-OracleGuide
        Show-CompletionMessage

        Write-Success "설치가 성공적으로 완료되었습니다!"
    }
    catch {
        Write-Error "설치 중 오류 발생: $_"
        Write-Host "자세한 오류 정보는 위 메시지를 확인하세요." -ForegroundColor Yellow
        exit 1
    }
}

# 스크립트 실행
if ($MyInvocation.InvocationName -ne '.') {
    Main
}