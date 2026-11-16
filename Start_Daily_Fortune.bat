@echo off
title Daily Fortune - Personal Auspicious Time Planner
cd /d "%~dp0"
python fortune_server.py --host 0.0.0.0 --port 8795 %*
pause
