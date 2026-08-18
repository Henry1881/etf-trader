"""Generate sync_reports.bat in GBK encoding for cmd.exe"""
lines = [
    "@echo off",
    "REM ETF report auto-download on startup",
    "set PY=C:\\Users\\清朗\\python-sdk\\python3.13.2\\python.exe",
    "set SCRIPT=C:\\Users\\清朗\\Documents\\trae_projects\\EtF Trader\\download_reports.py",
    "set LOG=C:\\Users\\清朗\\Documents\\trae_projects\\EtF Trader\\logs\\sync.log",
    'echo [%date% %time%] Sync START >> "%LOG%"',
    '"%PY%" "%SCRIPT%" >> "%LOG%" 2>&1',
    'echo [%date% %time%] Sync END >> "%LOG%"',
]
content = "\r\n".join(lines) + "\r\n"
with open(r"C:\Users\清朗\Documents\trae_projects\EtF Trader\sync_reports.bat", "w", encoding="gbk", errors="replace") as f:
    f.write(content)
print("sync_reports.bat written in GBK encoding")
