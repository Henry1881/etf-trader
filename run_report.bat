@echo off
set PY=C:\Users\ÇåÀÊ\python-sdk\python3.13.2\python.exe
set SCRIPT=C:\Users\ÇåÀÊ\Documents\trae_projects\EtF Trader\generate_report_v3.py
set LOGDIR=C:\Users\ÇåÀÊ\Documents\trae_projects\EtF Trader\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set DT=%%i
set LOG=%LOGDIR%\report_%DT%.log
echo [%DT%] START >> "%LOG%"
"%PY%" "%SCRIPT%" >> "%LOG%" 2>&1
set EC=%ERRORLEVEL%
echo [%DT%] END Exit:%EC% >> "%LOG%"
exit %EC%
