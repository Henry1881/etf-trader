# Install ETF Report Daemon to Windows Startup
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"

Write-Host "Script directory: $ScriptDir"
Write-Host "Startup directory: $StartupDir"

# Create startup directory if not exists
if (-not (Test-Path $StartupDir)) {
    New-Item -ItemType Directory -Path $StartupDir -Force | Out-Null
    Write-Host "Created startup directory."
}

# Create shortcut
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut("$StartupDir\ETF_Report_Daemon.lnk")
$Shortcut.TargetPath = Join-Path $ScriptDir "start_daemon.bat"
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "ETF Daily Report Daemon - Auto-generates reports every workday at 20:00"
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.Save()

Write-Host ""
Write-Host "================================================"
Write-Host "  SUCCESS! Daemon installed."
Write-Host "================================================"
Write-Host ""
Write-Host "  The daemon will start automatically when you log in."
Write-Host ""
Write-Host "  To test manually:"
Write-Host "    1. Double-click start_daemon.bat"
Write-Host "    2. Or run: python etf_daemon.py --generate"
Write-Host ""
Write-Host "  To check status:"
Write-Host "    python etf_daemon.py --status"
Write-Host ""
Write-Host "  To uninstall:"
Write-Host "    Delete: $StartupDir\ETF_Report_Daemon.lnk"
Write-Host ""
