#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/trading_signals.py

매매 신호 분석기 - 5가지 조건 기반 매매 신호 생성
1. RSI 과매도 탈출 (RSI > 30)
2. 거래량 급증 (20일 평균 대비 1.2배 이상)
3. MACD 매수 신호 (MACD가 Signal을 상향돌파)
4. 강세 캔들 패턴 (양봉이면서 몸체가 20일 평균 대비 2% 이상)
5. 5일선이 20일선을 골든 크로스
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from utils.logger import get_logger


class TradingSignalAnalyzer:
    """매매 신호 분석기"""

    def __init__(self):
        self.logger = get_logger(f"TradingSignalAnalyzer")

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        try:
            # 기본 이동평균선
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()

            # RSI 계산
            df = self._calculate_rsi(df)

            # MACD 계산
            df = self._calculate_macd(df)

            # 거래량 이동평균
            df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()

            return df

        except Exception as e:
            self.logger.error(f"[오류] 기술적 지표 계산 실패: {e}")
            return df

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI 계산"""
        try:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            return df
        except Exception as e:
            self.logger.error(f"[오류] RSI 계산 실패: {e}")
            return df

    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD 계산"""
        try:
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Histogram'] = df['MACD'] - df['Signal']

            return df
        except Exception as e:
            self.logger.error(f"[오류] MACD 계산 실패: {e}")
            return df

    def check_buy_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """매매 신호 조건 확인

        Args:
            df: 주가 데이터 (Open, High, Low, Close, Volume 포함)

        Returns:
            매매 신호가 추가된 DataFrame
        """
        try:
            # 기술적 지표 계산
            df = self.calculate_technical_indicators(df)

            # 1. RSI 과매도 탈출 신호 (RSI > 30)
            df['RSI_signal'] = (df['RSI'] > 30) & (df['RSI'].shift(1) <= 30)

            # 2. 거래량 급증 신호 (20일 평균 대비 1.2배 이상)
            df['VOL_signal'] = (df['Volume'] > df['Volume_MA20'] * 1.2)

            # 3. MACD 매수 신호 (MACD가 Signal을 상향돌파)
            df['MACD_signal'] = (df['MACD'] > df['Signal']) & (df['MACD'].shift(1) <= df['Signal'].shift(1))

            # 4. 강세 캔들 패턴 (양봉이면서 몸체가 20일 평균 대비 2% 이상)
            candle_body = abs(df['Close'] - df['Open'])
            avg_body = candle_body.rolling(window=20).mean()
            df['CANDLE_signal'] = (df['Close'] > df['Open']) & (candle_body > avg_body * 1.02)

            # 5. 5일선이 20일선을 골든 크로스
            df['GOLDEN_signal'] = (df['MA5'] > df['MA20']) & (df['MA5'].shift(1) <= df['MA20'].shift(1))

            # 조건 충족 개수 계산
            signal_columns = ['RSI_signal', 'VOL_signal', 'MACD_signal', 'CANDLE_signal', 'GOLDEN_signal']
            df['signal_count'] = df[signal_columns].sum(axis=1)

            # 2개 이상일 때 매수 신호
            df['BUY_signal'] = df['signal_count'] >= 2

            # 각 신호별 상세 정보
            df['signal_details'] = df.apply(self._get_signal_details, axis=1)

            # 신호 강도 계산 (0-100 스케일)
            df['signal_strength'] = (df['signal_count'] / len(signal_columns)) * 100

            return df

        except Exception as e:
            self.logger.error(f"[오류] 매매 신호 확인 실패: {e}")
            return df

    def _get_signal_details(self, row) -> Dict[str, Any]:
        """신호 상세 정보 생성"""
        details = {
            'RSI': {
                'active': bool(row['RSI_signal']) if pd.notna(row['RSI_signal']) else False,
                'value': round(row['RSI'], 2) if pd.notna(row['RSI']) else None,
                'description': f"RSI {row['RSI']:.1f} > 30 (과매도 탈출)" if pd.notna(row['RSI']) else "RSI 데이터 없음"
            },
            'Volume': {
                'active': bool(row['VOL_signal']) if pd.notna(row['VOL_signal']) else False,
                'ratio': round(row['Volume'] / row['Volume_MA20'], 2) if pd.notna(row['Volume_MA20']) and row['Volume_MA20'] > 0 else None,
                'description': f"거래량 {row['Volume']/row['Volume_MA20']:.1f}배 증가" if pd.notna(row['Volume_MA20']) and row['Volume_MA20'] > 0 else "거래량 데이터 없음"
            },
            'MACD': {
                'active': bool(row['MACD_signal']) if pd.notna(row['MACD_signal']) else False,
                'macd': round(row['MACD'], 4) if pd.notna(row['MACD']) else None,
                'signal': round(row['Signal'], 4) if pd.notna(row['Signal']) else None,
                'description': f"MACD({row['MACD']:.3f}) > Signal({row['Signal']:.3f})" if pd.notna(row['MACD']) and pd.notna(row['Signal']) else "MACD 데이터 없음"
            },
            'Candle': {
                'active': bool(row['CANDLE_signal']) if pd.notna(row['CANDLE_signal']) else False,
                'body_ratio': round((abs(row['Close'] - row['Open']) / row['Close']) * 100, 2) if row['Close'] > 0 else None,
                'description': f"강세 캔들 (몸체 {(abs(row['Close'] - row['Open'])/row['Close'])*100:.1f}%)" if row['Close'] > 0 else "캔들 데이터 없음"
            },
            'Golden_Cross': {
                'active': bool(row['GOLDEN_signal']) if pd.notna(row['GOLDEN_signal']) else False,
                'ma5': round(row['MA5'], 0) if pd.notna(row['MA5']) else None,
                'ma20': round(row['MA20'], 0) if pd.notna(row['MA20']) else None,
                'description': f"골든크로스 MA5({row['MA5']:.0f}) > MA20({row['MA20']:.0f})" if pd.notna(row['MA5']) and pd.notna(row['MA20']) else "이동평균 데이터 없음"
            }
        }
        return details

    def get_latest_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """최신 매매 신호 정보 반환"""
        try:
            if df.empty:
                return {'has_signal': False, 'message': '데이터가 없습니다'}

            latest = df.iloc[-1]

            signal_info = {
                'has_signal': bool(latest['BUY_signal']) if pd.notna(latest['BUY_signal']) else False,
                'signal_count': int(latest['signal_count']) if pd.notna(latest['signal_count']) else 0,
                'signal_strength': round(latest['signal_strength'], 1) if pd.notna(latest['signal_strength']) else 0,
                'timestamp': latest.name if hasattr(latest, 'name') else datetime.now(),
                'signals': {
                    'RSI_signal': bool(latest['RSI_signal']) if pd.notna(latest['RSI_signal']) else False,
                    'VOL_signal': bool(latest['VOL_signal']) if pd.notna(latest['VOL_signal']) else False,
                    'MACD_signal': bool(latest['MACD_signal']) if pd.notna(latest['MACD_signal']) else False,
                    'CANDLE_signal': bool(latest['CANDLE_signal']) if pd.notna(latest['CANDLE_signal']) else False,
                    'GOLDEN_signal': bool(latest['GOLDEN_signal']) if pd.notna(latest['GOLDEN_signal']) else False
                },
                'details': latest['signal_details'] if pd.notna(latest['signal_details']) else {},
                'price_info': {
                    'close': round(latest['Close'], 0) if pd.notna(latest['Close']) else 0,
                    'volume': int(latest['Volume']) if pd.notna(latest['Volume']) else 0,
                    'rsi': round(latest['RSI'], 1) if pd.notna(latest['RSI']) else 0,
                    'ma5': round(latest['MA5'], 0) if pd.notna(latest['MA5']) else 0,
                    'ma20': round(latest['MA20'], 0) if pd.notna(latest['MA20']) else 0
                }
            }

            return signal_info

        except Exception as e:
            self.logger.error(f"[오류] 최신 신호 정보 생성 실패: {e}")
            return {'has_signal': False, 'message': f'신호 분석 실패: {str(e)}'}

    def analyze_stock_signals(self, stock_code: str, stock_data: pd.DataFrame) -> Dict[str, Any]:
        """종목별 매매 신호 분석"""
        try:
            self.logger.info(f"[분석] {stock_code} 매매 신호 분석 시작")

            # 매매 신호 확인
            signals_df = self.check_buy_signals(stock_data.copy())

            # 최신 신호 정보
            latest_signals = self.get_latest_signals(signals_df)

            # 최근 7일간 신호 이력
            recent_signals = self._get_recent_signals_history(signals_df, days=7)

            # 신호 통계
            signal_stats = self._calculate_signal_statistics(signals_df)

            result = {
                'stock_code': stock_code,
                'latest_signals': latest_signals,
                'recent_history': recent_signals,
                'statistics': signal_stats,
                'analyzed_at': datetime.now()
            }

            self.logger.info(f"[완료] {stock_code} 매매 신호 분석 완료 - 신호강도: {latest_signals.get('signal_strength', 0)}%")

            return result

        except Exception as e:
            self.logger.error(f"[오류] {stock_code} 매매 신호 분석 실패: {e}")
            return {
                'stock_code': stock_code,
                'error': str(e),
                'analyzed_at': datetime.now()
            }

    def _get_recent_signals_history(self, df: pd.DataFrame, days: int = 7) -> List[Dict]:
        """최근 N일간의 신호 이력"""
        try:
            recent_df = df.tail(days)
            history = []

            for idx, row in recent_df.iterrows():
                if pd.notna(row['BUY_signal']) and row['BUY_signal']:
                    history.append({
                        'date': idx if hasattr(idx, 'strftime') else datetime.now(),
                        'signal_count': int(row['signal_count']) if pd.notna(row['signal_count']) else 0,
                        'signal_strength': round(row['signal_strength'], 1) if pd.notna(row['signal_strength']) else 0,
                        'active_signals': [k for k, v in {
                            'RSI': row['RSI_signal'],
                            'VOL': row['VOL_signal'],
                            'MACD': row['MACD_signal'],
                            'CANDLE': row['CANDLE_signal'],
                            'GOLDEN': row['GOLDEN_signal']
                        }.items() if pd.notna(v) and v],
                        'price': round(row['Close'], 0) if pd.notna(row['Close']) else 0
                    })

            return history

        except Exception as e:
            self.logger.error(f"[오류] 신호 이력 생성 실패: {e}")
            return []

    def _calculate_signal_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """신호 통계 계산"""
        try:
            stats = {
                'total_signals': int(df['BUY_signal'].sum()) if 'BUY_signal' in df else 0,
                'avg_signal_strength': round(df['signal_strength'].mean(), 1) if 'signal_strength' in df else 0,
                'signal_frequency': {
                    'RSI': int(df['RSI_signal'].sum()) if 'RSI_signal' in df else 0,
                    'VOL': int(df['VOL_signal'].sum()) if 'VOL_signal' in df else 0,
                    'MACD': int(df['MACD_signal'].sum()) if 'MACD_signal' in df else 0,
                    'CANDLE': int(df['CANDLE_signal'].sum()) if 'CANDLE_signal' in df else 0,
                    'GOLDEN': int(df['GOLDEN_signal'].sum()) if 'GOLDEN_signal' in df else 0
                }
            }

            return stats

        except Exception as e:
            self.logger.error(f"[오류] 신호 통계 계산 실패: {e}")
            return {}


# 사용 예시 함수
def demo_trading_signals():
    """매매 신호 데모"""
    # 샘플 데이터 생성 (실제 사용시에는 실제 주가 데이터 사용)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    # 샘플 주가 데이터
    close_prices = 10000 + np.cumsum(np.random.randn(100) * 50)

    sample_data = pd.DataFrame({
        'Open': close_prices - np.random.rand(100) * 100,
        'High': close_prices + np.random.rand(100) * 200,
        'Low': close_prices - np.random.rand(100) * 200,
        'Close': close_prices,
        'Volume': np.random.randint(100000, 1000000, 100)
    }, index=dates)

    # 매매 신호 분석
    analyzer = TradingSignalAnalyzer()
    result = analyzer.analyze_stock_signals('005930', sample_data)

    print("=== 매매 신호 분석 결과 ===")
    print(f"종목코드: {result['stock_code']}")
    print(f"매수 신호: {result['latest_signals']['has_signal']}")
    print(f"신호 강도: {result['latest_signals']['signal_strength']}%")
    print(f"활성 신호 수: {result['latest_signals']['signal_count']}/5")

    print("\n=== 개별 신호 상태 ===")
    for signal_name, is_active in result['latest_signals']['signals'].items():
        status = "🟢 활성" if is_active else "⚪ 비활성"
        print(f"{signal_name}: {status}")


if __name__ == "__main__":
    demo_trading_signals()