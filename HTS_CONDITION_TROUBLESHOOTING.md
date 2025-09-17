# HTS 조건식 검색 문제 해결 가이드

## 문제 상황
KIS API를 통한 HTS 조건식 검색에서 "종목코드 오류입니다" 에러가 지속적으로 발생

```
KIS API Error: 종목코드 오류입니다.
❌ 조건식 0 (3분봉 스캘핑 전략) 검색 실패: 잘못된 조건ID 또는 사용자ID
```

## 근본 원인

### 1. HTS 프로그램 미실행
- **문제**: HTS (Home Trading System) 데스크톱 프로그램이 실행되지 않음
- **해결**: 한국투자증권 HTS를 실행하고 로그인 유지

### 2. 조건식 미활성화
- **문제**: HTS에서 조건식이 등록되어 있지만 "실행" 상태가 아님
- **해결**: 각 조건식을 수동으로 "실행" 상태로 변경

### 3. API 권한 문제
- **문제**: 계정에 조건검색 API 사용 권한이 없음
- **해결**: 한국투자증권 고객센터를 통해 API 권한 신청

### 4. 동시 접속 제한
- **문제**: HTS와 API가 동시에 조건검색을 사용할 수 없음
- **해결**: HTS에서 조건검색을 종료하고 API만 사용

## 해결 방법

### 방법 1: HTS 설정 확인 (권장)

1. **HTS 실행 및 로그인**
   ```
   한국투자증권 HTS → 로그인 → 유지
   ```

2. **조건식 활성화**
   ```
   HTS → 조건검색 → 조건식 관리 → 각 조건식 "실행" 클릭
   ```

3. **API 권한 확인**
   ```
   고객센터 1588-0800 → API 서비스 → 조건검색 권한 신청
   ```

### 방법 2: 대안 분석 스크립트 사용 (즉시 해결)

HTS 조건식 문제가 해결될 때까지 대안 스크립트 사용:

```bash
# 인기종목 기반 분석
python fallback_analysis.py

# 수동 종목 리스트 분석
python manual_analysis_test.py
```

### 방법 3: 설정 파일 수정

현재 HTS 조건식 매핑이 정확한지 확인:

```python
# config.py에서 확인
HTS_CONDITION_NAMES = {
    'scalping_3m': '3분봉 스캘핑 전략',        # ID: 0
    'breakout': 'Breakout',                   # ID: 1
    'eod': 'EOD',                            # ID: 2
    'momentum': 'momentum',                   # ID: 3
    'rsi': 'RSI (상대강도지수) 전략',          # ID: 4
    'squeeze_momentum_pro': 'Squeeze Momentum Pro',  # ID: 5
    'supertrend_ema_rsi': 'SuperTrend',      # ID: 6
    'vwap': 'VWAP'                           # ID: 7
}
```

## 테스트 방법

### 1. 조건식 목록 확인
```bash
python debug_hts_conditions.py
```

### 2. 개별 조건식 테스트
```bash
python test_kis_connection_fix.py
```

### 3. 전체 시스템 테스트
```bash
python manual_analysis_test.py
```

## 현재 적용된 우회책

### 1. 에러 처리 개선 ✅
- API 오류와 정상적인 빈 결과를 구분
- 명확한 오류 메시지 제공

### 2. GPT 우선 분석 ✅
- Gemini 타임아웃 문제 해결
- GPT를 1차 분석기로 설정

### 3. 매수 기준 완화 ✅
- 85점 → 78점으로 기준 완화
- 더 많은 매수 기회 제공

### 4. 대안 분석 스크립트 ✅
- `fallback_analysis.py`: 인기종목 기반 분석
- `manual_analysis_test.py`: 수동 종목 리스트 분석

## 권장 사용 방법

### 단기 해결책 (즉시 사용 가능)
```bash
# 인기종목 기반 분석 - 즉시 사용 가능
python fallback_analysis.py
```

### 중장기 해결책 (HTS 설정 완료 후)
```bash
# 정상적인 조건식 기반 분석
python main.py
# → 전략 선택 → 6. 3분봉 스캘핑 전략
```

## 추가 지원

HTS 조건식 설정에 도움이 필요한 경우:
- 한국투자증권 고객센터: 1588-0800
- API 문의: api@truefriend.co.kr
- HTS 사용법: 홈페이지 → 고객지원 → HTS 가이드