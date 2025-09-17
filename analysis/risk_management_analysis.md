# 🛡️ 리스크 관리 시스템 분석

> 자동매매 시스템의 현재 리스크 관리 수준과 개선 방향

## 📊 현재 리스크 관리 구조 분석

### 1. 정적 리스크 설정 (config.py)

#### 현재 설정 코드
```python
class TradingConfig:
    # 리스크 관리 - 모든 값이 고정
    STOP_LOSS_RATIO = 0.05      # 5% 손절 (고정)
    TAKE_PROFIT_RATIO = 0.10    # 10% 익절 (고정)
    MAX_POSITIONS = 5           # 최대 동시 보유 종목수 (고정)
    
    # 포지션 크기
    MAX_POSITION_SIZE = 0.1     # 최대 포지션 크기 10% (고정)
    INITIAL_CAPITAL = 10000000  # 초기 자본금 1천만원
    
    # 일일 손실 제한
    MAX_DAILY_LOSS = 0.03       # 일일 최대 손실률 3% (고정)

class RiskConfig:
    MAX_DAILY_LOSS = 500000     # 일일 최대 손실 50만원 (고정)
    MAX_POSITION_LOSS = 200000  # 포지션별 최대 손실 20만원 (고정)
    DEFAULT_STOP_LOSS_PCT = 5.0 # 기본 손절매 비율 5% (고정)
```

#### 🔴 핵심 문제점들

1. **변동성 무시**: 모든 종목에 동일한 5% 손절률 적용
   - 삼성전자(안정주): 5% 손절 → 과도한 손절
   - 바이오주(고변동): 5% 손절 → 불충분한 보호

2. **시장 상황 무시**: 상승장/하락장/횡보장 구분 없음
   - 하락장에서도 10% 익절 목표 → 비현실적
   - 상승장에서 5% 손절 → 너무 보수적

3. **포지션 크기 경직성**: 신호 강도와 무관하게 동일 크기

### 2. AutoTrader의 리스크 적용 로직

#### 매수 시 리스크 설정 (auto_trader.py:368-371)
```python
# 손절가/목표가 설정 - 문제가 많은 코드
stop_loss_price = int(current_price * (1 - self.stop_loss_pct))  # 무조건 5% 하락
target_price = int(current_price * (1 + self.take_profit_pct))   # 무조건 10% 상승
```

#### 보유종목 매도 조건 (auto_trader.py:571-609)
```python
def _determine_sell_signal_for_holding(self, conditions, stock):
    # 손절 조건 - 단순 가격 비교만
    if stock.current_price <= stock.stop_loss_price:
        sell_signals.append("손절가도달")
    
    # 익절 조건 - 고정 비율만 사용
    if stock.current_price >= avg_price * (1 + self.take_profit_pct):
        sell_signals.append("익절목표달성")
```

#### 🔴 치명적 문제점들

1. **트레일링 스탑 부재**: 수익이 나도 손절가 고정
2. **부분 매도 부재**: 전량 매도만 가능
3. **시간 기반 관리 부재**: 장기 보유 종목도 동일한 기준
4. **변동성 기반 조정 없음**: ATR, 볼린저 밴드 등 미활용

---

## 🎯 고급 리스크 관리 시스템 설계

### 1. 변동성 기반 동적 손절 시스템

```python
class AdvancedRiskManager:
    def __init__(self):
        self.atr_period = 14  # ATR 계산 기간
        self.volatility_multiplier = 2.0  # 변동성 배수
    
    def calculate_dynamic_stop_loss(self, symbol: str, entry_price: float, 
                                  historical_data: List[Dict]) -> float:
        """변동성 기반 동적 손절가 계산"""
        
        # ATR (Average True Range) 계산
        atr = self.calculate_atr(historical_data)
        
        # 기본 손절가 계산 (ATR * 승수)
        atr_stop_distance = atr * self.volatility_multiplier
        basic_stop = entry_price - atr_stop_distance
        
        # 최소/최대 손절 비율 제한
        min_stop_pct = 0.02  # 최소 2%
        max_stop_pct = 0.08  # 최대 8%
        
        min_stop_price = entry_price * (1 - max_stop_pct)
        max_stop_price = entry_price * (1 - min_stop_pct)
        
        # 범위 내로 조정
        dynamic_stop = max(min_stop_price, min(basic_stop, max_stop_price))
        
        return dynamic_stop
    
    def calculate_atr(self, price_data: List[Dict]) -> float:
        """ATR (Average True Range) 계산"""
        true_ranges = []
        
        for i in range(1, len(price_data)):
            current = price_data[i]
            prev = price_data[i-1]
            
            high_low = current['high'] - current['low']
            high_close = abs(current['high'] - prev['close'])
            low_close = abs(current['low'] - prev['close'])
            
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        
        return sum(true_ranges[-self.atr_period:]) / self.atr_period
```

### 2. 트레일링 스탑 시스템

```python
class TrailingStopManager:
    def __init__(self):
        self.trailing_stops = {}  # 종목별 트레일링 스탑 저장
    
    def update_trailing_stop(self, symbol: str, current_price: float, 
                           entry_price: float, trail_percent: float = 0.03) -> float:
        """트레일링 스탑 업데이트"""
        
        if symbol not in self.trailing_stops:
            # 초기 손절가 설정
            initial_stop = entry_price * (1 - trail_percent * 2)  # 첫 손절가는 더 넓게
            self.trailing_stops[symbol] = {
                'stop_price': initial_stop,
                'highest_price': current_price,
                'trail_percent': trail_percent
            }
            return initial_stop
        
        stop_data = self.trailing_stops[symbol]
        
        # 최고가 갱신 확인
        if current_price > stop_data['highest_price']:
            stop_data['highest_price'] = current_price
            
            # 새로운 트레일링 스탑 계산
            new_stop = current_price * (1 - trail_percent)
            
            # 손절가는 상승만 가능 (하락 불가)
            if new_stop > stop_data['stop_price']:
                stop_data['stop_price'] = new_stop
        
        return stop_data['stop_price']
```

### 3. 포지션 크기 동적 조정 시스템

```python
class PositionSizeManager:
    def __init__(self, initial_capital: float):
        self.capital = initial_capital
        self.max_risk_per_trade = 0.02  # 거래당 최대 위험 2%
    
    def calculate_position_size(self, signal_strength: float, entry_price: float, 
                              stop_loss_price: float, volatility_score: float) -> int:
        """신호 강도와 위험도 기반 포지션 크기 계산"""
        
        # 거래당 위험 금액
        risk_amount = self.capital * self.max_risk_per_trade
        
        # 1주당 위험 금액
        risk_per_share = entry_price - stop_loss_price
        
        if risk_per_share <= 0:
            return 0
        
        # 기본 포지션 크기
        basic_position = risk_amount / risk_per_share
        
        # 신호 강도 조정 (0.5 ~ 1.5 배수)
        signal_multiplier = 0.5 + (signal_strength * 1.0)  # signal_strength: 0~1
        
        # 변동성 조정 (고변동성일수록 축소)
        volatility_multiplier = 1 / (1 + volatility_score)  # volatility_score: 0~1
        
        # 최종 포지션 크기
        final_position = int(basic_position * signal_multiplier * volatility_multiplier)
        
        # 최대 포지션 제한
        max_position_value = self.capital * 0.15  # 자본의 15%까지
        max_shares = int(max_position_value / entry_price)
        
        return min(final_position, max_shares)
```

### 4. 다단계 익절 시스템

```python
class TakeProfitManager:
    def __init__(self):
        self.profit_levels = [
            {'threshold': 0.05, 'sell_ratio': 0.3},  # 5% 수익 시 30% 매도
            {'threshold': 0.10, 'sell_ratio': 0.4},  # 10% 수익 시 40% 매도
            {'threshold': 0.20, 'sell_ratio': 0.3},  # 20% 수익 시 나머지 매도
        ]
    
    def check_take_profit(self, symbol: str, current_price: float, 
                         entry_price: float, current_quantity: int) -> Dict:
        """다단계 익절 체크"""
        
        profit_rate = (current_price - entry_price) / entry_price
        
        for level in self.profit_levels:
            if profit_rate >= level['threshold']:
                sell_quantity = int(current_quantity * level['sell_ratio'])
                
                if sell_quantity > 0:
                    return {
                        'action': 'partial_sell',
                        'quantity': sell_quantity,
                        'reason': f"{level['threshold']*100}% 익절 목표 달성",
                        'remaining_quantity': current_quantity - sell_quantity
                    }
        
        return {'action': 'hold'}
```

### 5. 시장 상황별 리스크 조정

```python
class MarketRegimeRiskAdjuster:
    def __init__(self):
        self.risk_adjustments = {
            'bull_market': {
                'stop_loss_multiplier': 0.8,    # 손절 더 넓게
                'take_profit_multiplier': 1.3,  # 익절 더 넓게
                'position_size_multiplier': 1.2  # 포지션 더 크게
            },
            'bear_market': {
                'stop_loss_multiplier': 1.3,    # 손절 더 타이트하게
                'take_profit_multiplier': 0.7,  # 익절 더 빠르게
                'position_size_multiplier': 0.6  # 포지션 더 작게
            },
            'sideways': {
                'stop_loss_multiplier': 1.0,    # 기본값
                'take_profit_multiplier': 1.0,  # 기본값
                'position_size_multiplier': 1.0  # 기본값
            }
        }
    
    def get_adjusted_risk_params(self, market_regime: str, base_params: Dict) -> Dict:
        """시장 상황별 리스크 파라미터 조정"""
        
        adjustments = self.risk_adjustments.get(market_regime, self.risk_adjustments['sideways'])
        
        return {
            'stop_loss_pct': base_params['stop_loss_pct'] * adjustments['stop_loss_multiplier'],
            'take_profit_pct': base_params['take_profit_pct'] * adjustments['take_profit_multiplier'],
            'position_size': base_params['position_size'] * adjustments['position_size_multiplier']
        }
```

---

## ⚡ 통합 리스크 관리 시스템

### 실시간 리스크 모니터링

```python
class IntegratedRiskManager:
    def __init__(self, config):
        self.config = config
        self.atr_risk = AdvancedRiskManager()
        self.trailing_stop = TrailingStopManager()
        self.position_size = PositionSizeManager(config.INITIAL_CAPITAL)
        self.take_profit = TakeProfitManager()
        self.market_adjuster = MarketRegimeRiskAdjuster()
        
        # 실시간 모니터링
        self.current_drawdown = 0.0
        self.max_daily_loss = config.risk.MAX_DAILY_LOSS
        self.total_risk_exposure = 0.0
    
    async def evaluate_trade_risk(self, trade_signal: Dict, market_data: Dict) -> Dict:
        """거래 위험도 종합 평가"""
        
        # 1. 현재 시장 상황 분석
        market_regime = self.detect_market_regime(market_data)
        
        # 2. 변동성 기반 손절가 계산
        stop_loss = self.atr_risk.calculate_dynamic_stop_loss(
            trade_signal['symbol'], 
            trade_signal['entry_price'], 
            market_data['historical_data']
        )
        
        # 3. 포지션 크기 계산
        position_size = self.position_size.calculate_position_size(
            trade_signal['signal_strength'],
            trade_signal['entry_price'],
            stop_loss,
            market_data['volatility_score']
        )
        
        # 4. 시장 상황별 조정
        adjusted_params = self.market_adjuster.get_adjusted_risk_params(
            market_regime, 
            {'stop_loss_pct': 0.05, 'take_profit_pct': 0.10, 'position_size': position_size}
        )
        
        # 5. 전체 리스크 노출도 체크
        portfolio_risk = self.calculate_portfolio_risk()
        
        # 6. 최종 승인/거부 결정
        risk_assessment = {
            'approved': True,
            'position_size': adjusted_params['position_size'],
            'stop_loss_price': stop_loss,
            'take_profit_price': trade_signal['entry_price'] * (1 + adjusted_params['take_profit_pct']),
            'market_regime': market_regime,
            'risk_score': self.calculate_risk_score(trade_signal, market_data),
            'warnings': []
        }
        
        # 위험 요소 체크
        if portfolio_risk > 0.8:
            risk_assessment['warnings'].append("포트폴리오 리스크 노출도 과도")
            
        if self.current_drawdown > self.max_daily_loss:
            risk_assessment['approved'] = False
            risk_assessment['warnings'].append("일일 손실 한도 도달")
        
        return risk_assessment
    
    def calculate_portfolio_risk(self) -> float:
        """전체 포트폴리오 리스크 계산"""
        # 현재 포지션들의 총 위험도 계산
        # VaR (Value at Risk) 계산 등
        return self.total_risk_exposure / self.position_size.capital
```

---

## 🎯 구현 우선순위

### Phase 1: 핵심 리스크 관리 (1주)
1. **변동성 기반 동적 손절**: ATR 기반 손절가 계산
2. **트레일링 스탑**: 수익 보호 시스템
3. **포지션 크기 조정**: 신호 강도 기반 크기 결정

### Phase 2: 고급 기능 (1-2주)
1. **다단계 익절**: 부분 매도 시스템
2. **시장 상황별 조정**: 상승장/하락장 대응
3. **실시간 모니터링**: 드로우다운 추적

### Phase 3: 최적화 (1주)
1. **백테스팅 검증**: 리스크 관리 효과 측정
2. **파라미터 최적화**: 성과 기반 자동 조정
3. **알림 시스템**: 위험 상황 즉시 알림

---

## 📊 예상 성과 개선

### 현재 시스템 위험도
- 최대 손실: 무제한 (시스템 실패 시)
- 드로우다운: 예측 불가
- 승률 vs 손익비: 불균형 (5% 손절 vs 10% 익절)

### 개선 후 목표
- 최대 손실: 거래당 2%, 일일 3% 제한
- 드로우다운: 10% 이내 제한
- 승률 vs 손익비: 균형 조정 (평균 승률 55%, 손익비 1:1.5)
- 연간 최대 손실: 15% 이내

---

**다음 단계**: 변동성 기반 동적 손절 시스템 구현 시작