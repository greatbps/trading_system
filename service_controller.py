#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/service_controller.py

백그라운드 모니터링 서비스 제어기 - 서비스 시작/중지/상태확인
"""

import asyncio
import sys
import os
import json
import subprocess
import psutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.logger import get_logger

class ServiceController:
    """백그라운드 모니터링 서비스 제어기"""
    
    def __init__(self):
        self.logger = get_logger("ServiceController")
        self.service_script = Path("D:/trading_system/background_monitoring_service.py")
        self.service_state_file = Path("D:/trading_system/data/service_state.json")
        self.pid_file = Path("D:/trading_system/data/service.pid")
        
    def get_service_status(self) -> Dict[str, Any]:
        """서비스 상태 확인"""
        try:
            # PID 파일 확인
            service_running = False
            pid = None
            
            if self.pid_file.exists():
                try:
                    with open(self.pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    
                    # 프로세스가 실제로 실행 중인지 확인
                    if psutil.pid_exists(pid):
                        proc = psutil.Process(pid)
                        if proc.is_running() and 'background_monitoring_service.py' in ' '.join(proc.cmdline()):
                            service_running = True
                except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 서비스 상태 파일 확인
            service_state = {}
            if self.service_state_file.exists():
                try:
                    with open(self.service_state_file, 'r', encoding='utf-8') as f:
                        service_state = json.load(f)
                except Exception as e:
                    self.logger.warning(f"⚠️ 서비스 상태 파일 읽기 실패: {e}")
            
            return {
                'service_running': service_running,
                'pid': pid,
                'service_state': service_state,
                'last_health_check': service_state.get('health_check'),
                'monitoring_active': service_state.get('monitoring_active', False)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 서비스 상태 확인 실패: {e}")
            return {'error': str(e)}
    
    async def start_service(self) -> bool:
        """백그라운드 서비스 시작"""
        try:
            status = self.get_service_status()
            if status.get('service_running'):
                self.logger.info("✅ 백그라운드 서비스가 이미 실행 중입니다")
                return True
            
            self.logger.info("🚀 백그라운드 모니터링 서비스 시작 중...")
            
            # 데이터 디렉토리 생성
            self.service_state_file.parent.mkdir(exist_ok=True)
            
            # 백그라운드에서 서비스 실행
            process = subprocess.Popen([
                sys.executable, str(self.service_script)
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # PID 저장
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # 잠시 대기 후 상태 확인
            await asyncio.sleep(3)
            
            status = self.get_service_status()
            if status.get('service_running'):
                self.logger.info(f"✅ 백그라운드 서비스 시작 완료 (PID: {process.pid})")
                return True
            else:
                self.logger.error("❌ 백그라운드 서비스 시작 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 백그라운드 서비스 시작 오류: {e}")
            return False
    
    async def stop_service(self) -> bool:
        """백그라운드 서비스 중지"""
        try:
            status = self.get_service_status()
            if not status.get('service_running'):
                self.logger.info("ℹ️ 백그라운드 서비스가 실행 중이 아닙니다")
                return True
            
            pid = status.get('pid')
            if pid:
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()  # 정상 종료 요청
                    
                    # 최대 10초 대기
                    try:
                        proc.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        proc.kill()  # 강제 종료
                    
                    self.logger.info(f"✅ 백그라운드 서비스 중지 완료 (PID: {pid})")
                    
                    # PID 파일 삭제
                    if self.pid_file.exists():
                        self.pid_file.unlink()
                    
                    return True
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    self.logger.warning(f"⚠️ 프로세스 종료 중 오류: {e}")
                    return True  # 이미 종료된 상태
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 백그라운드 서비스 중지 오류: {e}")
            return False
    
    async def restart_service(self) -> bool:
        """백그라운드 서비스 재시작"""
        try:
            self.logger.info("🔄 백그라운드 서비스 재시작 중...")
            
            # 먼저 중지
            await self.stop_service()
            await asyncio.sleep(2)
            
            # 다시 시작
            return await self.start_service()
            
        except Exception as e:
            self.logger.error(f"❌ 백그라운드 서비스 재시작 오류: {e}")
            return False
    
    def print_status(self):
        """서비스 상태 출력"""
        try:
            status = self.get_service_status()
            
            print("\n=== 백그라운드 모니터링 서비스 상태 ===")
            
            if status.get('error'):
                print(f"오류: {status['error']}")
                return
            
            service_running = status.get('service_running', False)
            pid = status.get('pid')
            service_state = status.get('service_state', {})
            
            print(f"서비스 실행 상태: {'실행 중' if service_running else '중지됨'}")
            
            if pid:
                print(f"프로세스 ID: {pid}")
            
            if service_state:
                print(f"서비스 상태: {service_state.get('status', '알 수 없음')}")
                
                # 시장 시간 정보 표시
                market_status_korean = service_state.get('market_status_korean', '알 수 없음')
                market_time_allowed = service_state.get('market_time_allowed', False)
                print(f"현재 시장 상태: {market_status_korean}")
                print(f"모니터링 허용 시간: {'예' if market_time_allowed else '아니오'}")
                
                monitoring_active = service_state.get('monitoring_active', False)
                print(f"모니터링 활성화: {'실행 중' if monitoring_active else '대기 중'}")
                
                if service_state.get('health_check'):
                    print(f"마지막 상태 확인: {service_state['health_check']}")
                
                if service_state.get('started_at'):
                    print(f"시작 시간: {service_state['started_at']}")
                    
                # 장 시간 정보 표시
                print(f"\n장 운영 시간 안내:")
                print(f"   정규 장: 09:00~15:30 (점심시간: 12:00~13:00)")  
                print(f"   모니터링: 장 시간에만 활성화")
                print(f"   휴장일: KIS API 기준 자동 적용")
            
            print("=" * 45)
            
        except Exception as e:
            print(f"상태 출력 오류: {e}")

async def main():
    """메인 함수"""
    controller = ServiceController()
    
    if len(sys.argv) < 2:
        print("사용법: python service_controller.py [start|stop|restart|status]")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        success = await controller.start_service()
        print("서비스 시작 완료" if success else "서비스 시작 실패")
        
    elif command == 'stop':
        success = await controller.stop_service()
        print("✅ 서비스 중지 완료" if success else "❌ 서비스 중지 실패")
        
    elif command == 'restart':
        success = await controller.restart_service()
        print("✅ 서비스 재시작 완료" if success else "❌ 서비스 재시작 실패")
        
    elif command == 'status':
        controller.print_status()
        
    else:
        print("지원되지 않는 명령입니다. [start|stop|restart|status]")

if __name__ == "__main__":
    asyncio.run(main())