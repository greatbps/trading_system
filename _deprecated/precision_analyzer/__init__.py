# D:\trading_system\precision_analyzer\__init__.py

import sys
import os
from loguru import logger

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Configure logger for the entire module
logger.remove()
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}", level="INFO", colorize=False)

# This makes 'logger' available for import in other files within this module
# e.g., from . import logger

