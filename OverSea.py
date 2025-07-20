# ==================== 시장 시간 감지 ====================
def get_market_session():
    """현재 시장 세션 판단"""
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    
    # 주말 체크
    if now_ny.weekday() >= 5:
        return "CLOSED", "주말 휴장"
    
    # 시간대별 세션 판단
    hour = now_ny.hour
    minute = now_ny.minute
    current_minutes = hour * 60 + minute
    
    # 정규장 (09:30 ~ 16:00) - 정규 거래시간
    market_open = 9 * 60 + 30  # 570분
    market_close = 16 * 60     # 960분
    
    if market_open <= current_minutes <= market_close:
        return "REGULAR", "정규장"
    
    # 프리마켓 (04:00 ~ 09:30) - 장외 거래시간
    premarket_start = 4 * 60   # 240분
    if premarket_start <= current_minutes < market_open:
        return "EXTENDED", "프리마켓 (장외거래)"
    
    # 애프터마켓 (16:00 ~ 20:00) - 장외 거래시간
    aftermarket_end = 20 * 60  # 1200분
    if market_close < current_minutes <= aftermarket_end:
        return "EXTENDED", "애프터마켓 (장외거래)"
    
    # 완전 휴장 (20:00 ~ 04:00 다음날)
    return "CLOSED", "완전 휴장"# -*- coding: utf-8 -*-
"""
완전한 SOXL 트레이딩 시스템
- RSI + EMA + 슈퍼트렌드 복합 전략
- 15분봉 1% 이상 변동성 알림
- 실시간 매매 시그널
- 텔레그램 알림
"""

import os
import json
import time
import threading
import requests
import pytz
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Optional, Tuple, Dict
from collections import deque

# ==================== 환경 설정 ====================
load_dotenv()

# API 키 설정
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELE_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 백업 API 키들
POLYGON_KEY = os.getenv("POLYGON_API_KEY")

# KIS API 환경
IS_VIRTUAL = True
BASE_URL = "https://openapivts.koreainvestment.com:29443" if IS_VIRTUAL else "https://openapi.koreainvestment.com:9443"

# ==================== 트레이딩 전략 설정 ====================
# 슈퍼트렌드 설정
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0

# RSI 설정
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# EMA 설정
EMA_SHORT = 20
EMA_LONG = 50

# 변동성 설정
VOLATILITY_THRESHOLD = 0.7  # 0.7% 이상으로 낮춤
VOLUME_RATIO_THRESHOLD = 1.5  # 거래량 1.5배 이상
CANDLE_INTERVAL = 15  # 15분봉

# 로그 설정
LOG_LEVEL = "INFO"

# ==================== 전역 변수 ====================
latest_price = None
price_source = None
access_token_cache = {"token": None, "expire_time": 0}

# 트레이딩 데이터
candle_data = deque(maxlen=100)  # 최대 100개 캔들 저장
strategy_data = {
    "last_signal": None,
    "last_signal_time": None,
    "supertrend_trend": None,
    "rsi": None,
    "ema_short": None,
    "ema_long": None
}

last_15min_candle = None

# ==================== 로깅 시스템 ====================
def log(level, message, force=False):
    """로그 출력"""
    levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
    current_level = levels.get(LOG_LEVEL, 1)
    msg_level = levels.get(level, 1)
    
    if msg_level < current_level and not force:
        return
    
    timestamp = datetime.now().strftime('%H:%M:%S')
    emoji = {"DEBUG": "🔧", "INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "📝")
    
    print(f"{emoji} {timestamp} {message}")

def send_telegram(msg, silent=False):
    """텔레그램 메시지 전송"""
    try:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        data = {
            "chat_id": TELE_CHAT_ID, 
            "text": msg,
            "parse_mode": "HTML",
            "disable_notification": silent
        }
        
        response = requests.post(url, data=data, timeout=5)
        response.raise_for_status()
        return True
    except Exception as e:
        log("ERROR", f"텔레그램 전송 실패: {e}")
        return False

# ==================== 캔들 데이터 수집 ====================
def get_candle_data_from_yahoo(count=100):
    """야후 파이낸스에서 15분봉 데이터 가져오기"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=30)  # 넉넉하게
        
        period1 = int(start_time.timestamp())
        period2 = int(end_time.timestamp())
        
        url = "https://query1.finance.yahoo.com/v8/finance/chart/SOXL"
        params = {
            'period1': period1,
            'period2': period2,
            'interval': '15m',
            'includePrePost': 'false'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result'][0]
                
                timestamps = result['timestamp']
                quotes = result['indicators']['quote'][0]
                
                candles = []
                for i, timestamp in enumerate(timestamps):
                    if all(quotes[key][i] is not None for key in ['open', 'high', 'low', 'close']):
                        candle = {
                            'timestamp': timestamp,
                            'datetime': datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/New_York')),
                            'open': float(quotes['open'][i]),
                            'high': float(quotes['high'][i]),
                            'low': float(quotes['low'][i]),
                            'close': float(quotes['close'][i]),
                            'volume': float(quotes['volume'][i]) if quotes['volume'][i] else 0
                        }
                        candles.append(candle)
                
                return candles[-count:] if len(candles) > count else candles
        
        raise Exception(f"야후 파이낸스 오류: {response.status_code}")
        
    except Exception as e:
        log("ERROR", f"캔들 데이터 수집 실패: {e}")
        return None

def update_candle_data():
    """캔들 데이터 업데이트"""
    global candle_data
    
    candles = get_candle_data_from_yahoo()
    if candles:
        candle_data.clear()
        candle_data.extend(candles)
        log("DEBUG", f"{len(candles)}개 캔들 업데이트")
        return True
    
    return False

# ==================== 기술적 지표 계산 ====================
def calculate_rsi(prices, period=14):
    """RSI 계산"""
    if len(prices) < period + 1:
        return None
    
    df = pd.Series(prices)
    delta = df.diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None

def calculate_ema(prices, span):
    """EMA 계산"""
    if len(prices) < span:
        return None
    
    df = pd.Series(prices)
    ema = df.ewm(span=span, adjust=False).mean()
    
    return ema.iloc[-1] if not pd.isna(ema.iloc[-1]) else None

def calculate_atr(candles, period=10):
    """ATR 계산"""
    if len(candles) < period + 1:
        return None
    
    tr_values = []
    
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low'] 
        close_prev = candles[i-1]['close']
        
        tr = max(
            high - low,
            abs(high - close_prev),
            abs(low - close_prev)
        )
        tr_values.append(tr)
    
    if len(tr_values) >= period:
        return sum(tr_values[-period:]) / period
    
    return None

def calculate_supertrend(candles, period=10, multiplier=3.0):
    """슈퍼트렌드 계산"""
    if len(candles) < period + 1:
        return None, None
    
    atr = calculate_atr(candles, period)
    if not atr:
        return None, None
    
    latest_candle = candles[-1]
    hl2 = (latest_candle['high'] + latest_candle['low']) / 2
    
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    # 이전 값들 가져오기
    if hasattr(calculate_supertrend, 'prev_upper'):
        prev_upper = calculate_supertrend.prev_upper
        prev_lower = calculate_supertrend.prev_lower
        prev_close = candles[-2]['close'] if len(candles) > 1 else latest_candle['close']
        
        final_upper = basic_upper if basic_upper < prev_upper or prev_close > prev_upper else prev_upper
        final_lower = basic_lower if basic_lower > prev_lower or prev_close < prev_lower else prev_lower
    else:
        final_upper = basic_upper
        final_lower = basic_lower
    
    close = latest_candle['close']
    
    if hasattr(calculate_supertrend, 'prev_trend'):
        if calculate_supertrend.prev_trend == 'UP':
            trend = 'DOWN' if close < final_lower else 'UP'
        else:
            trend = 'UP' if close > final_upper else 'DOWN'
    else:
        trend = 'UP' if close > final_lower else 'DOWN'
    
    supertrend_value = final_lower if trend == 'UP' else final_upper
    
    # 다음 계산을 위해 저장
    calculate_supertrend.prev_upper = final_upper
    calculate_supertrend.prev_lower = final_lower
    calculate_supertrend.prev_trend = trend
    
    return supertrend_value, trend

# ==================== 복합 전략 분석 ====================
def analyze_trading_strategy():
    """RSI + EMA + 슈퍼트렌드 복합 전략 분석"""
    global strategy_data
    
    if len(candle_data) < max(RSI_PERIOD, EMA_LONG, SUPERTREND_PERIOD) + 1:
        return None
    
    # 종가 데이터 추출
    closes = [candle['close'] for candle in candle_data]
    
    # 기술적 지표 계산
    rsi = calculate_rsi(closes, RSI_PERIOD)
    ema_short = calculate_ema(closes, EMA_SHORT)
    ema_long = calculate_ema(closes, EMA_LONG)
    st_value, st_trend = calculate_supertrend(list(candle_data), SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER)
    
    if not all([rsi, ema_short, ema_long, st_value, st_trend]):
        return None
    
    # 이전 트렌드 가져오기
    prev_trend = strategy_data.get("supertrend_trend")
    
    # 매매 시그널 분석
    signal = None
    
    # 매수 조건
    buy_conditions = [
        ema_short > ema_long,  # 단기 EMA가 장기 EMA 위에
        st_trend == 'UP',      # 슈퍼트렌드 상승
        prev_trend != 'UP',    # 트렌드 전환 (DOWN → UP)
        rsi < RSI_OVERBOUGHT   # RSI 과매수 아님
    ]
    
    # 매도 조건
    sell_conditions = [
        ema_short < ema_long or  # 단기 EMA가 장기 EMA 아래 또는
        st_trend == 'DOWN' or    # 슈퍼트렌드 하락 또는  
        rsi > RSI_OVERBOUGHT     # RSI 과매수
    ]
    
    if all(buy_conditions):
        signal = 'BUY'
    elif any(sell_conditions) and prev_trend == 'UP':
        signal = 'SELL'
    
    # 전략 데이터 업데이트
    strategy_data.update({
        "rsi": rsi,
        "ema_short": ema_short,
        "ema_long": ema_long,
        "supertrend_value": st_value,
        "supertrend_trend": st_trend,
        "last_update": datetime.now()
    })
    
    return signal

# ==================== 변동성 분석 (가격+거래량) ====================
def check_volatility():
    """15분봉 가격+거래량 변동성 체크"""
    global last_15min_candle
    
    if len(candle_data) < 4:  # 최소 4개 필요 (현재+이전+평균계산용)
        return None
    
    current_candle = candle_data[-1]
    
    # 이미 체크한 캔들이면 스킵
    if last_15min_candle and last_15min_candle['timestamp'] == current_candle['timestamp']:
        return None
    
    prev_candle = candle_data[-2]
    
    # 가격 변동률 계산
    price_change = current_candle['close'] - prev_candle['close']
    percentage_change = (price_change / prev_candle['close']) * 100
    
    # 거래량 비율 계산 (직전 3개 캔들 평균 대비)
    recent_volumes = [candle['volume'] for candle in list(candle_data)[-4:-1]]  # 최근 3개
    avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 1
    current_volume = current_candle['volume']
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
    
    # 알림 조건 판단
    price_significant = abs(percentage_change) >= VOLATILITY_THRESHOLD
    volume_significant = volume_ratio >= VOLUME_RATIO_THRESHOLD
    
    alert_type = None
    
    # 강한 신호: 가격 변화 + 거래량 급증
    if price_significant and volume_ratio >= VOLUME_RATIO_THRESHOLD:
        alert_type = "강한 추세"
        emoji = "🚀" if percentage_change > 0 else "🔻"
    
    # 세력 개입 신호: 작은 가격 변화 + 거래량 급증  
    elif 0.3 <= abs(percentage_change) < VOLATILITY_THRESHOLD and volume_ratio >= 2.0:
        alert_type = "거래량 이상"
        emoji = "👀"
    
    # 알림 조건 만족 시
    if alert_type:
        direction = "상승" if percentage_change > 0 else "하락"
        
        volatility_msg = f"""{emoji} <b>SOXL {alert_type} 감지</b>

15분봉 {direction}: {percentage_change:+.2f}%
거래량 급증: {volume_ratio:.1f}배

이전 종가: ${prev_candle['close']:.2f}
현재 종가: ${current_candle['close']:.2f}
변동금액: ${price_change:+.2f}

현재 거래량: {current_volume:,.0f}
평균 거래량: {avg_volume:,.0f}

시간: {current_candle['datetime'].strftime('%H:%M')} NY"""
        
        send_telegram(volatility_msg)
        last_15min_candle = current_candle
        
        log("INFO", f"{alert_type} 알림: {percentage_change:+.2f}% / 거래량 {volume_ratio:.1f}배")
        
        return {
            "type": alert_type,
            "percentage": percentage_change,
            "direction": direction,
            "volume_ratio": volume_ratio,
            "prev_close": prev_candle['close'],
            "current_close": current_candle['close']
        }
    
    # 체크 완료 표시 (알림은 없음)
    last_15min_candle = current_candle
    return None

# ==================== 시그널 알림 ====================
def send_trading_signal(signal):
    """복합 전략 매매 시그널 알림"""
    signal_emoji = "🟢" if signal == "BUY" else "🔴"
    
    # 안전한 값 추출
    rsi = strategy_data.get("rsi") or 0
    ema_short = strategy_data.get("ema_short") or 0
    ema_long = strategy_data.get("ema_long") or 0
    st_value = strategy_data.get("supertrend_value") or 0
    st_trend = strategy_data.get("supertrend_trend") or "N/A"
    
    # RSI 상태 판단
    if rsi > RSI_OVERBOUGHT:
        rsi_status = "⚠️과매수"
    elif rsi < RSI_OVERSOLD:
        rsi_status = "🔵과매도"
    else:
        rsi_status = "✅정상"
    
    signal_msg = f"""{signal_emoji} <b>SOXL 복합전략 시그널</b>

🎯 신호: {signal}
💰 현재가: ${latest_price:.2f}

<b>📊 기술적 지표</b>
RSI({RSI_PERIOD}): {rsi:.1f}
EMA{EMA_SHORT}: ${ema_short:.2f}
EMA{EMA_LONG}: ${ema_long:.2f}
슈퍼트렌드: ${st_value:.2f} ({st_trend})

<b>📈 매매 조건</b>
• EMA 배치: {"✅" if ema_short > ema_long else "❌"} (단기>장기)
• 슈퍼트렌드: {"✅" if st_trend == "UP" else "❌"} ({st_trend})
• RSI 상태: {rsi_status}

시간: {datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M')} NY

⚠️ 투자 결정은 신중히 하세요"""
    
    send_telegram(signal_msg)
    log("INFO", f"복합 시그널: {signal} at ${latest_price:.2f}")

# ==================== 현재가 조회 ====================
def get_yahoo_price():
    """Yahoo Finance 현재가"""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/SOXL"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if 'chart' in data and 'result' in data['chart']:
            result = data['chart']['result'][0]
            if 'meta' in result and 'regularMarketPrice' in result['meta']:
                price = float(result['meta']['regularMarketPrice'])
                return price, "Yahoo Finance"
        
        raise Exception("Yahoo Finance 가격 추출 실패")
        
    except Exception as e:
        log("DEBUG", f"Yahoo Finance 실패: {e}")
        raise

def fetch_current_price():
    """현재가 조회"""
    global latest_price, price_source
    
    try:
        price, source = get_yahoo_price()
        latest_price = price
        price_source = source
        return True
        
    except Exception as e:
        log("ERROR", f"가격 조회 실패: {e}")
        return False

# ==================== 메인 분석 로직 ====================
def analyze_market():
    """시장 분석 (복합 전략 + 변동성)"""
    # 캔들 데이터 업데이트
    if not update_candle_data():
        log("WARNING", "캔들 데이터 업데이트 실패")
        return
    
    # 현재가 업데이트
    if not fetch_current_price():
        log("WARNING", "현재가 조회 실패")
        return
    
    # 복합 전략 시그널 분석
    signal = analyze_trading_strategy()
    if signal:
        send_trading_signal(signal)
        strategy_data["last_signal"] = signal
        strategy_data["last_signal_time"] = datetime.now()
    
    # 변동성 체크
    volatility = check_volatility()
    if volatility:
        log("INFO", f"15분봉 {volatility['type']}: {volatility['percentage']:+.2f}% / 거래량 {volatility['volume_ratio']:.1f}배")

# ==================== 모니터링 스레드 ====================
def market_analyzer():
    """시장 분석 스레드 (실시간 대응)"""
    while True:
        try:
            session, session_status = get_market_session()
            
            # 세션별 분석 주기 조정
            if session == "REGULAR":
                # 정규장: 1분마다 (실시간)
                analyze_market()
                interval = 60
            elif session == "EXTENDED":
                # 장외 거래시간 (프리마켓/애프터마켓): 2분마다
                analyze_market()
                interval = 120
            else:
                # 완전 휴장시간: 30분마다 (최소 모니터링)
                analyze_market()
                interval = 1800  # 30분
            
            time.sleep(interval)
            
        except Exception as e:
            log("ERROR", f"시장 분석 오류: {e}")
            time.sleep(60)  # 오류 시 1분 후 재시도

def price_monitor():
    """가격 모니터링 (실시간 대응)"""
    while True:
        try:
            session, _ = get_market_session()
            
            # 세션별 가격 모니터링 주기
            if session == "REGULAR":
                # 정규장: 30초마다 (고빈도)
                fetch_current_price()
                interval = 30
            elif session == "EXTENDED":
                # 장외 거래시간: 1분마다
                fetch_current_price()
                interval = 60
            else:
                # 완전 휴장시간: 1시간마다 (최소 모니터링)
                fetch_current_price()
                interval = 3600  # 1시간
            
            time.sleep(interval)
            
        except Exception as e:
            log("ERROR", f"가격 모니터링 오류: {e}")
            time.sleep(60)

# ==================== 메인 함수 ====================
def main():
    """메인 실행 함수"""
    print("🚀 SOXL 완전한 트레이딩 시스템")
    print("=" * 60)
    
    # 환경변수 체크
    if not all([TELE_TOKEN, TELE_CHAT_ID]):
        log("ERROR", "텔레그램 설정이 필요합니다")
        return
    
    log("INFO", f"복합 전략 설정:")
    log("INFO", f"  RSI: 기간={RSI_PERIOD}, 과매수={RSI_OVERBOUGHT}, 과매도={RSI_OVERSOLD}")
    log("INFO", f"  EMA: 단기={EMA_SHORT}, 장기={EMA_LONG}")
    log("INFO", f"  슈퍼트렌드: 기간={SUPERTREND_PERIOD}, 승수={SUPERTREND_MULTIPLIER}")
    log("INFO", f"  변동성 임계치: {VOLATILITY_THRESHOLD}%, 거래량: {VOLUME_RATIO_THRESHOLD}배")
    
    # 초기 데이터 로드
    log("INFO", "초기 캔들 데이터 로딩...")
    if update_candle_data():
        log("INFO", f"캔들 데이터 {len(candle_data)}개 로드 완료")
    else:
        log("ERROR", "초기 캔들 데이터 로드 실패")
        return
    
    # 초기 가격 조회
    if fetch_current_price():
        log("INFO", f"현재가: ${latest_price:.2f}")
    else:
        log("ERROR", "초기 가격 조회 실패")
        return
    
    # 초기 지표 계산
    signal = analyze_trading_strategy()
    
    # 안전한 지표값 가져오기
    rsi_value = strategy_data.get("rsi")
    ema_short_value = strategy_data.get("ema_short")
    ema_long_value = strategy_data.get("ema_long")
    trend_value = strategy_data.get("supertrend_trend")
    
    if rsi_value:
        log("INFO", f"초기 지표 - RSI: {rsi_value:.1f}, 트렌드: {trend_value or 'N/A'}")
    
    # 시작 알림 (안전한 포맷팅)
    rsi_str = f"{rsi_value:.1f}" if rsi_value else "계산중"
    ema_short_str = f"${ema_short_value:.2f}" if ema_short_value else "계산중"
    ema_long_str = f"${ema_long_value:.2f}" if ema_long_value else "계산중"
    trend_str = trend_value if trend_value else "계산중"
    
    start_msg = f"""🚀 <b>SOXL 완전한 트레이딩 시스템 시작</b>

현재가: ${latest_price:.2f}
캔들 데이터: {len(candle_data)}개

<b>📊 복합 전략 구성</b>
• RSI({RSI_PERIOD}): {rsi_str}
• EMA{EMA_SHORT}: {ema_short_str}
• EMA{EMA_LONG}: {ema_long_str}
• 슈퍼트렌드: {trend_str}

<b>🚨 스마트 알림 설정</b>
• 매매 시그널: RSI+EMA+슈퍼트렌드
• 강한 추세: {VOLATILITY_THRESHOLD}%+ & 거래량 {VOLUME_RATIO_THRESHOLD}배+
• 세력 개입: 0.3%+ & 거래량 2배+
• 캔들: {CANDLE_INTERVAL}분봉

✅ 실시간 분석 시작!"""
    
    send_telegram(start_msg)
    
    # 백그라운드 스레드 시작
    analyzer_thread = threading.Thread(target=market_analyzer, daemon=True)
    analyzer_thread.start()
    
    price_thread = threading.Thread(target=price_monitor, daemon=True)
    price_thread.start()
    
    log("INFO", "모든 시스템 가동 완료")
    log("INFO", "Ctrl+C로 종료 가능")
    
    # 메인 루프 (실시간 상태 표시)
    try:
        while True:
            session, session_status = get_market_session()
            
            # 세션별 상태 표시 주기
            if session == "REGULAR":
                display_interval = 120   # 정규장: 2분마다
            elif session == "EXTENDED":
                display_interval = 300   # 장외 거래시간: 5분마다
            else:
                display_interval = 3600  # 완전 휴장시간: 1시간마다
            
            time.sleep(display_interval)
            
            if latest_price and strategy_data.get("rsi"):
                rsi = strategy_data["rsi"]
                trend = strategy_data.get("supertrend_trend", "N/A")
                log("INFO", f"{session_status} | SOXL ${latest_price:.2f} | RSI: {rsi:.1f} | ST: {trend}")
            
    except KeyboardInterrupt:
        log("INFO", "시스템 종료 중...")
        
        # 안전한 종료 메시지
        final_rsi = strategy_data.get("rsi")
        final_trend = strategy_data.get("supertrend_trend")
        
        rsi_str = f"{final_rsi:.1f}" if final_rsi else "N/A"
        trend_str = final_trend if final_trend else "N/A"
        price_str = f"{latest_price:.2f}" if latest_price else "0"
        
        stop_msg = f"""👋 <b>SOXL 트레이딩 시스템 종료</b>

종료 시간: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')}
최종 가격: ${price_str}
마지막 RSI: {rsi_str}
마지막 트렌드: {trend_str}

✅ 정상 종료"""
        
        send_telegram(stop_msg)
        log("INFO", "시스템 종료 완료")

if __name__ == "__main__":
    main()