# Ubuntu에서 AI Trading System 설정 가이드

## 1. 시스템 요구사항

### 최소 요구사항
- Ubuntu 20.04 LTS 이상
- Python 3.8 이상
- 메모리 4GB 이상 (권장: 8GB)
- 디스크 여유공간 10GB 이상

### 권장 환경
- Ubuntu 22.04 LTS
- Python 3.10
- 메모리 16GB
- SSD 스토리지

## 2. 기본 패키지 설치

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 개발 도구 설치
sudo apt install -y build-essential curl wget git vim

# Python 개발 환경 설치
sudo apt install -y python3 python3-pip python3-venv python3-dev

# 시스템 라이브러리 설치 (matplotlib, numpy 등을 위한)
sudo apt install -y pkg-config libpng-dev libfreetype6-dev
sudo apt install -y libffi-dev libssl-dev
```

## 3. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone https://github.com/greatbps/trading_system.git
cd trading_system

# Python 가상환경 생성
python3 -m venv trading_env
source trading_env/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. requirements.txt 파일 생성

만약 requirements.txt가 없다면 다음 내용으로 생성하세요:

```txt
# 기본 라이브러리
pandas>=1.5.0
numpy>=1.21.0
asyncio-throttle>=1.0.2
aiofiles>=0.8.0

# 데이터베이스
sqlalchemy>=1.4.0
alembic>=1.8.0
asyncpg>=0.27.0

# API 및 웹
fastapi>=0.85.0
uvicorn>=0.18.0
httpx>=0.23.0
websockets>=10.0

# 시각화
matplotlib>=3.5.0
seaborn>=0.11.0
plotly>=5.10.0

# Rich 터미널 UI
rich>=12.0.0

# 머신러닝
scikit-learn>=1.1.0
tensorflow>=2.10.0  # 또는 torch

# 기타
python-dotenv>=0.19.0
schedule>=1.1.0
```

## 5. 환경 설정

```bash
# .env 파일 생성 (예시)
cat > .env << EOF
# 데이터베이스 설정
DATABASE_URL=postgresql://username:password@localhost/trading_db

# API 키 (실제 값으로 교체 필요)
OPENAI_API_KEY=your-openai-api-key-here
KIS_APP_KEY=your-kis-app-key-here
KIS_APP_SECRET=your-kis-app-secret-here

# 거래 설정
TRADING_ENABLED=false
INITIAL_CAPITAL=10000000

# 로깅 설정
LOG_LEVEL=INFO
EOF

# 권한 설정
chmod 600 .env
```

## 6. 데이터베이스 설정 (PostgreSQL)

```bash
# PostgreSQL 설치
sudo apt install -y postgresql postgresql-contrib

# PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 및 사용자 생성
sudo -u postgres psql << EOF
CREATE DATABASE trading_db;
CREATE USER trading_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
\q
EOF

# 데이터베이스 마이그레이션 (있는 경우)
# alembic upgrade head
```

## 7. 시스템 서비스 설정 (선택사항)

자동 실행을 위한 systemd 서비스 파일 생성:

```bash
# 서비스 파일 생성
sudo tee /etc/systemd/system/trading-system.service > /dev/null << EOF
[Unit]
Description=AI Trading System
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/trading_system
Environment=PATH=/home/$USER/trading_system/trading_env/bin
ExecStart=/home/$USER/trading_system/trading_env/bin/python -m core.trading_system
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable trading-system
```

## 8. 실행 및 테스트

### 통합 데모 실행
```bash
# 가상환경 활성화
source trading_env/bin/activate

# 통합 데모 실행
python integration_demo.py
```

### 개별 컴포넌트 테스트
```bash
# 동적 설정 관리자 테스트
python -c "
import asyncio
from core.dynamic_settings_manager import DynamicSettingsManager

async def test():
    manager = DynamicSettingsManager()
    settings, info = await manager.update_balance_and_adjust_settings(
        current_balance=10_000_000,
        cash_balance=3_000_000,
        stock_value=7_000_000
    )
    print(f'조정된 설정: {settings}')

asyncio.run(test())
"
```

### 시각화 테스트
```bash
# 시각화 라이브러리 테스트
python -c "
import matplotlib
matplotlib.use('Agg')  # GUI 없이 실행
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)
plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('Test Plot')
plt.savefig('test_plot.png')
print('✅ 시각화 테스트 성공')
"
```

## 9. 원격 접속 설정 (GUI 필요시)

### X11 포워딩 (SSH)
```bash
# SSH로 접속할 때 X11 포워딩 활성화
ssh -X username@server_ip

# 또는 ~/.ssh/config에 설정
echo "ForwardX11 yes" >> ~/.ssh/config
```

### VNC 서버 설정
```bash
# VNC 서버 설치
sudo apt install -y tightvncserver

# VNC 서버 시작
vncserver :1 -geometry 1920x1080 -depth 24

# 방화벽 설정 (필요한 경우)
sudo ufw allow 5901
```

### 웹 기반 시각화 (권장)
Plotly 대시보드는 웹 브라우저에서 접근 가능하므로 GUI가 필요 없습니다.

## 10. 로그 및 모니터링

### 로그 확인
```bash
# 애플리케이션 로그
tail -f logs/trading_system.log

# 시스템 서비스 로그
sudo journalctl -u trading-system -f
```

### 성능 모니터링
```bash
# 시스템 리소스 확인
htop

# Python 프로세스 확인
ps aux | grep python

# 메모리 사용량 확인
free -h
```

## 11. 자동 시작 스크립트

```bash
# 시작 스크립트 생성
cat > start_trading.sh << 'EOF'
#!/bin/bash
cd /home/$USER/trading_system
source trading_env/bin/activate

echo "🚀 AI Trading System 시작 중..."

# 환경 변수 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. 먼저 환경 설정을 완료하세요."
    exit 1
fi

# 데이터베이스 연결 확인
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('✅ 환경 설정 로드 완료')
"

# 메인 프로그램 실행
python integration_demo.py
EOF

chmod +x start_trading.sh
```

## 12. 문제 해결

### 일반적인 문제들

#### 1. GUI 없음 오류 (matplotlib)
```bash
# Agg 백엔드 강제 사용
export MPLBACKEND=Agg
```

#### 2. 메모리 부족
```bash
# 스왑 파일 생성 (2GB)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 3. 포트 충돌
```bash
# 사용 중인 포트 확인
sudo netstat -tulpn | grep :8000
```

#### 4. 권한 문제
```bash
# 프로젝트 디렉토리 권한 수정
sudo chown -R $USER:$USER /home/$USER/trading_system
```

## 13. 보안 설정

### 방화벽 설정
```bash
# UFW 활성화
sudo ufw enable

# 필요한 포트만 열기
sudo ufw allow ssh
sudo ufw allow 8000  # 웹 대시보드 포트
```

### .env 파일 보안
```bash
# .env 파일 권한 제한
chmod 600 .env

# Git에서 제외 확인
echo ".env" >> .gitignore
```

## 14. 백업 및 복구

### 자동 백업 스크립트
```bash
cat > backup_trading.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/$USER/backups/trading_system"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 설정 파일 백업
cp .env $BACKUP_DIR/.env_$DATE
cp -r data/ $BACKUP_DIR/data_$DATE

# 데이터베이스 백업 (있는 경우)
# pg_dump trading_db > $BACKUP_DIR/db_backup_$DATE.sql

echo "✅ 백업 완료: $BACKUP_DIR"
EOF

chmod +x backup_trading.sh

# 크론탭에 등록 (매일 새벽 2시)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/$USER/trading_system/backup_trading.sh") | crontab -
```

이제 Ubuntu에서 AI Trading System을 완전히 설정하고 실행할 수 있습니다! 🚀