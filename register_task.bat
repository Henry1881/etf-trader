@echo off
chcp 65001 >nul
echo ================================================
echo 注册 ETF 每日报告自动生成任务
echo ================================================
echo.

set TASK_NAME=ETF_Daily_Report
set SCRIPT_PATH=C:\Users\清朗\Documents\trae_projects\EtF Trader\run_report.bat

REM 删除已存在的同名任务（如果有）
schtasks /delete /tn "%TASK_NAME%" /f 2>nul

REM 创建新的定时任务
REM 每天晚上 20:00 执行（周一到周五）
schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /sc weekly /d MON,TUE,WED,THU,FRI /st 20:00 /f

if %errorlevel% == 0 (
    echo.
    echo ✅ 定时任务注册成功！
    echo.
    echo 任务详情:
    echo   任务名称: %TASK_NAME%
    echo   执行时间: 每个工作日（周一至周五）20:00
    echo   执行脚本: %SCRIPT_PATH%
    echo.
    echo 您可以在"任务计划程序"中查看或修改此任务。
) else (
    echo.
    echo ❌ 任务注册失败，请手动创建或联系管理员。
    echo.
    echo 手动创建步骤:
    echo   1. 打开"任务计划程序" (taskschd.msc)
    echo   2. 创建基本任务 -^> 触发器: 每天 20:00
    echo   3. 操作: 启动程序 -^> 选择 run_report.bat
)

echo.
echo ================================================
echo 查看已注册的任务:
schtasks /query /tn "%TASK_NAME%" /fo list 2>nul
echo ================================================
pause
