#!/bin/bash

echo "PostgreSQL 설정 중..."

# PostgreSQL 비밀번호 설정
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'killer99!!';"

# trading_system 데이터베이스 생성
sudo -u postgres psql -c "CREATE DATABASE trading_system;" 2>/dev/null || echo "trading_system DB already exists"

# pg_hba.conf 수정 (비밀번호 인증 활성화)
sudo sed -i 's/peer/md5/g' /etc/postgresql/*/main/pg_hba.conf
sudo sed -i 's/ident/md5/g' /etc/postgresql/*/main/pg_hba.conf

# PostgreSQL 재시작
sudo systemctl restart postgresql

echo "PostgreSQL 설정 완료!"
echo "이제 ./run.sh 를 실행하세요."
