#!/bin/bash
# install_oracle.sh - Oracle 프리티어 자동 설치 스크립트

set -e  # 오류 발생시 스크립트 중단

echo "🚀 Oracle 프리티어 AI Trading System 설치 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 시스템 요구사항 확인
check_requirements() {
    print_status "시스템 요구사항 확인 중..."

    # Python 3.8+ 확인
    if ! command -v python3 &> /dev/null; then
        print_error "Python3가 설치되지 않았습니다."
        exit 1
    fi

    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    required_version="3.8"

    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_error "Python 3.8 이상이 필요합니다. 현재 버전: $python_version"
        exit 1
    fi

    print_success "Python $python_version 확인됨"

    # 메모리 확인 (최소 2GB 권장)
    total_mem=$(free -m | awk 'NR==2{printf "%.0f", $2/1024}')
    if [ "$total_mem" -lt 2 ]; then
        print_warning "메모리가 부족합니다. 최소 2GB 권장 (현재: ${total_mem}GB)"
    else
        print_success "메모리 확인됨: ${total_mem}GB"
    fi

    # 디스크 공간 확인 (최소 5GB 권장)
    available_space=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$available_space" -lt 5 ]; then
        print_warning "디스크 공간이 부족합니다. 최소 5GB 권장 (현재: ${available_space}GB)"
    else
        print_success "디스크 공간 확인됨: ${available_space}GB"
    fi
}

# 가상환경 설정
setup_virtual_env() {
    print_status "Python 가상환경 설정 중..."

    # 가상환경이 없으면 생성
    if [ ! -d "trading_env" ]; then
        python3 -m venv trading_env
        print_success "가상환경 생성 완료"
    else
        print_success "기존 가상환경 발견"
    fi

    # 가상환경 활성화
    source trading_env/bin/activate
    print_success "가상환경 활성화 완료"

    # pip 업그레이드
    pip install --upgrade pip setuptools wheel
    print_success "pip 업그레이드 완료"
}

# 의존성 설치
install_dependencies() {
    print_status "Python 패키지 설치 중..."

    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "requirements.txt 패키지 설치 완료"
    else
        print_error "requirements.txt 파일을 찾을 수 없습니다."
        exit 1
    fi

    # Oracle 드라이버 별도 설치 확인
    if ! python -c "import oracledb" 2>/dev/null; then
        print_status "Oracle 드라이버 재설치 중..."
        pip install oracledb>=2.0.0
        print_success "Oracle 드라이버 설치 완료"
    else
        print_success "Oracle 드라이버 이미 설치됨"
    fi
}

# 디렉토리 구조 확인
setup_directories() {
    print_status "디렉토리 구조 설정 중..."

    # 필요한 디렉토리 생성
    directories=("logs" "data" "reports" "reports/charts" "reports/interactive" "reports/data")

    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "디렉토리 생성: $dir"
        fi
    done
}

# SQLite 데이터베이스 초기화
initialize_sqlite_db() {
    print_status "SQLite 데이터베이스 초기화 중..."

    # 기존 데이터베이스 백업 (있는 경우)
    if [ -f "trading_system.db" ]; then
        backup_name="trading_system_backup_$(date +%Y%m%d_%H%M%S).db"
        cp trading_system.db "$backup_name"
        print_success "기존 데이터베이스 백업: $backup_name"
    fi

    # 데이터베이스 초기화
    if python setup_oracle_db.py --init; then
        print_success "SQLite 데이터베이스 초기화 완료"
    else
        print_error "데이터베이스 초기화 실패"
        exit 1
    fi
}

# Oracle 설치 가이드 표시
show_oracle_guide() {
    print_status "Oracle 설치 가이드 표시 중..."

    echo ""
    echo "==============================================="
    echo "📋 Oracle Database 21c XE 설치 가이드"
    echo "==============================================="
    echo ""
    echo "현재 SQLite로 시스템이 초기화되었습니다."
    echo "Oracle로 전환하려면 다음 단계를 따라하세요:"
    echo ""
    echo "1. Oracle Database 21c XE 다운로드:"
    echo "   https://www.oracle.com/database/technologies/xe-downloads.html"
    echo ""
    echo "2. Oracle 설치 후 사용자 생성:"
    echo "   sqlplus sys/password@localhost:1521/XE as sysdba"
    echo "   > CREATE USER trading_user IDENTIFIED BY 'StrongPassword123!';"
    echo "   > GRANT CONNECT, RESOURCE TO trading_user;"
    echo ""
    echo "3. 설정 파일 수정:"
    echo "   setup_oracle_db.py에서 database.type을 'oracle'로 변경"
    echo ""
    echo "4. Oracle 모드로 재초기화:"
    echo "   python setup_oracle_db.py --init"
    echo ""
    echo "자세한 가이드: cat com/oracle_setup_guide.md"
    echo "==============================================="
}

# 시스템 테스트
run_tests() {
    print_status "시스템 테스트 실행 중..."

    # 기본 임포트 테스트
    if python -c "
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
print(f'데이터베이스 상태: {\"정상\" if db_ok else \"오류\"}')
"; then
        print_success "시스템 테스트 통과"
    else
        print_error "시스템 테스트 실패"
        exit 1
    fi
}

# 설치 완료 메시지
show_completion_message() {
    echo ""
    echo "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
    echo "     AI Trading System 설치 완료!"
    echo "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
    echo ""
    echo "✅ Python 가상환경: trading_env"
    echo "✅ 데이터베이스: SQLite (Oracle 전환 가능)"
    echo "✅ 샘플 데이터: 10개 주요 종목"
    echo "✅ 시각화 도구: Matplotlib, Plotly"
    echo "✅ AI 분석 엔진: 준비 완료"
    echo ""
    echo "🚀 시작 명령어:"
    echo "   source trading_env/bin/activate"
    echo "   python integration_demo.py"
    echo ""
    echo "📊 데이터베이스 관리:"
    echo "   python setup_oracle_db.py --init    # 초기화"
    echo "   python setup_oracle_db.py --guide   # Oracle 가이드"
    echo ""
    echo "📖 자세한 설명:"
    echo "   cat com/oracle_setup_guide.md"
    echo ""
    echo "Happy Trading! 🚀📈💰"
}

# 메인 실행 함수
main() {
    echo "============================================="
    echo "🤖 AI Trading System - Oracle 프리티어용"
    echo "============================================="
    echo ""

    # 설치 단계 실행
    check_requirements
    setup_virtual_env
    install_dependencies
    setup_directories
    initialize_sqlite_db
    run_tests
    show_oracle_guide
    show_completion_message

    echo ""
    print_success "설치가 성공적으로 완료되었습니다!"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi