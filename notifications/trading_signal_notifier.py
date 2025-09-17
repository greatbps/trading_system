#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/notifications/trading_signal_notifier.py

전략별 매매 신호 실시간 알림 시스템
매매조건.md의 기준에 따른 실시간 신호 발생 및 텔레그램 알림
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

from config import Config
from data_collectors.kis_collector import KISCollector
from analyzers.analysis_engine import AnalysisEngine
from notifications.telegram_notifier import TelegramNotifier
from utils.encoding_fix import clean_unicode_emojis, safe_format


@dataclass
class TradingSignalAlert:
    """매매 신호 알림 데이터"""
    timestamp: datetime
    symbol: str
    name: str
    strategy: str
    signal_type: str  # BUY, SELL, PARTIAL_SELL, WATCH
    price: float
    confidence: float
    reasons: List[str]
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    timeframe: str  # 3m, 5m, 15m, 30m, 1h, 1d
    technical_data: Dict[str, Any]
    urgency: int  # 1=즉시, 2=높음, 3=보통, 4=낮음, 5=참고용


class TradingSignalNotifier:
    """실시간 매매 신호 알림 시스템"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 컴포넌트 초기화
        self.kis_collector = None
        self.analysis_engine = None
        self.telegram_notifier = None
        
        # 알림 설정
        self.monitoring_symbols = []
        self.active_strategies = ['momentum', 'breakout', 'eod', 'supertrend_ema_rsi', 'vwap', 'scalping_3m', 'rsi']
        self.scan_interval = 180  # 3분 간격
        self.last_signals = {}  # 중복 알림 방지
        
        # 시간대별 모니터링 설정
        self.timeframe_intervals = {
            '3m': 3,    # 3분
            '5m': 5,    # 5분
            '15m': 15,  # 15분
            '30m': 30,  # 30분
            '1h': 60,   # 1시간
            '1d': 1440  # 1일
        }
        
        self.logger.info("✅ Trading Signal Notifier 초기화 완료")
    
    async def initialize(self):
        """시스템 컴포넌트 초기화"""
        try:
            # KIS 데이터 수집기 초기화
            self.kis_collector = KISCollector(self.config)
            await self.kis_collector.initialize()
            
            # 분석 엔진 초기화
            self.analysis_engine = AnalysisEngine(self.config)
            
            # 텔레그램 알림 초기화
            self.telegram_notifier = TelegramNotifier(self.config)
            
            # 모니터링 종목 로드
            await self._load_monitoring_symbols()
            
            self.logger.info("✅ Trading Signal Notifier 컴포넌트 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 초기화 오류: {e}")
            raise
    
    async def start_monitoring(self):
        """실시간 모니터링 시작"""
        try:
            self.logger.info("🚀 실시간 매매 신호 모니터링 시작")
            
            while True:
                try:
                    # 매매 시간 확인
                    if not self._is_trading_time():
                        await asyncio.sleep(300)  # 5분 대기
                        continue
                    
                    # 전략별 신호 스캔
                    signals = await self._scan_trading_signals()
                    
                    # 신호 처리 및 알림
                    for signal in signals:
                        await self._process_signal(signal)
                    
                    # 다음 스캔까지 대기
                    await asyncio.sleep(self.scan_interval)
                    
                except Exception as e:
                    self.logger.error(f"❌ 모니터링 오류: {e}")
                    await asyncio.sleep(60)  # 1분 대기 후 재시도
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 시작 오류: {e}")
            raise
    
    def _is_trading_time(self) -> bool:
        """매매 시간 확인"""
        now = datetime.now()
        weekday = now.weekday()
        
        # 주말 제외
        if weekday >= 5:  # 토요일(5), 일요일(6)
            return False
        
        # 평일 9:00 ~ 15:30
        trading_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        trading_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return trading_start <= now <= trading_end
    
    async def _load_monitoring_symbols(self):
        """모니터링 종목 로드"""
        try:
            # 기본 모니터링 종목 (대형주 + 관심종목)
            default_symbols = [
                ('005930', '삼성전자'),
                ('000660', 'SK하이닉스'),
                ('035420', 'NAVER'),
                ('051910', 'LG화학'),
                ('068270', '셀트리온'),
                ('207940', '삼성바이오로직스'),
                ('006400', '삼성SDI'),
                ('028260', '삼성물산'),
                ('012330', '현대모비스'),
                ('066570', 'LG전자')
            ]
            
            # HTS 조건검색으로 추가 종목 수집
            for strategy in ['momentum', 'breakout', 'rsi']:
                try:
                    strategy_symbols = await self.kis_collector.get_filtered_stocks(strategy, 10)
                    if strategy_symbols:
                        default_symbols.extend(strategy_symbols[:5])  # 상위 5개만 추가
                except Exception as e:
                    self.logger.warning(f"⚠️ {strategy} 전략 종목 수집 실패: {e}")
            
            # 중복 제거
            seen = set()
            self.monitoring_symbols = []
            for symbol, name in default_symbols:
                if symbol not in seen:
                    self.monitoring_symbols.append((symbol, name))
                    seen.add(symbol)
            
            self.logger.info(f"📊 모니터링 종목 로드 완료: {len(self.monitoring_symbols)}개 종목")
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 종목 로드 오류: {e}")
            # 기본 종목으로 폴백
            self.monitoring_symbols = [('005930', '삼성전자'), ('000660', 'SK하이닉스')]
    
    async def _scan_trading_signals(self) -> List[TradingSignalAlert]:
        """전체 종목의 매매 신호 스캔"""
        signals = []
        
        try:
            # 병렬로 종목 분석
            tasks = []
            for symbol, name in self.monitoring_symbols:
                task = self._analyze_symbol_signals(symbol, name)
                tasks.append(task)
            
            # 최대 10개씩 배치 처리
            batch_size = 10
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, list):
                        signals.extend(result)
                    elif isinstance(result, Exception):
                        self.logger.warning(f"⚠️ 종목 분석 오류: {result}")
            
            self.logger.debug(f"📈 신호 스캔 완료: {len(signals)}개 신호 발견")
            return signals
            
        except Exception as e:
            self.logger.error(f"❌ 신호 스캔 오류: {e}")
            return []
    
    async def _analyze_symbol_signals(self, symbol: str, name: str) -> List[TradingSignalAlert]:
        """개별 종목의 매매 신호 분석"""
        signals = []
        
        try:
            # 현재 주가 정보 수집
            stock_data = await self._get_current_stock_data(symbol, name)
            if not stock_data:
                return signals
            
            # 전략별 신호 분석
            for strategy in self.active_strategies:
                try:
                    strategy_signals = await self._analyze_strategy_signal(
                        symbol, name, stock_data, strategy
                    )
                    signals.extend(strategy_signals)
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} {strategy} 분석 오류: {e}")
            
            return signals
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 신호 분석 오류: {e}")
            return []
    
    async def _get_current_stock_data(self, symbol: str, name: str) -> Optional[Dict[str, Any]]:
        """현재 주가 데이터 수집"""
        try:
            # KIS API에서 실시간 데이터 수집 (임시로 가상 데이터 사용)
            import random
            
            base_price = 50000 + (hash(symbol) % 50000)
            current_price = base_price * (1 + (random.random() - 0.5) * 0.1)  # ±5% 변동
            
            stock_data = {
                'symbol': symbol,
                'name': name,
                'current_price': round(current_price, 0),
                'change_rate': (random.random() - 0.5) * 10,  # ±5% 변동률
                'volume': random.randint(100000, 5000000),
                'market_cap': random.randint(1000000000, 500000000000),
                'high_52w': current_price * 1.3,
                'low_52w': current_price * 0.7,
                'avg_volume_30d': random.randint(500000, 2000000),
                
                # 기술적 지표 (실제로는 계산된 값 사용)
                'technical_indicators': {
                    'rsi': 30 + random.random() * 40,  # 30-70
                    'ema_5': current_price * (1 + (random.random() - 0.5) * 0.02),
                    'ema_20': current_price * (1 + (random.random() - 0.5) * 0.05),
                    'macd_line': (random.random() - 0.5) * 100,
                    'macd_signal': (random.random() - 0.5) * 100,
                    'bb_upper': current_price * 1.02,
                    'bb_lower': current_price * 0.98,
                    'volume_ratio': 0.5 + random.random() * 2.0
                }
            }
            
            return stock_data
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 데이터 수집 오류: {e}")
            return None
    
    async def _analyze_strategy_signal(
        self,
        symbol: str,
        name: str,
        stock_data: Dict[str, Any],
        strategy: str
    ) -> List[TradingSignalAlert]:
        """전략별 매매 신호 분석"""
        signals = []
        
        try:
            # 전략별 신호 생성
            if strategy == "scalping_3m":
                signals.extend(await self._analyze_scalping_signals(symbol, name, stock_data))
            elif strategy == "rsi":
                signals.extend(await self._analyze_rsi_signals(symbol, name, stock_data))
            elif strategy == "momentum":
                signals.extend(await self._analyze_momentum_signals(symbol, name, stock_data))
            elif strategy == "breakout":
                signals.extend(await self._analyze_breakout_signals(symbol, name, stock_data))
            
            return signals
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} {strategy} 신호 분석 오류: {e}")
            return []
    
    async def _analyze_scalping_signals(self, symbol: str, name: str, stock_data: Dict[str, Any]) -> List[TradingSignalAlert]:
        """3분봉 스캘핑 신호 분석 (매매조건.md 기준)"""
        signals = []
        indicators = stock_data.get('technical_indicators', {})
        
        # 매수 신호 조건
        buy_conditions = []
        
        # 1. 5EMA > 20EMA 돌파
        if indicators.get('ema_5', 0) > indicators.get('ema_20', 0):
            buy_conditions.append("5EMA > 20EMA 돌파")
        
        # 2. 거래량 급증 + 양봉
        if (stock_data.get('change_rate', 0) > 0 and 
            indicators.get('volume_ratio', 1) > 2.0):
            buy_conditions.append("거래량 급증 양봉")
        
        # 3. 볼린저 하단 반등
        if (stock_data.get('current_price', 0) > indicators.get('bb_lower', 0)):
            buy_conditions.append("볼린저 하단 반등")
        
        # 매수 신호 생성 (2개 이상 조건 만족)
        if len(buy_conditions) >= 2:
            signal = TradingSignalAlert(
                timestamp=datetime.now(),
                symbol=symbol,
                name=name,
                strategy="scalping_3m",
                signal_type="BUY",
                price=stock_data.get('current_price', 0),
                confidence=len(buy_conditions) / 3.0,
                reasons=buy_conditions,
                risk_level="MEDIUM",
                timeframe="3m",
                technical_data=indicators,
                urgency=2  # 높은 우선순위
            )
            signals.append(signal)
        
        # 매도 신호 조건
        sell_conditions = []
        
        # 1. 5EMA 이탈 (부분 매도)
        if indicators.get('ema_5', 0) < indicators.get('ema_20', 0):
            sell_conditions.append("5EMA 이탈")
        
        # 2. 거래량 급감 음봉
        if (stock_data.get('change_rate', 0) < 0 and 
            indicators.get('volume_ratio', 1) < 0.5):
            sell_conditions.append("거래량 급감 음봉")
        
        # 매도 신호 생성
        if len(sell_conditions) >= 1:
            signal_type = "PARTIAL_SELL" if "5EMA 이탈" in sell_conditions else "SELL"
            signal = TradingSignalAlert(
                timestamp=datetime.now(),
                symbol=symbol,
                name=name,
                strategy="scalping_3m",
                signal_type=signal_type,
                price=stock_data.get('current_price', 0),
                confidence=0.7,
                reasons=sell_conditions,
                risk_level="LOW",
                timeframe="3m",
                technical_data=indicators,
                urgency=1  # 즉시
            )
            signals.append(signal)
        
        return signals
    
    async def _analyze_rsi_signals(self, symbol: str, name: str, stock_data: Dict[str, Any]) -> List[TradingSignalAlert]:
        """RSI 전략 신호 분석 (매매조건.md 기준)"""
        signals = []
        indicators = stock_data.get('technical_indicators', {})
        rsi = indicators.get('rsi', 50)
        
        # 매수 신호 - RSI 30 이하에서 반등
        if rsi <= 30 and stock_data.get('change_rate', 0) > 0:
            buy_conditions = ["RSI 과매도 반등"]
            
            # 추가 확인 조건
            if indicators.get('macd_line', 0) > indicators.get('macd_signal', 0):
                buy_conditions.append("MACD 골든크로스")
            
            if indicators.get('volume_ratio', 1) > 1.2:
                buy_conditions.append("거래량 증가")
            
            signal = TradingSignalAlert(
                timestamp=datetime.now(),
                symbol=symbol,
                name=name,
                strategy="rsi",
                signal_type="BUY",
                price=stock_data.get('current_price', 0),
                confidence=len(buy_conditions) / 3.0,
                reasons=buy_conditions,
                risk_level="LOW",
                timeframe="15m",
                technical_data=indicators,
                urgency=2
            )
            signals.append(signal)
        
        # 매도 신호 - RSI 70 이상에서 하락 반전
        elif rsi >= 70 and stock_data.get('change_rate', 0) < 0:
            sell_conditions = ["RSI 과매수 하락 반전"]
            
            if indicators.get('macd_line', 0) < indicators.get('macd_signal', 0):
                sell_conditions.append("MACD 데드크로스")
            
            signal = TradingSignalAlert(
                timestamp=datetime.now(),
                symbol=symbol,
                name=name,
                strategy="rsi",
                signal_type="SELL",
                price=stock_data.get('current_price', 0),
                confidence=len(sell_conditions) / 2.0,
                reasons=sell_conditions,
                risk_level="MEDIUM",
                timeframe="15m",
                technical_data=indicators,
                urgency=1
            )
            signals.append(signal)
        
        return signals
    
    async def _analyze_momentum_signals(self, symbol: str, name: str, stock_data: Dict[str, Any]) -> List[TradingSignalAlert]:
        """모멘텀 전략 신호 분석"""
        signals = []
        
        # 강한 상승 모멘텀 감지
        if (stock_data.get('change_rate', 0) > 3.0 and 
            stock_data.get('technical_indicators', {}).get('volume_ratio', 1) > 1.5):
            
            signal = TradingSignalAlert(
                timestamp=datetime.now(),
                symbol=symbol,
                name=name,
                strategy="momentum",
                signal_type="BUY",
                price=stock_data.get('current_price', 0),
                confidence=0.8,
                reasons=["강한 상승 모멘텀", "거래량 증가"],
                risk_level="HIGH",
                timeframe="5m",
                technical_data=stock_data.get('technical_indicators', {}),
                urgency=1
            )
            signals.append(signal)
        
        return signals
    
    async def _analyze_breakout_signals(self, symbol: str, name: str, stock_data: Dict[str, Any]) -> List[TradingSignalAlert]:
        """돌파 전략 신호 분석"""
        signals = []
        indicators = stock_data.get('technical_indicators', {})
        
        # 볼린저 밴드 상단 돌파
        if (stock_data.get('current_price', 0) > indicators.get('bb_upper', 0) and 
            indicators.get('volume_ratio', 1) > 1.3):
            
            signal = TradingSignalAlert(
                timestamp=datetime.now(),
                symbol=symbol,
                name=name,
                strategy="breakout",
                signal_type="BUY",
                price=stock_data.get('current_price', 0),
                confidence=0.75,
                reasons=["볼린저 상단 돌파", "거래량 동반"],
                risk_level="MEDIUM",
                timeframe="15m",
                technical_data=indicators,
                urgency=2
            )
            signals.append(signal)
        
        return signals
    
    async def _process_signal(self, signal: TradingSignalAlert):
        """신호 처리 및 알림 전송"""
        try:
            # 중복 신호 확인
            signal_key = f"{signal.symbol}_{signal.strategy}_{signal.signal_type}"
            
            if signal_key in self.last_signals:
                last_time = self.last_signals[signal_key]
                if (signal.timestamp - last_time).seconds < 600:  # 10분 내 중복 방지
                    return
            
            # 신호 기록
            self.last_signals[signal_key] = signal.timestamp
            
            # 텔레그램 알림 전송
            await self._send_telegram_alert(signal)
            
            # 로그 기록
            self.logger.info(f"📢 매매신호: {signal.symbol}({signal.name}) {signal.strategy} {signal.signal_type} {signal.price:,.0f}원")
            
        except Exception as e:
            self.logger.error(f"❌ 신호 처리 오류: {e}")
    
    async def _send_telegram_alert(self, signal: TradingSignalAlert):
        """텔레그램 알림 전송"""
        try:
            # 긴급도별 이모지
            urgency_emoji = {1: "🚨", 2: "⚡", 3: "📈", 4: "📊", 5: "💡"}
            signal_emoji = {
                "BUY": "🟢",
                "SELL": "🔴", 
                "PARTIAL_SELL": "🟡",
                "WATCH": "👀"
            }
            
            # 메시지 구성
            message_parts = [
                f"{urgency_emoji.get(signal.urgency, '📊')} {signal_emoji.get(signal.signal_type, '📈')} **매매신호**",
                f"",
                f"🎯 **종목**: {signal.symbol} {signal.name}",
                f"📊 **전략**: {signal.strategy.upper()}",
                f"🔄 **신호**: {signal.signal_type}",
                f"💰 **가격**: {signal.price:,.0f}원",
                f"시간 **시간**: {signal.timestamp.strftime('%H:%M:%S')}",
                f"📋 **시간대**: {signal.timeframe}",
                f"🎯 **신뢰도**: {signal.confidence:.1%}",
                f"⚠️ **위험도**: {signal.risk_level}",
                f"",
                f"📝 **근거**:"
            ]
            
            for i, reason in enumerate(signal.reasons, 1):
                message_parts.append(f"  {i}. {reason}")
            
            # 기술적 지표 정보 추가
            if signal.technical_data:
                message_parts.extend([
                    f"",
                    f"📊 **기술지표**:"
                ])
                
                if 'rsi' in signal.technical_data:
                    message_parts.append(f"  RSI: {signal.technical_data['rsi']:.1f}")
                if 'volume_ratio' in signal.technical_data:
                    message_parts.append(f"  거래량비: {signal.technical_data['volume_ratio']:.1f}배")
            
            message = "\n".join(message_parts)
            
            # 인코딩 안전 처리
            safe_message = clean_unicode_emojis(message)
            
            # 텔레그램 전송
            if self.telegram_notifier:
                await self.telegram_notifier.send_trading_signal(safe_message)
            
        except Exception as e:
            self.logger.error(f"❌ 텔레그램 알림 전송 오류: {e}")
    
    async def add_monitoring_symbol(self, symbol: str, name: str):
        """모니터링 종목 추가"""
        if (symbol, name) not in self.monitoring_symbols:
            self.monitoring_symbols.append((symbol, name))
            self.logger.info(f"➕ 모니터링 종목 추가: {symbol} {name}")
    
    async def remove_monitoring_symbol(self, symbol: str):
        """모니터링 종목 제거"""
        self.monitoring_symbols = [(s, n) for s, n in self.monitoring_symbols if s != symbol]
        self.logger.info(f"➖ 모니터링 종목 제거: {symbol}")
    
    def get_monitoring_symbols(self) -> List[tuple]:
        """현재 모니터링 종목 조회"""
        return self.monitoring_symbols.copy()


async def main():
    """메인 실행 함수"""
    try:
        config = Config()
        notifier = TradingSignalNotifier(config)
        await notifier.initialize()
        
        print("🚀 실시간 매매 신호 알림 시스템 시작")
        await notifier.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"❌ 실행 오류: {e}")


if __name__ == "__main__":
    asyncio.run(main())