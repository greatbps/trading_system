#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web_dashboard_api.py

웹 대시보드를 위한 REST API 엔드포인트
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

# FastAPI 및 관련 라이브러리
try:
    from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    # Mock classes for when FastAPI is not available
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Field:
        def __init__(self, *args, **kwargs):
            pass

    class FastAPI:
        def __init__(self, *args, **kwargs):
            self.routes = []

        def get(self, path):
            def decorator(func):
                self.routes.append(type('Route', (), {'path': path, 'func': func}))
                return func
            return decorator

        def post(self, path):
            def decorator(func):
                self.routes.append(type('Route', (), {'path': path, 'func': func}))
                return func
            return decorator

# Core components
from core.dynamic_settings_manager import DynamicSettingsManager, TradingSettings
from backtesting.enhanced_visualizer import EnhancedVisualizer
from monitoring.notification_system import NotificationSystem, NotificationConfig
from utils.logger import get_logger

logger = get_logger("WebDashboardAPI")

# API 모델 정의
class BalanceUpdate(BaseModel):
    """잔고 업데이트 요청"""
    total_balance: float = Field(..., gt=0, description="총 잔고")
    cash_balance: float = Field(..., ge=0, description="현금 잔고")
    stock_value: float = Field(..., ge=0, description="주식 평가액")

class TradingSettingsResponse(BaseModel):
    """거래 설정 응답"""
    position_size_ratio: float
    max_positions: int
    stop_loss_pct: float
    take_profit_pct: float
    risk_level: str
    min_cash_reserve: float
    max_daily_trades: int
    volatility_adjustment: float

class BalanceSummaryResponse(BaseModel):
    """잔고 요약 응답"""
    status: str
    latest_balance: Optional[float] = None
    latest_pnl: Optional[float] = None
    latest_pnl_pct: Optional[float] = None
    cash_ratio: Optional[float] = None
    stock_ratio: Optional[float] = None
    record_count: int = 0
    current_risk_level: str = "medium"

class NotificationRequest(BaseModel):
    """알림 요청"""
    event_type: str
    title: str
    message: str
    level: str = "info"
    metadata: Optional[Dict[str, Any]] = None

class APIResponse(BaseModel):
    """일반 API 응답"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class TradingSystemAPI:
    """거래 시스템 웹 API"""

    def __init__(self, config=None):
        """API 초기화"""
        self.config = config
        self.logger = get_logger("TradingSystemAPI")

        # 핵심 컴포넌트 초기화
        self.settings_manager = DynamicSettingsManager(config)
        self.visualizer = EnhancedVisualizer(config)
        self.notification_system = NotificationSystem()

        # FastAPI 앱 초기화
        if FASTAPI_AVAILABLE:
            self.app = FastAPI(
                title="AI Trading System API",
                description="동적 설정 조정 및 시각화를 위한 REST API",
                version="1.0.0"
            )
            self._setup_middleware()
            self._setup_routes()
            self._setup_websocket()
        else:
            self.app = None
            self.logger.warning("⚠️ FastAPI가 설치되지 않아 웹 API를 사용할 수 없습니다")

        # 웹소켓 연결 관리
        self.websocket_connections: List[WebSocket] = []

    def _setup_middleware(self):
        """미들웨어 설정"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 실제 환경에서는 구체적인 도메인으로 제한
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """API 라우트 설정"""

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """메인 대시보드 페이지"""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>AI Trading System Dashboard</title>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .card { background: #f8f9fa; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    .metric { display: inline-block; margin: 10px; padding: 15px; background: white; border-radius: 5px; text-align: center; }
                    .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
                    .metric-label { font-size: 14px; color: #666; }
                    button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
                    button:hover { background: #0056b3; }
                    #status { margin: 20px 0; padding: 10px; border-radius: 5px; }
                    .success { background: #d4edda; color: #155724; }
                    .error { background: #f8d7da; color: #721c24; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 AI Trading System Dashboard</h1>

                    <div class="card">
                        <h2>현재 설정</h2>
                        <div id="settings">로딩 중...</div>
                        <button onclick="loadSettings()">설정 새로고침</button>
                    </div>

                    <div class="card">
                        <h2>잔고 현황</h2>
                        <div id="balance">로딩 중...</div>
                        <button onclick="loadBalance()">잔고 새로고침</button>
                    </div>

                    <div class="card">
                        <h2>잔고 업데이트</h2>
                        <input type="number" id="totalBalance" placeholder="총 잔고" step="1000">
                        <input type="number" id="cashBalance" placeholder="현금 잔고" step="1000">
                        <input type="number" id="stockValue" placeholder="주식 평가액" step="1000">
                        <button onclick="updateBalance()">잔고 업데이트</button>
                    </div>

                    <div class="card">
                        <h2>테스트 알림</h2>
                        <button onclick="sendTestNotification()">테스트 알림 발송</button>
                    </div>

                    <div id="status"></div>
                </div>

                <script>
                    const API_BASE = '';

                    async function apiCall(endpoint, method = 'GET', data = null) {
                        const options = {
                            method,
                            headers: { 'Content-Type': 'application/json' }
                        };
                        if (data) options.body = JSON.stringify(data);

                        const response = await fetch(API_BASE + endpoint, options);
                        return await response.json();
                    }

                    function showStatus(message, isError = false) {
                        const status = document.getElementById('status');
                        status.textContent = message;
                        status.className = isError ? 'error' : 'success';
                        setTimeout(() => status.textContent = '', 5000);
                    }

                    async function loadSettings() {
                        try {
                            const result = await apiCall('/api/settings');
                            if (result.success) {
                                const settings = result.data;
                                document.getElementById('settings').innerHTML = `
                                    <div class="metric">
                                        <div class="metric-value">${(settings.position_size_ratio * 100).toFixed(1)}%</div>
                                        <div class="metric-label">포지션 크기</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-value">${settings.max_positions}</div>
                                        <div class="metric-label">최대 포지션</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-value">${settings.stop_loss_pct}%</div>
                                        <div class="metric-label">손절 비율</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-value">${settings.risk_level}</div>
                                        <div class="metric-label">리스크 레벨</div>
                                    </div>
                                `;
                                showStatus('설정 로드 완료');
                            }
                        } catch (error) {
                            showStatus('설정 로드 실패: ' + error.message, true);
                        }
                    }

                    async function loadBalance() {
                        try {
                            const result = await apiCall('/api/balance/summary');
                            if (result.success) {
                                const balance = result.data;
                                if (balance.status === 'available') {
                                    document.getElementById('balance').innerHTML = `
                                        <div class="metric">
                                            <div class="metric-value">₩${balance.latest_balance.toLocaleString()}</div>
                                            <div class="metric-label">총 자산</div>
                                        </div>
                                        <div class="metric">
                                            <div class="metric-value">${balance.latest_pnl_pct.toFixed(2)}%</div>
                                            <div class="metric-label">수익률</div>
                                        </div>
                                        <div class="metric">
                                            <div class="metric-value">${(balance.cash_ratio * 100).toFixed(1)}%</div>
                                            <div class="metric-label">현금 비율</div>
                                        </div>
                                        <div class="metric">
                                            <div class="metric-value">${balance.current_risk_level}</div>
                                            <div class="metric-label">리스크 레벨</div>
                                        </div>
                                    `;
                                } else {
                                    document.getElementById('balance').innerHTML = '<p>잔고 데이터가 없습니다.</p>';
                                }
                                showStatus('잔고 정보 로드 완료');
                            }
                        } catch (error) {
                            showStatus('잔고 로드 실패: ' + error.message, true);
                        }
                    }

                    async function updateBalance() {
                        const totalBalance = parseFloat(document.getElementById('totalBalance').value);
                        const cashBalance = parseFloat(document.getElementById('cashBalance').value);
                        const stockValue = parseFloat(document.getElementById('stockValue').value);

                        if (!totalBalance || !cashBalance || stockValue === null) {
                            showStatus('모든 값을 입력해주세요', true);
                            return;
                        }

                        try {
                            const result = await apiCall('/api/balance/update', 'POST', {
                                total_balance: totalBalance,
                                cash_balance: cashBalance,
                                stock_value: stockValue
                            });

                            if (result.success) {
                                showStatus('잔고 업데이트 완료');
                                loadSettings();
                                loadBalance();
                                // 입력 필드 초기화
                                document.getElementById('totalBalance').value = '';
                                document.getElementById('cashBalance').value = '';
                                document.getElementById('stockValue').value = '';
                            }
                        } catch (error) {
                            showStatus('잔고 업데이트 실패: ' + error.message, true);
                        }
                    }

                    async function sendTestNotification() {
                        try {
                            const result = await apiCall('/api/notifications/test', 'POST');
                            if (result.success) {
                                showStatus('테스트 알림 발송 완료');
                            }
                        } catch (error) {
                            showStatus('알림 발송 실패: ' + error.message, true);
                        }
                    }

                    // 페이지 로드 시 초기 데이터 로드
                    window.onload = function() {
                        loadSettings();
                        loadBalance();
                    };
                </script>
            </body>
            </html>
            """

        @self.app.get("/api/settings", response_model=APIResponse)
        async def get_settings():
            """현재 거래 설정 조회"""
            try:
                settings = await self.settings_manager.get_current_settings()
                return APIResponse(
                    success=True,
                    message="설정 조회 성공",
                    data=settings.__dict__
                )
            except Exception as e:
                logger.error(f"설정 조회 실패: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/balance/summary", response_model=APIResponse)
        async def get_balance_summary():
            """잔고 요약 정보 조회"""
            try:
                summary = await self.settings_manager.get_balance_summary()
                return APIResponse(
                    success=True,
                    message="잔고 요약 조회 성공",
                    data=summary
                )
            except Exception as e:
                logger.error(f"잔고 요약 조회 실패: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/balance/update", response_model=APIResponse)
        async def update_balance(balance_update: BalanceUpdate, background_tasks: BackgroundTasks):
            """잔고 업데이트 및 설정 조정"""
            try:
                new_settings, adjustment_info = await self.settings_manager.update_balance_and_adjust_settings(
                    current_balance=balance_update.total_balance,
                    cash_balance=balance_update.cash_balance,
                    stock_value=balance_update.stock_value
                )

                # 웹소켓으로 실시간 업데이트 전송
                background_tasks.add_task(
                    self._broadcast_update,
                    {
                        "type": "balance_updated",
                        "settings": new_settings.__dict__,
                        "adjustment_info": adjustment_info
                    }
                )

                return APIResponse(
                    success=True,
                    message="잔고 업데이트 및 설정 조정 완료",
                    data={
                        "new_settings": new_settings.__dict__,
                        "adjustment_info": adjustment_info
                    }
                )
            except Exception as e:
                logger.error(f"잔고 업데이트 실패: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/notifications/send", response_model=APIResponse)
        async def send_notification(notification: NotificationRequest):
            """알림 발송"""
            try:
                from monitoring.notification_system import NotificationLevel

                level_map = {
                    "info": NotificationLevel.INFO,
                    "warning": NotificationLevel.WARNING,
                    "error": NotificationLevel.ERROR,
                    "critical": NotificationLevel.CRITICAL
                }

                await self.notification_system.notify(
                    event_type=notification.event_type,
                    title=notification.title,
                    message=notification.message,
                    level=level_map.get(notification.level, NotificationLevel.INFO),
                    metadata=notification.metadata
                )

                return APIResponse(
                    success=True,
                    message="알림 발송 완료"
                )
            except Exception as e:
                logger.error(f"알림 발송 실패: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/notifications/test", response_model=APIResponse)
        async def test_notifications():
            """테스트 알림 발송"""
            try:
                await self.notification_system.test_notifications()
                return APIResponse(
                    success=True,
                    message="테스트 알림 발송 완료"
                )
            except Exception as e:
                logger.error(f"테스트 알림 실패: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/dashboard/data", response_model=APIResponse)
        async def get_dashboard_data():
            """대시보드 데이터 조회"""
            try:
                # 설정 정보
                settings = await self.settings_manager.get_current_settings()
                balance_summary = await self.settings_manager.get_balance_summary()

                dashboard_data = {
                    "settings": settings.__dict__,
                    "balance": balance_summary,
                    "timestamp": datetime.now().isoformat()
                }

                return APIResponse(
                    success=True,
                    message="대시보드 데이터 조회 성공",
                    data=dashboard_data
                )
            except Exception as e:
                logger.error(f"대시보드 데이터 조회 실패: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/health")
        async def health_check():
            """헬스 체크"""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    def get_portfolio_summary(self):
        """포트폴리오 요약 정보 반환"""
        try:
            # 기본 포트폴리오 요약 정보 생성
            summary = {
                "total_value": 0.0,
                "cash_balance": 0.0,
                "stock_value": 0.0,
                "daily_pnl": 0.0,
                "daily_pnl_pct": 0.0,
                "positions": 0,
                "timestamp": datetime.now().isoformat()
            }
            return summary
        except Exception as e:
            self.logger.error(f"포트폴리오 요약 생성 실패: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_trading_settings(self):
        """현재 거래 설정 반환"""
        try:
            settings = await self.settings_manager.get_current_settings()
            return settings
        except Exception as e:
            self.logger.error(f"거래 설정 조회 실패: {e}")
            return TradingSettings()  # 기본 설정 반환

    def _setup_websocket(self):
        """웹소켓 설정"""
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)

            try:
                while True:
                    # 클라이언트로부터 메시지 대기
                    data = await websocket.receive_text()
                    # 필요시 메시지 처리 로직 추가

            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)

    async def _broadcast_update(self, data: Dict[str, Any]):
        """웹소켓으로 실시간 업데이트 브로드캐스트"""
        if not self.websocket_connections:
            return

        message = json.dumps(data, default=str)
        disconnected = []

        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)

        # 연결이 끊어진 웹소켓 제거
        for websocket in disconnected:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)

    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        """API 서버 시작"""
        if not FASTAPI_AVAILABLE:
            logger.error("❌ FastAPI가 설치되지 않아 웹 서버를 시작할 수 없습니다")
            return

        try:
            # 알림 시스템 시작
            await self.notification_system.start()

            logger.info(f"🚀 웹 대시보드 API 서버 시작: http://{host}:{port}")

            # 개발 환경에서만 자동 리로드 활성화
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info",
                reload=False  # 실제 환경에서는 False
            )

            server = uvicorn.Server(config)
            await server.serve()

        except Exception as e:
            logger.error(f"❌ API 서버 시작 실패: {e}")

    async def stop(self):
        """API 서버 정지"""
        try:
            await self.notification_system.stop()
            logger.info("✅ 웹 대시보드 API 서버 정지 완료")
        except Exception as e:
            logger.error(f"❌ API 서버 정지 실패: {e}")

# 편의 함수
def create_api_server(config=None) -> TradingSystemAPI:
    """API 서버 생성"""
    return TradingSystemAPI(config)

# 메인 실행 함수
async def main():
    """API 서버 실행"""
    if not FASTAPI_AVAILABLE:
        print("❌ FastAPI가 설치되지 않았습니다. 다음 명령어로 설치하세요:")
        print("pip install fastapi uvicorn")
        return

    # API 서버 생성 및 시작
    api_server = create_api_server()

    try:
        await api_server.start(host="127.0.0.1", port=8000)
    except KeyboardInterrupt:
        print("\n👋 사용자가 서버를 중단했습니다.")
        await api_server.stop()

if __name__ == "__main__":
    asyncio.run(main())