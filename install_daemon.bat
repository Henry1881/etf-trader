@echo off
REM ETF Report Daemon 安装脚本
REM 此脚本会将守护进程添加到 Windows 启动项

chcp 65001 >nul

echo ================================================
echo   ETF Report Daemon 安装程序
echo ================================================
echo.

REM 检查当前目录
set "SCRIPT_DIR=%~dp0"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo Script directory: %SCRIPT_DIR%
echo Startup directory: %STARTUP_DIR%
echo.

REM 创建启动文件夹（如果不存在）
if not exist "%STARTUP_DIR%" (
    mkdir "%STARTUP_DIR%"
    echo Created startup directory.
)

REM 创建快捷方式
echo Creating startup shortcut...

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTUP_DIR%\ETF_Report_Daemon.lnk'); $Shortcut.TargetPath = '%SCRIPT_DIR%start_daemon.bat'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.Description = 'ETF每日报告守护进程'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo   SUCCESS! Daemon installed successfully.
    echo ================================================
    echo.
    echo   The ETF Report Daemon will start automatically
    echo   when you log in to Windows.
    echo.
    echo   To test now:
    echo   1. Double-click start_daemon.bat
    echo   2. Or run: python etf_daemon.py --generate
    echo.
    echo   To check status:
    echo   python etf_daemon.py --status
    echo.
    echo   To uninstall:
    echo   Delete the shortcut from:
    echo   %STARTUP_DIR%\ETF_Report_Daemon.lnk
    echo.
    pause
) else (
    echo.
    echo Installation failed. Please check permissions.
    pause
)
