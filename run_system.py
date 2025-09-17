#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 시스템 실행 스크립트
"""

import sys
import os

# UTF-8 인코딩 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# 환경변수 설정
os.environ["PYTHONIOENCODING"] = "utf-8"

if __name__ == "__main__":
    # main.py 실행
    import subprocess
    result = subprocess.run([sys.executable, "-X", "utf8", "main.py"] + sys.argv[1:], 
                          encoding="utf-8")
    sys.exit(result.returncode)