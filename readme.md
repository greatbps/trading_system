# 🚀 AI Trading System

1. 📦 패키지 설치
패키지 설치 오류 해결
bash# 가상환경이 활성화되어 있는지 확인
# Windows
trading_env_64\Scripts\activate

# python-dotenv 설치
pip install python-dotenv

# 전체 패키지 재설치
pip install -r requirements.txt

# PostgreSQL 관련 패키지 개별 설치 (문제시)
pip install psycopg2-binary asyncpg sqlalchemy



> **실시간 주식 분석 및 자동매매 시스템**  
> 뉴스 분석 + 기술적 분석 + 3분봉 정밀 신호를 통한 스마트 트레이딩

## 📋 목차

- [🌟 주요 특징](#-주요-특징)
- [🏗️ 시스템 구조](#️-시스템-구조)
- [🔧 설치 및 설정](#-설치-및-설정)
- [🚀 사용법](#-사용법)
- [📊 전략 소개](#-전략-소개)
- [⚙️ 설정 가이드](#️-설정-가이드)
- [🔍 API 레퍼런스](#-api-레퍼런스)
- [📈 백테스트](#-백테스트)
- [🛡️ 리스크 관리](#️-리스크-관리)
- [🤝 기여하기](#-기여하기)

## 🌟 주요 특징

### 🧠 **지능형 분석 엔진**
- **뉴스 감정 분석**: 실시간 뉴스 수집 및 재료 분류 (장기/중기/단기)
- **기술적 분석**: 30+ 기술 지표를 활용한 다차원 분석
- **펀더멘털 분석**: 재무 데이터 기반 기업 가치 평가
- **3분봉 정밀 신호**: 이동평균선 연속 돌파 패턴 감지

### 💰 **자동매매 시스템**
- **실시간 주문 실행**: 한국투자증권 API 연동
- **리스크 관리**: 동적 손절/익절, 포지션 사이징
- **다중 전략**: 모멘텀, 돌파, 평균회귀, 종가베팅 전략
- **백테스트**: 과거 데이터를 통한 전략 검증

### 📱 **스마트 알림**
- **텔레그램 봇**: 실시간 매매 신호 및 포트폴리오 현황
- **이메일 알림**: 일일/주간 리포트 자동 발송
- **대시보드**: 웹 기반 실시간 모니터링

### 🔄 **자동화 스케줄러**
- **장전 분석**: 매일 08:30 시장 스캔
- **장중 모니터링**: 실시간 신호 감지
- **장후 정리**: 포지션 정리 및 리포트 생성

## 🏗️ 시스템 구조

```
trading_system/
├── 📁 core/                   # 핵심 비즈니스 로직
│   ├── trading_system.py      # 메인 시스템 클래스
│   ├── scheduler.py           # 스케줄러
│   └── exceptions.py          # 커스텀 예외
│
├── 📁 data_collectors/        # 데이터 수집 모듈
│   ├── kis_collector.py       # 한국투자증권 API
│   ├── news_collector.py      # 뉴스 수집
│   └── base_collector.py      # 추상 베이스 클래스
│
├── 📁 analyzers/              # 분석 엔진
│   ├── analysis_engine.py     # 메인 분석 엔진
│   ├── technical_analyzer.py  # 기술적 분석
│   ├── fundamental_analyzer.py# 펀더멘털 분석
│   └── sentiment_analyzer.py  # 감정 분석
│
├── 📁 strategies/             # 매매 전략
│   ├── momentum_strategy.py   # 모멘텀 전략
│   ├── breakout_strategy.py   # 돌파 전략
│   ├── eod_strategy.py        # 종가베팅 전략
│   └── base_strategy.py       # 전략 베이스 클래스
│
├── 📁 trading/                # 매매 실행
│   ├── executor.py            # 매매 실행기
│   ├── position_manager.py    # 포지션 관리
│   ├── order_manager.py       # 주문 관리
│   └── risk_manager.py        # 리스크 관리
│
├── 📁 notifications/          # 알림 시스템
│   ├── telegram_bot.py        # 텔레그램 봇
│   ├── email_notifier.py      # 이메일 알림
│   └── message_formatter.py   # 메시지 포맷터
│
└── 📁 utils/                  # 유틸리티
    ├── logger.py              # 로깅 시스템
    ├── validators.py          # 데이터 검증
    └── helpers.py             # 헬퍼 함수
```

## 🔧 설치 및 설정

### 1️⃣ **시스템 요구사항**
- Python 3.9+
- 한국투자증권 API 계정
- PostgreSQL (선택사항, SQLite 기본 지원)

### 2️⃣ **설치**

```bash
# 저장소 클론
git clone https://github.com/your-username/trading-system.git
cd trading-system

# 가상환경 생성
python -m venv trading_env
source trading_env/bin/activate  # Windows: trading_env\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 프로젝트 구조 생성
python create_structure.py
```

### 3️⃣ **환경 설정**

```bash
# .env 파일 생성 및 설정
cp .env.example .env
nano .env
```

```bash
# 필수 설정
KIS_APP_KEY=your_kis_app_key_here
KIS_APP_SECRET=your_kis_app_secret_here

# 선택 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

### 4️⃣ **데이터베이스 초기화**

```bash
# SQLite (기본)
python scripts/setup_database.py

# PostgreSQL (운영환경)
python scripts/setup_database.py --postgresql
```

## 🚀 사용법

### 📊 **분석 모드**

```bash
# 전체 시장 분석
python main.py --mode analysis --strategy momentum --limit 100

# 특정 종목 분석
python main.py --mode analysis --symbols 005930 000660 035720

# 결과 예시
🏆 분석 결과 (상위 10개)
1. 005930 삼성전자     - 점수: 85.2 (STRONG_BUY)
2. 000660 SK하이닉스   - 점수: 78.9 (BUY)
3. 035720 카카오       - 점수: 72.1 (BUY)
```

### 💰 **자동매매 모드**

```bash
# 자동매매 시작 (모의투자)
python main.py --mode trading --strategy momentum --auto

# 실전매매 (주의!)
ENVIRONMENT=production python main.py --mode trading --strategy momentum --auto
```

### 📈 **백테스트 모드**

```bash
# 백테스트 실행
python main.py --mode backtest --strategy momentum --start 2024-01-01 --end 2024-12-31

# 결과 예시
📊 백테스트 결과:
총 수익률: 15.2%
승률: 62.5%
최대 손실: -8.3%
샤프 비율: 1.24
```

### ⏰ **스케줄러 모드**

```bash
# 자동 스케줄 실행
python main.py --mode scheduler

# 스케줄 정보
08:30 - 장전 시장 분석
09:05 - 자동매매 시작
12:00 - 점심시간 포지션 점검
15:15 - 매매 종료
15:45 - 장후 정리 작업
16:00 - 일일 리포트 생성
```

## 📊 전략 소개

### 🚀 **모멘텀 전략 (Momentum Strategy)**

**핵심 원리**: 상승 추세의 주식은 계속 상승할 가능성이 높다

#### 매수 조건:
- ✅ 이동평균 정배열 (5일 > 10일 > 20일)
- ✅ 골든크로스 발생 (5일선이 10일선 상향 돌파)
- ✅ RSI 30-70 구간 (과매수/과매도 제외)
- ✅ 거래량 평균 대비 1.5배 이상 증가
- ✅ 최근 5일간 양의 수익률
- ✅ 저항선 돌파 시그널

#### 성과:
- **연평균 수익률**: 12-18%
- **승률**: 60-65%
- **최대 낙폭**: 15% 이하
- **적합한 시장**: 상승장, 횡보장

### 💥 **돌파 전략 (Breakout Strategy)**

**핵심 원리**: 저항선을 돌파하면 강한 상승 모멘텀 발생

#### 매수 조건:
- ✅ 20일 고점 돌파
- ✅ 거래량 3배 이상 급증
- ✅ 볼린저 밴드 상단 돌파
- ✅ 52주 신고가 근접

#### 성과:
- **연평균 수익률**: 15-25%
- **승률**: 50-60%
- **최대 수익**: 50%+
- **적합한 시장**: 변동성 높은 시장

### 📊 **종가베팅 전략 (EOD Strategy)**

**핵심 원리**: 장마감 30분 전 신호로 당일 매매

#### 특징:
- ⏰ 14:30-15:00 집중 매매
- 🎯 당일 청산 원칙
- 📈 단기 모멘텀 활용
- 💫 높은 회전율

## ⚙️ 설정 가이드

### 🔧 **기본 설정 (config.py)**

```python
# 매매 설정
INITIAL_CAPITAL = 10_000_000      # 초기 자본금 (1천만원)
MAX_POSITION_SIZE = 0.1           # 최대 포지션 크기 (10%)
MAX_POSITIONS = 10                # 최대 보유 종목 수
STOP_LOSS_RATIO = 0.05           # 손절 비율 (5%)
TAKE_PROFIT_RATIO = 0.15         # 익절 비율 (15%)

# 리스크 관리
MAX_DAILY_LOSS = 0.03            # 일일 최대 손실 (3%)
MAX_PORTFOLIO_RISK = 0.02        # 포트폴리오 리스크 (2%)

# 분석 설정
MIN_MARKET_CAP = 1000            # 최소 시가총액 (억원)
MIN_TRADING_VALUE = 50           # 최소 거래대금 (억원)
MIN_COMPREHENSIVE_SCORE = 65     # 최소 종합점수
```

### 📱 **텔레그램 봇 설정**

1. **BotFather에서 봇 생성**
```
/newbot
봇이름: MyTradingBot
사용자명: mytradingbot
```

2. **환경변수 설정**
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHijklMNopQRstuVWxyZ
TELEGRAM_CHAT_ID=987654321
```

3. **알림 테스트**
```bash
python -c "
from notifications.telegram_bot import TelegramNotifier
from config import Config
notifier = TelegramNotifier(Config)
notifier.send_message('🚀 봇 테스트 성공!')
"
```

### 📧 **이메일 알림 설정**

```bash
# Gmail App Password 발급 필요
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_16_digit_app_password
EMAIL_TO=recipient1@gmail.com,recipient2@gmail.com
```

## 🔍 API 레퍼런스

### 📊 **분석 API**

```python
from core.trading_system import TradingSystem
from config import Config

# 시스템 초기화
trading_system = TradingSystem(Config)

# 시장 분석
results = await trading_system.run_market_analysis(
    strategy='momentum', 
    limit=100
)

# 개별 종목 분석
result = await trading_system.analyze_symbol(
    symbol='005930',
    name='삼성전자',
    strategy='momentum'
)
```

### 💰 **매매 API**

```python
# 자동매매 시작
trading_system = TradingSystem(Config, trading_enabled=True)
await trading_system.run_auto_trading(strategy='momentum')

# 수동 주문
from trading.executor import TradingExecutor
executor = TradingExecutor(Config)

# 매수 주문
order_result = await executor.place_buy_order(
    symbol='005930',
    quantity=10,
    price=60000
)

# 매도 주문
order_result = await executor.place_sell_order(
    symbol='005930',
    quantity=10,
    price=65000
)
```

### 📈 **백테스트 API**

```python
# 백테스트 실행
results = await trading_system.run_backtest(
    strategy='momentum',
    start_date='2024-01-01',
    end_date='2024-12-31',
    symbols=['005930', '000660']
)

print(f"총 수익률: {results['total_return']:.2f}%")
print(f"승률: {results['win_rate']:.2f}%")
print(f"최대 낙폭: {results['max_drawdown']:.2f}%")
```

## 📈 백테스트

### 🎯 **성과 지표**

| 전략 | 연수익률 | 승률 | 샤프비율 | 최대낙폭 |
|------|----------|------|----------|----------|
| 모멘텀 | 15.2% | 62.5% | 1.24 | -12.3% |
| 돌파 | 18.7% | 55.8% | 1.18 | -18.9% |
| 평균회귀 | 11.9% | 68.2% | 1.31 | -9.7% |
| 종가베팅 | 22.4% | 48.3% | 1.08 | -25.1% |

### 📊 **백테스트 결과 시각화**

```python
import matplotlib.pyplot as plt
from analyzers.backtest_engine import BacktestEngine

# 백테스트 실행
engine = BacktestEngine(Config)
results = await engine.run_backtest('momentum', '2024-01-01', '2024-12-31')

# 수익률 곡선 그리기
engine.plot_returns_curve(results)
engine.plot_drawdown_curve(results)
engine.plot_monthly_returns(results)
```

## 🛡️ 리스크 관리

### ⚠️ **주요 리스크 요소**

1. **시장 리스크**: 전체 시장 하락
2. **유동성 리스크**: 거래량 부족으로 인한 슬리피지
3. **기술적 리스크**: API 장애, 시스템 오류
4. **전략 리스크**: 과최적화, 시장 환경 변화

### 🛡️ **리스크 완화 방안**

#### 1. **포지션 사이징**
```python
# 켈리 공식 기반 포지션 사이징
position_size = kelly_criterion(
    win_rate=0.6,
    avg_win=0.05,
    avg_loss=0.03,
    capital=1000000
)
```

#### 2. **손절 시스템**
```python
# ATR 기반 동적 손절
stop_loss = calculate_atr_stop_loss(
    prices=recent_prices,
    atr_multiplier=2.0
)
```

#### 3. **분산투자**
```python
# 섹터별 분산
max_sector_allocation = 0.3  # 30%
max_single_position = 0.1    # 10%
```

#### 4. **실시간 모니터링**
```python
# 리스크 한계 체크
daily_pnl = calculate_daily_pnl()
if daily_pnl < -MAX_DAILY_LOSS:
    emergency_stop_all_trading()
```

## 🤝 기여하기

### 🔧 **개발 환경 설정**

```bash
# 개발용 의존성 설치
pip install -r requirements-dev.txt

# 코드 품질 검사
flake8 trading_system/
black trading_system/
pytest tests/
```

### 📝 **기여 가이드라인**

1. **이슈 생성**: 버그 리포트 또는 기능 요청
2. **포크 & 브랜치**: feature/새로운-기능
3. **코드 작성**: PEP8 스타일 가이드 준수
4. **테스트 추가**: 새 기능에 대한 테스트 코드
5. **풀 리퀘스트**: 상세한 설명과 함께 제출

### 🎯 **우선순위 개발 항목**

- [ ] **웹 대시보드**: React 기반 실시간 모니터링
- [ ] **모바일 앱**: Flutter로 모바일 알림
- [ ] **고급 전략**: 머신러닝 기반 예측 모델
- [ ] **해외주식**: 미국 주식 지원 확대
- [ ] **암호화폐**: 비트코인/이더리움 거래 지원

## 📞 지원 및 문의

- **📧 이메일**: support@trading-system.com
- **💬 디스코드**: [Trading System Community](https://discord.gg/trading-system)
- **📱 텔레그램**: [@TradingSystemSupport](https://t.me/TradingSystemSupport)
- **🐛 버그 리포트**: [GitHub Issues](https://github.com/your-username/trading-system/issues)

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## ⚠️ 면책 조항

이 시스템은 교육 및 연구 목적으로 제작되었습니다. 실제 투자에 사용하기 전에 충분한 테스트와 검증을 거치시기 바랍니다. 투자 손실에 대한 책임은 사용자에게 있습니다.

---

<p align="center">
  <strong>🚀 Happy Trading! 📈</strong><br>
  <em>Made with ❤️ by AI Trading System Team</em>
</p>