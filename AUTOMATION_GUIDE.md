# 🚀 자동화된 거래 시스템 사용 가이드

## 📋 **해결된 문제들**

### ✅ **EOF 에러 완전 해결**
- `input()` 함수 사용 제거
- 비대화형 모드 전용 실행
- stdin 없는 환경에서 안정적 동작

### ✅ **시간대별 정확한 실행**
- 세션별 최적 전략 자동 선택
- 시장 시간 자동 감지
- 스케줄 기반 정시 실행

### ✅ **완전 자동화**
- 사용자 입력 없이 동작
- 백그라운드 실행 지원
- 에러 복구 메커니즘

## 🎯 **새로운 실행 방법**

### **1. 즉시 실행 (테스트용)**
```bash
cd D:\trading_system
python run_trading.py
```

### **2. 스케줄 모드 실행**
```bash
python run_trading.py --schedule
```

### **3. 배치 파일 실행 (Windows)**
```bash
schedule_trading.bat
```

### **4. 데몬 모드 (24시간 자동)**
```bash
python trading_scheduler.py --daemon
```

## 🕐 **자동 실행 스케줄**

| 시간 | 동작 | 전략 |
|------|------|------|
| 08:30 | 시장 점검 | 데이터 확인 |
| 09:00 | 장 시작 | 오프닝 전략 |
| 10:00 | 오전장 | 모멘텀 전략 |
| 12:00 | 점심시간 | 포지션 점검 |
| 14:00 | 오후장 | 오후 전략 |
| 15:30 | 장 마감 | EOD 전략 |
| 17:00 | 시간외 | 일일 정산 |

## 📊 **실행 상태 모니터링**

### **로그 파일 위치**
```
logs/automated_trading_YYYYMMDD.log  # 일일 거래 로그
logs/scheduler_YYYYMMDD.log          # 스케줄러 로그  
logs/batch_execution.log             # 배치 실행 로그
```

### **실시간 모니터링**
```bash
# Windows
tail -f logs\automated_trading_20250911.log

# 실행 상태 확인
tasklist | findstr python
```

## ⚙️ **설정 및 커스터마이징**

### **전략별 실행 조건 수정**
`run_trading.py` 파일에서:
```python
def should_execute_strategy(self, session_info) -> bool:
    # 커스텀 실행 조건 추가
    pass
```

### **포지션 크기 조정**
```python
def calculate_position_size(self, analysis_result):
    # 신뢰도 기반 포지션 사이징
    confidence = analysis_result.get('confidence', 0.7)
    base_position = 100  # 기본값 변경 가능
    return int(base_position * confidence)
```

### **거래 조건 변경**
```python
# 신뢰도 임계값 조정
if signal == 'BUY' and confidence >= 0.7:  # 0.7 → 원하는 값
    await self.execute_buy_order(...)
```

## 🔧 **문제 해결**

### **EOF 에러 발생 시**
1. `run_trading.py` 사용 (기존 main.py 대신)
2. `--schedule` 플래그로 실행
3. 배치 파일 사용

### **거래 미실행 시**
1. 시장 시간 확인: `09:00-15:30`
2. 전략 조건 확인: 신뢰도 >= 0.7
3. 로그 파일 점검: 에러 메시지 확인

### **스케줄러 문제 시**
```bash
# 스케줄러 재시작
python trading_scheduler.py --daemon

# 프로세스 확인
tasklist | findstr python
```

## 🚀 **권장 실행 방법**

### **개발/테스트 환경**
```bash
python run_trading.py
```

### **운영 환경 (추천)**
```bash
python trading_scheduler.py --daemon
```

### **Windows 서비스 등록**
```bash
# 관리자 권한으로 실행
sc create "TradingScheduler" binpath= "python D:\trading_system\trading_scheduler.py --daemon"
sc start "TradingScheduler"
```

## 📈 **성능 모니터링**

### **일일 체크리스트**
- [ ] 스케줄러 정상 동작 확인
- [ ] 로그 파일 에러 점검
- [ ] 거래 실행 현황 확인
- [ ] 포지션 상태 점검
- [ ] 수익/손실 현황 확인

### **주간 체크리스트**
- [ ] 전략 성과 분석
- [ ] 시스템 리소스 점검
- [ ] 로그 파일 정리
- [ ] 설정 최적화 검토

---

## 💡 **핵심 포인트**

1. **기존 시스템은 그대로 유지** - 새로운 자동화 레이어만 추가
2. **EOF 에러 완전 해결** - 비대화형 모드로 100% 동작
3. **시간대별 정확한 실행** - 각 세션에 맞는 전략 자동 실행
4. **완전 자동화** - 설정 후 개입 불필요

**결론**: 이제 거래가 자동으로 실행됩니다! 🎉