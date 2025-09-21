# 매매 분석 성능 최적화 가이드

## 개요

24개 종목 매매 분석의 성능을 최적화하고 자동으로 병렬 처리를 적용하는 시스템입니다.

## 주요 기능

### 1. 실시간 성능 측정
- 각 종목 분석 시간 추적
- 전체 사이클 시간 모니터링
- 메모리 사용량 감시

### 2. 자동 최적화
- 병렬 처리 자동 활성화/비활성화
- 최적 갱신 주기 자동 계산
- 동시 분석 수 자동 조정

### 3. 성능 등급 시스템
- A~F 등급으로 성능 평가
- 실시간 성능 상태 모니터링
- 최적화 제안 자동 생성

## 사용 방법

### 기본 사용
```python
# 자동매매 시스템에서 자동으로 작동
# 10회 사이클마다 성능 분석 및 최적화 실행
```

### 수동 성능 분석
```python
# 현재 성능 확인
metrics = trader.calculate_performance_metrics()
print(f"평균 분석 시간: {metrics['avg_analysis_time']:.2f}초")
print(f"병렬 처리 권장: {metrics['parallel_recommended']}")

# 최적 감시 종목 수 확인
optimal = trader.get_optimal_monitoring_count()
print(f"권장 종목 수: {optimal['recommended_count']}개")
print(f"최대 안전 종목 수: {optimal['max_safe_count']}개")
```

### 성능 최적화 강제 실행
```python
# 즉시 최적화 적용
result = await trader.optimize_monitoring_performance()
print(f"적용된 최적화: {result['optimizations_applied']}")
```

### 종합 성능 리포트
```python
# 상세 성능 리포트 생성
report = trader.get_performance_report()
print(f"성능 등급: {report['performance_grade']}")
print(f"권장사항: {report['recommendations']}")
```

## 성능 최적화 테스트

```bash
# 성능 테스트 실행
python test_performance_optimization.py
```

### 테스트 스크립트 사용 예시
```python
from test_performance_optimization import PerformanceTester

# 실제 매매 시스템 연결 후
tester = PerformanceTester(db_auto_trader)
result = await tester.run_performance_test()
```

## 성능 기준

### 분석 시간 목표
- **우수**: 종목당 1초 이하
- **양호**: 종목당 2초 이하
- **보통**: 종목당 3초 이하
- **개선 필요**: 종목당 4초 이상

### 권장 종목 수
- **순차 처리**: 15개 이하
- **병렬 처리**: 30개 이하
- **최대 한계**: 40개

### 갱신 주기
- **빠른 분석**: 15-20초
- **표준**: 25-35초
- **안정성 우선**: 40-60초

## 자동 최적화 로직

### 병렬 처리 활성화 조건
1. 평균 분석 시간 > 2초 OR
2. 감시 종목 수 > 10개

### 갱신 주기 계산
```python
# 병렬 처리시
estimated_time = max_analysis_time + (total_stocks / workers) * 0.5
optimal_interval = max(15, estimated_time * 1.5)

# 순차 처리시
total_time = sum(analysis_times)
optimal_interval = max(20, total_time * 1.2)
```

### 동시 분석 수 조정
```python
if total_stocks > 15:
    max_concurrent = min(12, total_stocks // 2)
```

## 성능 등급 평가

### 평가 기준 (총 100점)
- **분석 시간** (40점): 빠를수록 높은 점수
- **병렬 처리 효율성** (30점): 적절한 병렬 처리 활용
- **갱신 주기 적정성** (20점): 최적 주기와의 차이
- **전체 처리 시간** (10점): 제한 시간 내 완료

### 등급 기준
- **A급**: 90점 이상 - 최적화 상태
- **B급**: 80-89점 - 양호한 성능
- **C급**: 70-79점 - 보통 성능
- **D급**: 60-69점 - 개선 필요
- **F급**: 60점 미만 - 즉시 최적화 필요

## 문제 해결

### 자주 발생하는 문제

#### 1. 분석 시간이 너무 느림
**증상**: 종목당 4초 이상 소요
**해결책**:
- 네트워크 연결 상태 확인
- API 호출 제한 확인
- 타임아웃 설정 검토

#### 2. 병렬 처리가 활성화되지 않음
**증상**: 10개 이상 종목인데 순차 처리
**해결책**:
```python
trader.adjust_monitoring_settings(force_parallel=True)
```

#### 3. 메모리 사용량 증가
**증상**: 성능 데이터 누적으로 메모리 사용량 증가
**해결책**: 자동으로 최근 데이터만 유지 (최근 100개)

#### 4. 갱신 주기가 너무 길어짐
**증상**: 60초 이상의 긴 갱신 주기
**해결책**:
- 감시 종목 수 줄이기
- 병렬 처리 활성화
- 타임아웃 시간 단축

### 로그 메시지 해석

```
📈 성능 분석 결과:
   평균 종목당 분석 시간: 2.35초
   전체 분석 시간: 56.40초
   병렬 처리 권장: Yes
   최적 갱신 주기: 25초
```

**해석**:
- 현재 24개 종목 분석에 56초 소요
- 병렬 처리로 25초 주기로 최적화 가능
- 성능 개선 여지 있음

## 모니터링 권장사항

1. **정기적인 성능 체크**: 일주일에 한 번 성능 리포트 확인
2. **종목 수 관리**: 성능에 맞춰 감시 종목 수 조정
3. **시장 상황 고려**: 변동성이 큰 시기에는 더 자주 분석
4. **시스템 리소스 모니터링**: CPU, 메모리, 네트워크 상태 확인

## 추가 최적화 옵션

### 고급 설정
```python
# 워커 수 조정
trader.optimal_workers = 6

# 최대 동시 분석 수 조정
trader.max_concurrent_analysis = 10

# 타임아웃 시간 조정 (개별 종목)
# _analyze_stock_by_id 메서드에서 timeout 값 변경
```

### 실험적 기능
- 적응형 타임아웃: 종목별 평균 분석 시간에 따른 동적 타임아웃
- 우선순위 분석: 중요 종목 우선 분석
- 캐싱 최적화: 분석 결과 일시 캐싱

이 가이드를 통해 24개 종목의 매매 분석을 효율적으로 최적화할 수 있습니다.