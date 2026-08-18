@echo off
REM ETF report auto-download on startup
set PY=C:\Users\ÇåÀÊ\python-sdk\python3.13.2\python.exe
set SCRIPT=C:\Users\ÇåÀÊ\Documents\trae_projects\EtF Trader\download_reports.py
set LOG=C:\Users\ÇåÀÊ\Documents\trae_projects\EtF Trader\logs\sync.log
echo [%date% %time%] Sync START >> "%LOG%"
"%PY%" "%SCRIPT%" >> "%LOG%" 2>&1
echo [%date% %time%] Sync END >> "%LOG%"
