#!/usr/bin/env python3
"""
KIS API 오늘자 거래내역 조회 및 DB 동기화
오늘 매도한 종목들의 실제 체결가격을 KIS API에서 가져와 DB와 동기화
"""

import asyncio
import sys
import os
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional

# 프로젝트 루트 경로 추가
sys.path.append('D:/trading_system')

try:
    from data_collectors.kis_collector import KISCollector
    from database.database_manager import DatabaseManager
    from database.models import Trade, Stock, TradeType
    from config import Config
    print("[OK] 모든 모듈 import 성공")
except ImportError as e:
    print(f"[ERROR] Import 실패: {e}")
    sys.exit(1)

class TradingHistorySyncer:
    def __init__(self):
        self.config = Config()
        self.kis_collector = KISCollector(self.config)
        self.db_manager = DatabaseManager(self.config)
        
    async def get_today_trading_history(self) -> List[Dict[str, Any]]:
        """
        KIS API를 통해 오늘자 주문체결내역 조회
        """
        try:
            # 오늘 날짜 문자열
            today_str = datetime.now().strftime('%Y%m%d')
            
            # API 요청 파라미터
            params = {
                'CANO': self.config.api.KIS_ACCOUNT_NUMBER[:8],  # 계좌번호 앞 8자리
                'ACNT_PRDT_CD': self.config.api.KIS_ACCOUNT_NUMBER[-2:],  # 계좌번호 뒤 2자리
                'INQR_STRT_DT': today_str,  # 조회시작일자
                'INQR_END_DT': today_str,   # 조회종료일자
                'SLL_BUY_DVSN_CD': '00',    # 매매구분코드 (00:전체, 01:매도, 02:매수)
                'INQR_DVSN': '00',          # 조회구분 (00:역순, 01:정순)
                'PDNO': '',                 # 상품번호 (종목번호, 공백시 전체)
                'CCLD_DVSN': '00',          # 체결구분 (00:전체)
                'ORD_GNO_BRNO': '',         # 주문채번지점번호
                'ODNO': '',                 # 주문번호
                'INQR_DVSN_3': '00',        # 조회구분3 (00:전체)
                'INQR_DVSN_1': '',          # 조회구분1
                'CTX_AREA_FK100': '',       # 연속조회검색조건100
                'CTX_AREA_NK100': ''        # 연속조회키100
            }
            
            # KISCollector의 _make_api_request 메소드 사용
            data = await self.kis_collector._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
                params=params,
                tr_id="TTTC0081R"  # 3개월 이내 체결내역 조회
            )
            
            if data and data.get('rt_cd') == '0':
                print(f"[OK] KIS API 호출 성공: {len(data.get('output1', []))}건 조회")
                return data.get('output1', [])
            else:
                error_msg = data.get('msg1') if data else 'API 응답 없음'
                print(f"[ERROR] KIS API 오류: {error_msg}")
                return []
                
        except Exception as e:
            print(f"[ERROR] 거래내역 조회 실패: {e}")
            return []
    
    def parse_trading_history(self, history_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        KIS API 응답 데이터를 파싱하여 필요한 정보 추출
        """
        parsed_trades = []
        
        for item in history_data:
            try:
                # 매매구분 확인 (매도만 처리)
                if item.get('sll_buy_dvsn_cd') != '01':  # 01: 매도
                    continue
                    
                trade_info = {
                    'stock_code': item.get('pdno', '').zfill(6),    # 종목코드
                    'stock_name': item.get('prdt_name', ''),        # 종목명
                    'order_id': item.get('odno', ''),               # 주문번호
                    'order_date': item.get('ord_dt', ''),           # 주문일자
                    'order_time': item.get('ord_tmd', ''),          # 주문시각
                    'order_quantity': int(item.get('ord_qty', '0')),        # 주문수량
                    'ccld_quantity': int(item.get('tot_ccld_qty', '0')),    # 총체결수량
                    'order_price': int(item.get('ord_unpr', '0')),          # 주문단가
                    'ccld_price': int(item.get('avg_prvs', '0')),           # 평균체결가
                    'ccld_amount': int(item.get('tot_ccld_amt', '0')),      # 총체결금액
                    'ord_dvsn_name': item.get('ord_dvsn_name', ''),         # 주문구분명
                    'ccld_cndt_name': item.get('ccld_cndt_name', ''),       # 체결조건명
                }
                
                parsed_trades.append(trade_info)
                
            except (ValueError, TypeError) as e:
                print(f"[WARNING] 거래내역 파싱 오류: {e}, 데이터: {item}")
                continue
        
        return parsed_trades
    
    async def sync_database_trades(self, parsed_trades: List[Dict[str, Any]]):
        """
        DB의 Trade 레코드들을 KIS API 데이터와 동기화
        """
        if not parsed_trades:
            print("[INFO] 동기화할 거래내역이 없습니다.")
            return
            
        with self.db_manager.get_session() as session:
            try:
                # 오늘 날짜의 매도 Trade 레코드들 조회
                today = date.today()
                from sqlalchemy import and_, func
                
                # 오늘 날짜 범위 계산
                start_of_today = datetime.combine(today, datetime.min.time())
                end_of_today = datetime.combine(today, datetime.max.time())
                
                sell_trades = session.query(Trade).filter(
                    and_(
                        Trade.order_time >= start_of_today,
                        Trade.order_time <= end_of_today,
                        Trade.trade_type == TradeType.SELL
                    )
                ).all()
                
                print(f"[INFO] DB에서 {len(sell_trades)}개의 매도 거래 조회")
                print(f"[INFO] KIS API에서 {len(parsed_trades)}개의 체결내역 조회")
                
                # 동기화 통계
                updated_count = 0
                missing_count = 0
                
                # KIS API 데이터로 DB 업데이트
                for api_trade in parsed_trades:
                    stock_code = api_trade['stock_code']
                    order_id = api_trade['order_id']
                    
                    # 매칭되는 DB Trade 레코드 찾기 (종목코드 기준)
                    matching_trade = None
                    for db_trade in sell_trades:
                        # Stock 테이블 조인으로 symbol 확인
                        if db_trade.stock.symbol == stock_code:
                            matching_trade = db_trade
                            break
                    
                    if matching_trade:
                        # 가격 정보 업데이트
                        old_order_price = matching_trade.order_price
                        old_executed_price = matching_trade.executed_price
                        
                        matching_trade.order_price = Decimal(str(api_trade['order_price']))
                        matching_trade.executed_price = Decimal(str(api_trade['ccld_price']))
                        matching_trade.order_id = api_trade['order_id']
                        
                        print(f"[UPDATE] {stock_code} ({api_trade['stock_name']})")
                        print(f"  주문가격: {old_order_price} -> {matching_trade.order_price}")
                        print(f"  체결가격: {old_executed_price} -> {matching_trade.executed_price}")
                        print(f"  주문번호: {api_trade['order_id']}")
                        
                        updated_count += 1
                    else:
                        print(f"[MISSING] KIS 체결내역에 있지만 DB에 없는 거래: {stock_code} ({api_trade['stock_name']})")
                        missing_count += 1
                
                # Stock 테이블의 종목명도 업데이트
                for api_trade in parsed_trades:
                    stock_code = api_trade['stock_code']
                    stock_name = api_trade['stock_name']
                    
                    if stock_name and not stock_name.startswith('종목'):
                        stock = session.query(Stock).filter(Stock.symbol == stock_code).first()
                        if stock and stock.name != stock_name:
                            old_name = stock.name
                            stock.name = stock_name
                            print(f"[UPDATE] Stock 종목명: {stock_code} {old_name} -> {stock_name}")
                
                # 변경사항 커밋
                session.commit()
                
                print(f"\n[SUMMARY] 동기화 완료:")
                print(f"  업데이트된 거래: {updated_count}건")
                print(f"  DB에 없는 거래: {missing_count}건")
                
            except Exception as e:
                session.rollback()
                print(f"[ERROR] DB 동기화 실패: {e}")
                raise e
    
    async def run_sync(self):
        """
        전체 동기화 프로세스 실행
        """
        print("=== KIS API 거래내역 동기화 시작 ===")
        
        async with self.kis_collector:  # async context manager 사용
            # 1. KIS API에서 오늘자 거래내역 조회
            print("[1] KIS API에서 오늘자 거래내역 조회 중...")
            history_data = await self.get_today_trading_history()
            
            if not history_data:
                print("[INFO] 오늘자 거래내역이 없습니다.")
                return
            
            # 2. 거래내역 데이터 파싱
            print("[2] 거래내역 데이터 파싱 중...")
            parsed_trades = self.parse_trading_history(history_data)
            
            if not parsed_trades:
                print("[INFO] 매도 거래내역이 없습니다.")
                return
            
            # 3. 파싱된 거래내역 출력
            print(f"[3] 파싱된 매도 거래내역 ({len(parsed_trades)}건):")
            for trade in parsed_trades:
                print(f"  {trade['stock_code']} {trade['stock_name']}: "
                      f"{trade['ccld_quantity']}주 @ {trade['ccld_price']:,}원")
            
            # 4. DB와 동기화
            print("[4] DB와 동기화 중...")
            await self.sync_database_trades(parsed_trades)
            
            print("=== 동기화 완료 ===")

async def main():
    syncer = TradingHistorySyncer()
    await syncer.run_sync()

if __name__ == "__main__":
    asyncio.run(main())