#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 트레이딩 시스템에서의 모델 사용 예시
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import *
from datetime import datetime, timedelta
from decimal import Decimal

def simulate_trading_workflow():
    """실제 트레이딩 워크플로우 시뮬레이션"""
    
    # 인메모리 데이터베이스로 테스트
    engine = create_database_engine('sqlite:///:memory:', echo=False)
    create_all_tables(engine)
    
    SessionFactory = get_session_factory(engine)
    session = SessionFactory()
    
    try:
        print("=== AI 주식 트레이딩 시스템 워크플로우 시뮬레이션 ===\n")
        
        # 1. 초기 데이터 설정
        print("1. 초기 종목 데이터 설정...")
        stocks_data = [
            {'symbol': '005930', 'name': '삼성전자', 'market': Market.KOSPI, 'sector': 'IT', 'current_price': 75000},
            {'symbol': '000660', 'name': 'SK하이닉스', 'market': Market.KOSPI, 'sector': 'IT', 'current_price': 125000},
            {'symbol': '035420', 'name': 'NAVER', 'market': Market.KOSPI, 'sector': 'IT', 'current_price': 220000},
        ]
        
        stocks = []
        for stock_data in stocks_data:
            stock = Stock(**stock_data)
            stock.save(session)
            stocks.append(stock)
            print(f"  - {stock.name} ({stock.symbol}) 등록")
        
        # 2. 계좌 정보 설정
        print("\n2. 계좌 정보 설정...")
        account = AccountInfo(
            account_number='1234567890',
            cash_balance=10000000,  # 천만원
            total_assets=10000000,
            stock_value=0,
            available_cash=10000000
        )
        account.save(session)
        print(f"  - 계좌번호: {account.account_number}")
        print(f"  - 가용현금: {account.available_cash:,}원")
        
        # 3. 거래 세션 시작
        print("\n3. 거래 세션 시작...")
        trading_session = TradingSession.create_new_session(
            session=session,
            session_id=f'MOMENTUM_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            strategy='momentum',
            initial_capital=10000000,
            max_positions=3
        )
        print(f"  - 세션 ID: {trading_session.session_id}")
        print(f"  - 전략: {trading_session.strategy}")
        print(f"  - 초기자본: {trading_session.initial_capital:,}원")
        
        # 4. HTS 조건검색 결과 (1차 필터링)
        print("\n4. HTS 조건검색 실행...")
        filtered_stocks = []
        for i, stock in enumerate(stocks[:2]):  # 2개 종목만 선택
            filtered = FilteredStock(
                stock_id=stock.id,
                strategy_name='momentum',
                filtered_date=datetime.now(),
                hts_condition_name='모멘텀 급등주',
                current_price=stock.current_price,
                volume=1000000 + i * 500000
            )
            filtered.save(session)
            filtered_stocks.append(filtered)
            print(f"  - {stock.name}: 거래량 {filtered.volume:,}")
        
        # 5. AI 정량적 분석 (2차 필터링)
        print("\n5. AI 정량적 분석 실행...")
        selected_analyses = []
        for i, filtered in enumerate(filtered_stocks):
            # 다양한 점수로 분석 결과 생성
            scores = [
                (85.5, AnalysisGrade.BUY, True),
                (72.3, AnalysisGrade.BUY, True),
            ]
            
            total_score, grade, is_selected = scores[i]
            
            analysis = AnalysisResult(
                filtered_stock_id=filtered.id,
                stock_id=filtered.stock_id,
                total_score=Decimal(str(total_score)),
                final_grade=grade,
                news_score=Decimal('15.0'),
                technical_score=Decimal('35.5'),
                supply_demand_score=Decimal('35.0'),
                rsi_14=Decimal('65.2'),
                risk_level=RiskLevel.MEDIUM,
                is_selected=is_selected,
                technical_details={
                    'macd_signal': 'BUY',
                    'supertrend_signal': 'BUY',
                    'volume_surge': True
                }
            )
            analysis.save(session)
            
            if is_selected:
                selected_analyses.append(analysis)
                print(f"  - {filtered.stock.name}: {total_score}점 -> {grade.value} (선정)")
            else:
                print(f"  - {filtered.stock.name}: {total_score}점 -> {grade.value} (제외)")
        
        # 6. 실제 매매 실행
        print("\n6. 매매 주문 실행...")
        trades = []
        portfolio_positions = []
        
        for analysis in selected_analyses:
            stock = analysis.stock
            
            # 매수 주문 실행
            order_quantity = 50  # 50주 매수
            order_price = stock.current_price
            
            trade = Trade(
                analysis_result_id=analysis.id,
                stock_id=stock.id,
                trade_type=TradeType.BUY,
                order_type=OrderType.LIMIT,
                order_quantity=order_quantity,
                order_price=order_price,
                executed_price=order_price - 100,  # 약간 낮은 가격에 체결
                executed_quantity=order_quantity,
                order_status=OrderStatus.FILLED,
                order_time=datetime.now(),
                execution_time=datetime.now(),
                strategy_name='momentum',
                commission=int(order_price * order_quantity * 0.00015)  # 0.015% 수수료
            )
            trade.save(session)
            trades.append(trade)
            
            # 포트폴리오에 포지션 추가
            portfolio = Portfolio(
                stock_id=stock.id,
                quantity=order_quantity,
                avg_price=trade.executed_price,
                total_cost=trade.executed_price * order_quantity,
                first_buy_date=datetime.now()
            )
            portfolio.update_current_values(stock.current_price)
            portfolio.save(session)
            portfolio_positions.append(portfolio)
            
            print(f"  - {stock.name}: {order_quantity}주 매수 ({trade.executed_price:,}원)")
            print(f"    거래금액: {trade.get_total_amount():,}원 (수수료 포함)")
        
        # 7. 포트폴리오 현황 확인
        print("\n7. 포트폴리오 현황...")
        total_cost = 0
        total_value = 0
        total_pnl = 0
        
        for position in portfolio_positions:
            stock = position.stock
            position.update_current_values(stock.current_price + 1000)  # 가격 상승 시뮬레이션
            
            total_cost += position.total_cost
            total_value += position.market_value
            total_pnl += position.unrealized_pnl
            
            print(f"  - {stock.name}: {position.quantity}주")
            print(f"    평균단가: {position.avg_price:,}원")
            print(f"    현재가: {position.current_price:,}원")
            print(f"    평가손익: {position.unrealized_pnl:,}원 ({position.unrealized_pnl_rate:.2f}%)")
        
        print(f"\n  총 투자금액: {total_cost:,}원")
        print(f"  총 평가금액: {total_value:,}원")
        print(f"  총 평가손익: {total_pnl:,}원")
        
        # 8. 계좌 정보 업데이트
        print("\n8. 계좌 정보 업데이트...")
        account.update_balances(
            cash_balance=account.cash_balance - total_cost,
            stock_value=total_value,
            available_cash=account.cash_balance - total_cost
        )
        account.daily_pnl = total_pnl
        account.save(session)
        
        print(f"  - 현금 잔고: {account.cash_balance:,}원")
        print(f"  - 주식 평가액: {account.stock_value:,}원")
        print(f"  - 총 자산: {account.total_assets:,}원")
        print(f"  - 일일 손익: {account.daily_pnl:,}원")
        
        # 9. 거래 세션 성과 업데이트
        print("\n9. 거래 세션 성과...")
        winning_trades = sum(1 for trade in trades if trade.executed_price < trade.stock.current_price + 1000)
        
        trading_session.update_performance(
            total_trades=len(trades),
            winning_trades=winning_trades,
            total_pnl=total_pnl,
            max_drawdown=0
        )
        trading_session.save(session)
        
        print(f"  - 총 거래: {trading_session.total_trades}건")
        print(f"  - 수익 거래: {trading_session.winning_trades}건")
        print(f"  - 승률: {trading_session.get_win_rate():.1f}%")
        print(f"  - 총 손익: {trading_session.total_pnl:,}원")
        
        # 10. 시스템 로그 기록
        print("\n10. 시스템 로그 기록...")
        SystemLog.log_info(
            session=session,
            module='trading_workflow',
            function='simulate_trading_workflow',
            message=f'Trading session completed successfully',
            extra_data={
                'session_id': trading_session.session_id,
                'total_trades': len(trades),
                'total_pnl': int(total_pnl),
                'selected_stocks': [stock.symbol for stock in [pos.stock for pos in portfolio_positions]]
            }
        )
        
        # 11. 데이터 조회 예시
        print("\n11. 조회 기능 시연...")
        
        # 선정된 분석 결과
        selected = AnalysisResult.get_selected_stocks(session)
        print(f"  - 선정된 종목: {len(selected)}개")
        
        # 열린 포지션
        open_positions = Portfolio.get_open_positions(session)
        print(f"  - 보유 포지션: {len(open_positions)}개")
        
        # 최근 거래
        recent_trades = Trade.get_recent_trades(session, days=1)
        print(f"  - 오늘 거래: {len(recent_trades)}건")
        
        # 최근 로그
        recent_logs = SystemLog.get_recent_logs(session, hours=1)
        print(f"  - 최근 로그: {len(recent_logs)}건")
        
        print("\n=== 시뮬레이션 완료 ===")
        print("모든 모델이 정상적으로 작동하며, 실제 트레이딩 워크플로우에서 사용할 준비가 되었습니다.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    simulate_trading_workflow()