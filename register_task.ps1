# ETF每日报告定时任务注册脚本
# Run as Administrator

$TaskName = "ETF_Daily_Report"
$ScriptPath = "C:\Users\清朗\Documents\trae_projects\EtF Trader\run_report.ps1"
$WorkingDir = "C:\Users\清朗\Documents\trae_projects\EtF Trader"

# Create action - run PowerShell with execution policy bypass
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`"" `
    -WorkingDirectory $WorkingDir

# Trigger: every workday at 20:00
$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At (Get-Date "20:00:00")

# Settings - allow on battery, restart on failure
# 注意：不使用 -StartWhenAvailable，防止错过 20:00 后在次日盘中补跑（会导致盘中生成报告）
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew

# Principal - run with highest privileges
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Delete existing task if exists
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Deleted old task"
}

# Register task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "ETF Daily Trading Report Auto-Generation - Runs every workday at 20:00"

Write-Host ""
Write-Host "================================================"
Write-Host "  Scheduled Task Registered Successfully!"
Write-Host "================================================"
Write-Host "  Task Name: $TaskName"
Write-Host "  Script: $ScriptPath"
Write-Host "  Schedule: Every workday (Mon-Fri) at 20:00"
Write-Host "  Privilege: Highest"
Write-Host "  Logs: $WorkingDir\logs\"
Write-Host ""
Write-Host "  Manual test:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "  Check status:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Format-List *"
Write-Host ""
Write-Host "  View logs:"
Write-Host "  Get-Content '$WorkingDir\logs\report_*.log' -Tail 20"
