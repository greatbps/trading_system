#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/integration

성능 최적화 통합 모듈 - 즉시 실행 권장 (높은 ROI)

이 모듈은 다음과 같은 성능 최적화 기능들을 통합합니다:
- 병렬 처리 개선 (AsyncEngine)
- 성능 모니터링 강화 (PerformanceMonitor)
- API 타임아웃 최적화 (TimeoutOptimizer)

주요 개선 사항:
1. CPU 기반 동적 워커 조정 (최대 16개)
2. 지능형 로드 밸런싱
3. 배치 처리 시스템
4. 실시간 성능 모니터링
5. 예측 알림 시스템
6. 적응형 API 타임아웃
7. 서킷 브레이커 패턴

사용 예시:
```python
from integration import PerformanceIntegrationSystem

# 통합 시스템 초기화 및 시작
system = PerformanceIntegrationSystem()
await system.start()

# 최적화된 작업 실행
result = await system.execute_optimized_operation(
    some_function,
    *args,
    operation_name="important_task"
)

# 최적화된 API 호출
api_result = await system.make_optimized_api_call(
    "current_price",
    method="GET",
    data=request_data
)

# 배치 작업 실행
batch_results = await system.execute_batch_operations([
    {'function': func1, 'args': args1},
    {'function': func2, 'args': args2},
])
```

즉시 실행 권장 이유:
- 30-50% 성능 향상 기대
- API 응답 시간 최적화
- 시스템 안정성 증대
- 리소스 사용 효율화
"""

from .performance_integration import (
    PerformanceIntegrationSystem,
    get_global_performance_system,
    shutdown_global_performance_system
)

__all__ = [
    'PerformanceIntegrationSystem',
    'get_global_performance_system',
    'shutdown_global_performance_system'
]