# Oracle 프리티어 설치 및 설정 가이드

## 🚀 빠른 시작

### 1. 수정된 데이터베이스 초기화 명령어
```bash
# 기존 오류 발생 명령어 (사용하지 말것)
# python -c "from database.database_manager import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().initialize_database())"

# ✅ 수정된 명령어 (config 포함)
python setup_oracle_db.py --init
```

### 2. Oracle 연결 설정 가이드 보기
```bash
python setup_oracle_db.py --guide
```

## 📦 단계별 설치 가이드

### Phase 1: SQLite로 임시 실행 (현재 상태)
```bash
# 1. 프로젝트 의존성 설치
pip install -r requirements.txt

# 2. SQLite 데이터베이스 초기화
python setup_oracle_db.py --init

# 3. 시스템 테스트
python -m pytest tests/ -v
```

### Phase 2: Oracle Database 21c XE 설치
```bash
# Ubuntu에서 Oracle XE 설치
sudo apt update
sudo apt install -y wget

# Oracle XE 다운로드 및 설치
wget https://download.oracle.com/otn-pub/otn_software/db-express/oracle-database-xe-21c-1.0-1.ol8.x86_64.rpm
sudo alien -d oracle-database-xe-21c-1.0-1.ol8.x86_64.rpm
sudo dpkg -i oracle-database-xe_21c-2_amd64.deb

# Oracle XE 설정
sudo /etc/init.d/oracle-xe-21c configure
```

### Phase 3: 데이터베이스 사용자 설정
```sql
-- Oracle SQL*Plus에 SYS로 접속
sqlplus sys/your_password@localhost:1521/XE as sysdba

-- 트레이딩 시스템 전용 테이블스페이스 생성
CREATE TABLESPACE trading_tbs
DATAFILE '/opt/oracle/oradata/XE/XEPDB1/trading_tbs.dbf'
SIZE 100M AUTOEXTEND ON NEXT 10M MAXSIZE 1G;

-- 트레이딩 시스템 전용 사용자 생성
CREATE USER trading_user IDENTIFIED BY "StrongPassword123!"
DEFAULT TABLESPACE trading_tbs
QUOTA UNLIMITED ON trading_tbs;

-- 권한 부여
GRANT CONNECT, RESOURCE, CREATE VIEW, CREATE SEQUENCE TO trading_user;
GRANT CREATE SESSION TO trading_user;
GRANT UNLIMITED TABLESPACE TO trading_user;

-- 추가 권한 (필요시)
GRANT CREATE TABLE, CREATE INDEX, CREATE TRIGGER TO trading_user;

exit;
```

### Phase 4: Python Oracle 연결 설정
```bash
# Oracle 클라이언트 드라이버 설치
pip install oracledb

# 연결 테스트
python -c "import oracledb; print('Oracle DB 드라이버 설치 완료')"
```

### Phase 5: 시스템 설정 전환
```python
# setup_oracle_db.py 파일에서 다음 설정 수정:

class OracleConfig:
    def __init__(self):
        # SQLite에서 Oracle로 전환
        self.database = {
            'type': 'oracle',  # 'sqlite'에서 'oracle'로 변경
            'url': self.get_oracle_url(),  # Oracle URL 사용
            'echo': False,
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 3600
        }

        # Oracle 연결 정보 (실제 정보로 수정)
        self.oracle = {
            'host': 'your_oracle_server_ip',  # Oracle 서버 IP
            'port': 1521,
            'service_name': 'XEPDB1',
            'username': 'trading_user',
            'password': 'StrongPassword123!',
            'thick_mode': False
        }
```

### Phase 6: Oracle 모드로 재초기화
```bash
# Oracle 데이터베이스 초기화
python setup_oracle_db.py --init

# 연결 테스트
python -c "
from setup_oracle_db import OracleConfig
from database.database_manager import DatabaseManager
import asyncio

async def test():
    config = OracleConfig()
    db = DatabaseManager(config)
    await db.initialize_database()
    print('Oracle 연결 성공!')

asyncio.run(test())
"
```

## 🔧 트러블슈팅

### 문제 1: "TNS: could not resolve the connect identifier"
```bash
# 해결방법: tnsnames.ora 파일 설정
sudo nano $ORACLE_HOME/network/admin/tnsnames.ora

# 다음 내용 추가:
XE =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = XE)
    )
  )

XEPDB1 =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = XEPDB1)
    )
  )
```

### 문제 2: "ORA-12514: TNS:listener does not currently know of service"
```bash
# 리스너 상태 확인
lsnrctl status

# 리스너 재시작
sudo lsnrctl stop
sudo lsnrctl start

# Oracle 인스턴스 상태 확인
sqlplus / as sysdba
SELECT instance_name, status FROM v$instance;
```

### 문제 3: 메모리 부족 오류
```bash
# Oracle XE 메모리 설정 조정
sqlplus / as sysdba

-- SGA 크기 확인
SHOW PARAMETER sga_target;

-- 메모리 설정 조정 (프리티어 권장: 1GB 이하)
ALTER SYSTEM SET sga_target=800M SCOPE=BOTH;
ALTER SYSTEM SET pga_aggregate_target=200M SCOPE=BOTH;
```

### 문제 4: 포트 충돌
```bash
# 포트 사용 확인
netstat -tlnp | grep 1521

# Oracle 리스너 포트 변경 (필요시)
sudo nano $ORACLE_HOME/network/admin/listener.ora
# PORT = 1521을 다른 포트로 변경
```

## 📊 성능 최적화 (프리티어용)

### Oracle XE 설정 최적화
```sql
-- 프리티어 환경을 위한 최적화 설정
ALTER SYSTEM SET processes=100 SCOPE=SPFILE;
ALTER SYSTEM SET sessions=100 SCOPE=SPFILE;
ALTER SYSTEM SET open_cursors=100 SCOPE=BOTH;

-- 통계 수집 활성화
EXEC DBMS_STATS.GATHER_SCHEMA_STATS('TRADING_USER');

-- 자동 메모리 관리 활성화
ALTER SYSTEM SET memory_target=1G SCOPE=SPFILE;
```

### 인덱스 최적화
```sql
-- 트레이딩 시스템용 인덱스 생성
CREATE INDEX idx_stock_code ON stocks(code);
CREATE INDEX idx_market_data_date ON market_data(date);
CREATE INDEX idx_analysis_result_timestamp ON analysis_results(timestamp);
CREATE INDEX idx_trade_execution_time ON trade_executions(execution_time);
```

## 🔄 마이그레이션 스크립트

### SQLite에서 Oracle로 데이터 마이그레이션
```python
# migration_script.py
import asyncio
import sqlite3
from setup_oracle_db import OracleConfig
from database.database_manager import DatabaseManager

async def migrate_data():
    # SQLite 연결
    sqlite_conn = sqlite3.connect('trading_system.db')

    # Oracle 연결
    oracle_config = OracleConfig()
    oracle_db = DatabaseManager(oracle_config)

    # 데이터 마이그레이션 로직
    # ... (세부 구현)

    print("마이그레이션 완료!")

if __name__ == "__main__":
    asyncio.run(migrate_data())
```

## 📈 모니터링 및 백업

### 자동 백업 스크립트
```bash
#!/bin/bash
# backup_oracle.sh

ORACLE_HOME=/opt/oracle/product/21c/dbhomeXE
BACKUP_DIR=/opt/backups/trading_system
DATE=$(date +%Y%m%d_%H%M%S)

# 디렉토리 생성
mkdir -p $BACKUP_DIR

# 데이터 백업
expdp trading_user/StrongPassword123!@localhost:1521/XEPDB1 \
  directory=BACKUP_DIR \
  dumpfile=trading_backup_$DATE.dmp \
  logfile=trading_backup_$DATE.log

echo "백업 완료: $BACKUP_DIR/trading_backup_$DATE.dmp"
```

### 시스템 모니터링
```sql
-- 세션 모니터링
SELECT username, status, machine, program
FROM v$session
WHERE username = 'TRADING_USER';

-- 테이블스페이스 사용량 모니터링
SELECT tablespace_name,
       ROUND(bytes/1024/1024, 2) AS size_mb,
       ROUND(maxbytes/1024/1024, 2) AS max_size_mb
FROM user_ts_quotas;

-- 성능 통계
SELECT sql_text, executions, elapsed_time
FROM v$sql
WHERE parsing_user_id = (SELECT user_id FROM all_users WHERE username = 'TRADING_USER')
ORDER BY elapsed_time DESC;
```

## 📞 지원 및 문의

### 공식 문서
- [Oracle Database XE 문서](https://docs.oracle.com/en/database/oracle/oracle-database/21/xeinl/index.html)
- [oracledb Python 드라이버](https://python-oracledb.readthedocs.io/)

### 커뮤니티
- [Oracle 개발자 커뮤니티](https://community.oracle.com/)
- [Stack Overflow Oracle 태그](https://stackoverflow.com/questions/tagged/oracle)

---

## ⚡ 빠른 명령어 요약

```bash
# 전체 설치 과정 한번에 실행
# 1. SQLite로 먼저 시작
python setup_oracle_db.py --init

# 2. Oracle 설치 가이드 확인
python setup_oracle_db.py --guide

# 3. Oracle 설치 후 설정 전환
# setup_oracle_db.py 파일의 database.type을 'oracle'로 변경

# 4. Oracle 모드로 재초기화
python setup_oracle_db.py --init
```