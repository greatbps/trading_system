# Phase 1 개발 체크리스트: 진입 신호 품질 개선

## 🎯 목표
- 승률(Win Rate) +5~10%p 개선
- 신호 정밀도(Precision) 향상
- 거짓 신호(False Positive) 30% 감소

## 📂 디렉토리 구조 (준비 완료)

```
signal_processing/           # ✅ 생성됨
├── consensus_engine.py      # 🔄 제미나이 개발 중
├── mtf_analyzer.py         # 🔄 제미나이 개발 중  
├── liquidity_gate.py       # 🔄 제미나이 개발 중
├── news_gate.py            # 🔄 제미나이 개발 중
└── regime_gate.py          # 🔄 제미나이 개발 중

execution/                   # ✅ 생성됨
risk_management/            # ✅ 생성됨  
optimization/               # ✅ 생성됨
```

## 🧠 제미나이 개발 항목

### 1. ConsensusEngine (signal_processing/consensus_engine.py)

**요구사항:**
```python
class ConsensusEngine:
    def __init__(self, strategies: List[str], lookback_days: int = 60):
        # 전략별 최근 정밀도 가중치 계산
        pass
    
    def calculate_consensus_score(self, signals: Dict[str, float]) -> float:
        # w_i = normalize(recent_precision)  
        # score = sum(w_i * signal_i)
        pass
    
    def is_consensus_reached(self, score: float, threshold: float = 2.0) -> bool:
        # consensus = score >= threshold
        pass
```

**테스트 케이스:**
- [ ] 4전략 중 3개 동의 → True
- [ ] 4전략 중 2개 동의 → False  
- [ ] 가중치 적용 검증 (정밀도 높은 전략 우선)
- [ ] 성능: <100ms

### 2. MTFAnalyzer (signal_processing/mtf_analyzer.py)

**요구사항:**
```python
class MTFAnalyzer:
    def __init__(self, timeframes: List[str]):
        # ['3m', '15m', '1h', '1d'] 설정
        pass
    
    def calculate_confluence_score(self, signals: Dict[str, float]) -> float:
        # mtf = 0.1*s_3m + 0.2*s_15m + 0.3*s_1h + 0.4*s_1d
        pass
    
    def is_confluence_met(self, score: float, min_threshold: float = 0.6) -> bool:
        pass
```

**테스트 케이스:**
- [ ] 가중치 계산 정확성 (장기 > 단기)
- [ ] 임계값 검증 (0.6 기준)
- [ ] 성능: <50ms

### 3. LiquidityGate (signal_processing/liquidity_gate.py)

**요구사항:**
```python
class LiquidityGate:
    def __init__(self, atr_min: float, volume_min: int, spread_max: float):
        pass
    
    def evaluate(self, symbol: str, market_data: Dict) -> bool:
        # ATR% 하한, 거래대금 상한/하한, 스프레드 임계 체크
        pass
```

**테스트 케이스:**
- [ ] ATR 2% 이상 → Pass
- [ ] 거래대금 100만 이상 → Pass  
- [ ] 스프레드 0.1% 이하 → Pass
- [ ] 복합 조건 검증

### 4. NewsGate (signal_processing/news_gate.py)

**요구사항:**
```python
class NewsGate:
    def __init__(self, sentiment_threshold: float = -0.5):
        pass
    
    def evaluate(self, symbol: str, news_data: List[Dict]) -> bool:
        # 악성 키워드, 감성점수 체크
        # 공시 이벤트 쿨다운 체크
        pass
```

**테스트 케이스:**
- [ ] 부정 뉴스(-0.8) → Block
- [ ] 중립/긍정 뉴스 → Pass
- [ ] 공시 직후 N분 쿨다운

### 5. RegimeGate (signal_processing/regime_gate.py)

**요구사항:**
```python
class RegimeGate:
    def __init__(self):
        pass
    
    def detect_regime(self, market_data: Dict) -> str:
        # 'TRENDING_UP', 'TRENDING_DOWN', 'SIDEWAYS' 
        pass
    
    def evaluate_strategy_for_regime(self, strategy: str, regime: str) -> float:
        # 레짐별 전략 적합도 (0~1)
        pass
```

**테스트 케이스:**
- [ ] 상승장 → 추세추종 가중 증가
- [ ] 횡보장 → 역추세 가중 증가
- [ ] 급락장 → 관망 모드

## 🧪 테스트 환경 (준비 완료)

### 통합 테스트 (test_phase1_integration.py)
- [x] 테스트 프레임워크 구축
- [x] 모듈별 단위 테스트 준비
- [x] 통합 시나리오 설계
- [x] 성능 벤치마크 기준

### 성능 모니터링 (monitoring/phase1_performance_monitor.py)  
- [x] 실시간 성능 추적
- [x] 임계값 알림 시스템
- [x] 메트릭 수집 및 저장

## ⚡ 성능 목표

| 항목 | 목표 | 측정 방법 |
|------|------|-----------|
| Consensus 계산 | <100ms | phase1_monitor |
| MTF 분석 | <50ms | phase1_monitor |  
| 게이트 평가 | <20ms | phase1_monitor |
| 총 신호 생성 | <200ms | 통합 측정 |
| 메모리 사용량 | <100MB | 프로파일링 |

## 🎯 승률 개선 검증

### Before/After 비교
- [ ] 기존 시스템 성능 기록 (Baseline)
- [ ] Phase 1 적용 후 성능 측정
- [ ] A/B 테스트로 검증 (30일간)

### 핵심 KPI
- [ ] 승률(Win Rate): +5~10%p
- [ ] 신호 정밀도(Precision): +15%  
- [ ] 거짓 신호율(FPR): -30%
- [ ] 기대값(Expectancy): +0.05~0.15

## 🔄 통합 계획

### 기존 시스템 연동
1. **StrategyManager 확장** (strategies/strategy_manager.py)
   - ConsensusEngine 통합
   - 기존 전략 래핑

2. **AnalysisEngine 확장** (analyzers/analysis_engine.py)  
   - MTFAnalyzer 통합
   - 게이트 시스템 연동

3. **DatabaseAutoTrader 업데이트** (trading/db_auto_trader.py)
   - 새로운 신호 체계 적용
   - 성능 모니터링 통합

### 배포 단계
1. **개발 환경 테스트** → 모든 단위/통합 테스트 통과
2. **시뮬레이션 검증** → 과거 데이터로 성능 검증  
3. **소규모 실서비스** → 1-2개 종목으로 검증
4. **전면 적용** → 전체 시스템 업그레이드

## 📝 개발 진행 상황

### 제미나이 개발 현황
- [ ] ConsensusEngine 구현
- [ ] MTFAnalyzer 구현  
- [ ] LiquidityGate 구현
- [ ] NewsGate 구현
- [ ] RegimeGate 구현

### 클로드 관리 현황  
- [x] 디렉토리 구조 준비
- [x] 테스트 환경 구축
- [x] 성능 모니터링 시스템
- [x] 개발 체크리스트
- [ ] 통합 테스트 실행
- [ ] 성능 벤치마크 실행
- [ ] 배포 준비

## 🚨 주의사항

1. **기존 시스템 호환성** 
   - 기존 전략들과 충돌 방지
   - 점진적 통합으로 안정성 확보

2. **성능 저하 방지**
   - 실시간 처리 속도 유지
   - 메모리 사용량 모니터링

3. **백테스팅 검증**
   - 과거 데이터로 충분한 검증 후 적용
   - 실서비스 전 시뮬레이션 필수

---

**담당자:**
- **제미나이**: 핵심 알고리즘 개발 (ConsensusEngine, MTFAnalyzer, Gates)  
- **클로드**: 개발 관리, 테스트, 통합, 성능 모니터링