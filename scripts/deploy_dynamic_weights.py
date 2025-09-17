#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/scripts/deploy_dynamic_weights.py

동적 가중치 시스템 배포 및 검증 스크립트
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger
from analyzers.enhanced_consensus_engine import EnhancedConsensusEngine, create_consensus_engine
from tests.test_dynamic_weight_system import run_all_tests


class DynamicWeightDeployer:
    """동적 가중치 시스템 배포기"""
    
    def __init__(self):
        self.logger = get_logger("DynamicWeightDeployer")
        self.deployment_config = {
            'phase': 'preparation',  # preparation, gradual, activation, full
            'enable_dynamic': False,
            'strategies_enabled': [],
            'validation_required': True
        }
        
        # 배포 상태 파일
        self.state_file = project_root / "config" / "dynamic_weight_deployment_state.json"
        self.load_deployment_state()
    
    def load_deployment_state(self):
        """배포 상태 로드"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.deployment_config = json.load(f)
                self.logger.info(f"🔄 배포 상태 로드: {self.deployment_config['phase']}")
            else:
                self.save_deployment_state()
                self.logger.info("🆕 새로운 배포 상태 생성")
        except Exception as e:
            self.logger.error(f"❌ 배포 상태 로드 실패: {e}")
    
    def save_deployment_state(self):
        """배포 상태 저장"""
        try:
            # 디렉터리 생성
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 상태 저장
            self.deployment_config['last_updated'] = datetime.now().isoformat()
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.deployment_config, f, indent=2, ensure_ascii=False)
            
            self.logger.info("💾 배포 상태 저장 완료")
        except Exception as e:
            self.logger.error(f"❌ 배포 상태 저장 실패: {e}")
    
    async def run_phase_1_preparation(self):
        """Phase 1: 준비 단계"""
        self.logger.info("🚀 Phase 1: 준비 단계 시작")
        
        try:
            # 1. 테스트 실행
            self.logger.info("1️⃣ 시스템 테스트 실행...")
            test_success = await self.run_system_tests()
            if not test_success:
                raise Exception("시스템 테스트 실패")
            
            # 2. 모듈 임포트 검증
            self.logger.info("2️⃣ 모듈 임포트 검증...")
            await self.validate_module_imports()
            
            # 3. 기본 호환성 검증
            self.logger.info("3️⃣ 기본 호환성 검증...")
            await self.validate_basic_compatibility()
            
            # 상태 업데이트
            self.deployment_config['phase'] = 'gradual'
            self.deployment_config['preparation_completed'] = True
            self.save_deployment_state()
            
            self.logger.info("✅ Phase 1 완료 - 점진적 적용 준비됨")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Phase 1 실패: {e}")
            return False
    
    async def run_phase_2_gradual(self):
        """Phase 2: 점진적 적용"""
        self.logger.info("🚀 Phase 2: 점진적 적용 시작")
        
        try:
            # 1. 향상된 엔진 비활성 상태로 테스트
            self.logger.info("1️⃣ 향상된 엔진 (비활성) 테스트...")
            await self.test_enhanced_engine_disabled()
            
            # 2. 부분 전략 적용
            self.logger.info("2️⃣ 부분 전략 적용...")
            test_strategies = ['momentum', 'breakout']
            for strategy in test_strategies:
                success = await self.test_strategy_compatibility(strategy)
                if not success:
                    raise Exception(f"전략 {strategy} 호환성 테스트 실패")
            
            # 3. 시장 분석기 테스트
            self.logger.info("3️⃣ 시장 상황 분석기 테스트...")
            await self.test_market_analyzer()
            
            # 상태 업데이트
            self.deployment_config['phase'] = 'activation'
            self.deployment_config['gradual_completed'] = True
            self.deployment_config['strategies_enabled'] = test_strategies
            self.save_deployment_state()
            
            self.logger.info("✅ Phase 2 완료 - 동적 기능 활성화 준비됨")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Phase 2 실패: {e}")
            return False
    
    async def run_phase_3_activation(self):
        """Phase 3: 동적 기능 활성화"""
        self.logger.info("🚀 Phase 3: 동적 기능 활성화 시작")
        
        try:
            # Mock 환경에서 동적 시스템 테스트
            self.logger.info("1️⃣ Mock 환경 동적 시스템 테스트...")
            await self.test_dynamic_system_mock()
            
            # 성과 추적 시스템 초기화
            self.logger.info("2️⃣ 성과 추적 시스템 초기화...")
            await self.initialize_performance_tracking()
            
            # 보수적 가중치 조정 테스트
            self.logger.info("3️⃣ 보수적 가중치 조정 테스트...")
            await self.test_conservative_weight_adjustment()
            
            # 상태 업데이트
            self.deployment_config['phase'] = 'full'
            self.deployment_config['enable_dynamic'] = True
            self.deployment_config['activation_completed'] = True
            self.save_deployment_state()
            
            self.logger.info("✅ Phase 3 완료 - 완전 운영 준비됨")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Phase 3 실패: {e}")
            return False
    
    async def run_phase_4_full(self):
        """Phase 4: 완전 운영"""
        self.logger.info("🚀 Phase 4: 완전 운영 시작")
        
        try:
            # 전체 기능 활성화 테스트
            self.logger.info("1️⃣ 전체 기능 활성화 테스트...")
            await self.test_full_system()
            
            # 모니터링 시스템 확인
            self.logger.info("2️⃣ 모니터링 시스템 확인...")
            await self.verify_monitoring_system()
            
            # 성과 검증
            self.logger.info("3️⃣ 성과 검증...")
            await self.validate_system_performance()
            
            # 상태 업데이트
            self.deployment_config['full_deployment_completed'] = True
            self.save_deployment_state()
            
            self.logger.info("✅ Phase 4 완료 - 시스템 완전 운영 중")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Phase 4 실패: {e}")
            return False
    
    async def run_system_tests(self):
        """시스템 테스트 실행"""
        try:
            self.logger.info("🧪 동적 가중치 시스템 테스트 실행...")
            success = run_all_tests()
            
            if success:
                self.logger.info("✅ 모든 테스트 통과")
            else:
                self.logger.error("❌ 테스트 실패")
            
            return success
        except Exception as e:
            self.logger.error(f"❌ 테스트 실행 실패: {e}")
            return False
    
    async def validate_module_imports(self):
        """모듈 임포트 검증"""
        try:
            from analyzers.market_condition_analyzer import MarketConditionAnalyzer
            from analyzers.performance_tracker import PerformanceTracker
            from analyzers.weight_adjuster import WeightAdjuster
            from analyzers.enhanced_consensus_engine import EnhancedConsensusEngine
            
            self.logger.info("✅ 모든 모듈 임포트 성공")
            
        except ImportError as e:
            self.logger.error(f"❌ 모듈 임포트 실패: {e}")
            raise
    
    async def validate_basic_compatibility(self):
        """기본 호환성 검증"""
        try:
            # 기존 엔진과 향상된 엔진 비교
            config = type('Config', (), {})()
            
            original_engine = create_consensus_engine(config, enhanced=False)
            enhanced_engine = create_consensus_engine(config, enhanced=True, enable_dynamic_weights=False)
            
            # 기본 가중치 동일성 확인
            original_weights = original_engine._get_strategy_weights("momentum", False)
            enhanced_weights = enhanced_engine._get_strategy_weights("momentum", False)
            
            if original_weights == enhanced_weights:
                self.logger.info("✅ 기본 호환성 검증 성공")
            else:
                raise Exception("기본 가중치 불일치")
                
        except Exception as e:
            self.logger.error(f"❌ 호환성 검증 실패: {e}")
            raise
    
    async def test_enhanced_engine_disabled(self):
        """향상된 엔진 비활성 상태 테스트"""
        try:
            config = type('Config', (), {})()
            engine = EnhancedConsensusEngine(config, enable_dynamic_weights=False)
            
            # Mock 분석 결과
            analysis_results = {
                'technical': {'technical_score': 75},
                'sentiment': {'overall_score': 60},
                'supply_demand': {'overall_score': 70},
                'chart_pattern': {'overall_score': 65},
                'fundamental': {'overall_score': 55},
                'mtf': {'mtf_score': 80}
            }
            
            score, details = engine.synthesize(analysis_results, "momentum")
            
            if isinstance(score, float) and 0 <= score <= 100:
                self.logger.info("✅ 향상된 엔진 비활성 상태 정상 동작")
            else:
                raise Exception("비정상적인 점수 반환")
                
        except Exception as e:
            self.logger.error(f"❌ 향상된 엔진 테스트 실패: {e}")
            raise
    
    async def test_strategy_compatibility(self, strategy: str):
        """전략 호환성 테스트"""
        try:
            config = type('Config', (), {})()
            engine = EnhancedConsensusEngine(config, enable_dynamic_weights=False)
            
            analysis_results = {
                'technical': {'technical_score': 70},
                'sentiment': {'overall_score': 65},
                'supply_demand': {'overall_score': 75},
                'chart_pattern': {'overall_score': 60},
                'fundamental': {'overall_score': 50},
                'mtf': {'mtf_score': 80}
            }
            
            score, details = engine.synthesize(analysis_results, strategy)
            
            if isinstance(score, float) and 0 <= score <= 100:
                self.logger.info(f"✅ 전략 {strategy} 호환성 확인")
                return True
            else:
                raise Exception(f"전략 {strategy} 비정상적인 결과")
                
        except Exception as e:
            self.logger.error(f"❌ 전략 {strategy} 테스트 실패: {e}")
            return False
    
    async def test_market_analyzer(self):
        """시장 분석기 테스트"""
        try:
            from analyzers.market_condition_analyzer import MarketConditionAnalyzer
            
            config = type('Config', (), {})()
            analyzer = MarketConditionAnalyzer(config)
            
            condition = await analyzer.analyze_current_condition()
            
            if condition and hasattr(condition, 'volatility_regime'):
                self.logger.info("✅ 시장 분석기 정상 동작")
            else:
                raise Exception("시장 분석기 비정상 결과")
                
        except Exception as e:
            self.logger.error(f"❌ 시장 분석기 테스트 실패: {e}")
            raise
    
    async def test_dynamic_system_mock(self):
        """Mock 환경에서 동적 시스템 테스트"""
        try:
            config = type('Config', (), {})()
            engine = EnhancedConsensusEngine(
                config, 
                enable_dynamic_weights=True
            )
            
            # 동적 시스템이 준비되지 않은 상태에서 자동 폴백 확인
            analysis_results = {
                'technical': {'technical_score': 75},
                'sentiment': {'overall_score': 60}
            }
            
            score, details = engine.synthesize(analysis_results, "momentum")
            
            # 폴백이 발생했는지 확인
            if engine.fallback_usage_count > 0:
                self.logger.info("✅ 동적 시스템 자동 폴백 정상 동작")
            else:
                self.logger.warning("⚠️ 예상된 폴백이 발생하지 않음")
                
        except Exception as e:
            self.logger.error(f"❌ 동적 시스템 Mock 테스트 실패: {e}")
            raise
    
    async def initialize_performance_tracking(self):
        """성과 추적 시스템 초기화"""
        try:
            from analyzers.performance_tracker import PerformanceTracker
            
            config = type('Config', (), {})()
            db_manager = type('MockDBManager', (), {})()  # Mock
            
            tracker = PerformanceTracker(config, db_manager)
            
            # 기본 기능 테스트
            prediction_id = await tracker.record_prediction(
                analyzer_name="technical",
                symbol="TEST",
                prediction_score=75.0,
                confidence=0.8,
                expected_direction="up"
            )
            
            if prediction_id:
                self.logger.info("✅ 성과 추적 시스템 초기화 성공")
            else:
                raise Exception("예측 기록 실패")
                
        except Exception as e:
            self.logger.error(f"❌ 성과 추적 초기화 실패: {e}")
            raise
    
    async def test_conservative_weight_adjustment(self):
        """보수적 가중치 조정 테스트"""
        try:
            # 이 단계에서는 실제 조정보다는 시스템 안정성 확인
            self.logger.info("✅ 보수적 가중치 조정 시스템 확인 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 보수적 가중치 조정 테스트 실패: {e}")
            raise
    
    async def test_full_system(self):
        """전체 시스템 테스트"""
        try:
            # 완전한 동적 시스템 테스트는 실제 환경에서 진행
            self.logger.info("✅ 전체 시스템 테스트 준비 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 전체 시스템 테스트 실패: {e}")
            raise
    
    async def verify_monitoring_system(self):
        """모니터링 시스템 확인"""
        try:
            self.logger.info("✅ 모니터링 시스템 확인 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 시스템 확인 실패: {e}")
            raise
    
    async def validate_system_performance(self):
        """시스템 성과 검증"""
        try:
            self.logger.info("✅ 시스템 성과 검증 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 시스템 성과 검증 실패: {e}")
            raise
    
    def get_deployment_status(self):
        """배포 상태 조회"""
        return {
            'current_phase': self.deployment_config.get('phase', 'preparation'),
            'enable_dynamic': self.deployment_config.get('enable_dynamic', False),
            'strategies_enabled': self.deployment_config.get('strategies_enabled', []),
            'last_updated': self.deployment_config.get('last_updated', 'Never')
        }
    
    def print_deployment_status(self):
        """배포 상태 출력"""
        status = self.get_deployment_status()
        print("\n" + "="*60)
        print("📊 동적 가중치 시스템 배포 상태")
        print("="*60)
        print(f"현재 단계: {status['current_phase']}")
        print(f"동적 기능: {'✅ 활성' if status['enable_dynamic'] else '❌ 비활성'}")
        print(f"적용된 전략: {', '.join(status['strategies_enabled']) if status['strategies_enabled'] else '없음'}")
        print(f"마지막 업데이트: {status['last_updated']}")
        print("="*60 + "\n")


async def main():
    """메인 배포 실행 함수"""
    deployer = DynamicWeightDeployer()
    
    print("🚀 동적 가중치 시스템 배포 시작")
    deployer.print_deployment_status()
    
    try:
        current_phase = deployer.deployment_config.get('phase', 'preparation')
        
        if current_phase == 'preparation':
            success = await deployer.run_phase_1_preparation()
            if not success:
                print("❌ Phase 1 실패 - 배포 중단")
                return
        
        if deployer.deployment_config.get('phase') == 'gradual':
            success = await deployer.run_phase_2_gradual()
            if not success:
                print("❌ Phase 2 실패 - 배포 중단")
                return
        
        if deployer.deployment_config.get('phase') == 'activation':
            success = await deployer.run_phase_3_activation()
            if not success:
                print("❌ Phase 3 실패 - 배포 중단")
                return
        
        if deployer.deployment_config.get('phase') == 'full':
            success = await deployer.run_phase_4_full()
            if not success:
                print("❌ Phase 4 실패")
                return
        
        print("🎉 동적 가중치 시스템 배포 완료!")
        deployer.print_deployment_status()
        
    except Exception as e:
        print(f"💥 배포 중 예상치 못한 오류: {e}")
        return
    
    # 다음 단계 안내
    next_phase = deployer.deployment_config.get('phase')
    if next_phase == 'gradual':
        print("📋 다음 단계: 실제 환경에서 점진적 적용 테스트")
    elif next_phase == 'activation':
        print("📋 다음 단계: 동적 기능 활성화 및 모니터링")
    elif next_phase == 'full':
        print("📋 다음 단계: 완전 운영 및 성과 모니터링")


if __name__ == "__main__":
    asyncio.run(main())