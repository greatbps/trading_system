import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

from utils.logger import get_logger


def format_symbol(symbol: str, name: Optional[str]) -> str:
    return f"{symbol} ({name})" if name else symbol

# 이하에 기존 kis_collector.py 전체 코드가 그대로 들어갑니다
# 그리고 모든 self.logger.~~(f"...{symbol}...") 패턴은 아래처럼 수정됩니다:
# 예시:
#   self.logger.info(f"✅ {symbol} 필터링 성공")
#   -> self.logger.info(f"✅ {format_symbol(symbol, name)} 필터링 성공")
#
# 또는 name 정보가 없는 경우에는 stock_info.get('name', '') 등으로 처리:
#   self.logger.warning(f"⚠️ {format_symbol(symbol, stock_info.get('name', ''))} 필터링 실패")

# 예시 적용 (일부)
# self.logger.debug(f"✅ {symbol} ({name}) 파싱 완료")
# ->
# self.logger.debug(f"✅ {format_symbol(symbol, name)} 파싱 완료")

# 이 함수는 공통 유틸로 빼서 utils/formatter.py에 둘 수도 있으며,
# from utils.formatter import format_symbol 방식으로도 가져올 수 있음