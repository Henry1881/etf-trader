param(
    [switch]$TestMode
)

# Set encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 硬编码绝对路径（兼容 SYSTEM 账户运行，不依赖 $env:USERPROFILE）
$ProjectDir = "C:\Users\清朗\Documents\trae_projects\EtF Trader"
$PythonPath = "C:\Users\清朗\python-sdk\python3.13.2\python.exe"
$ScriptPath = Join-Path $ProjectDir "generate_report_v3.py"
$LogDir = Join-Path $ProjectDir "logs"
$ReportsDir = Join-Path $ProjectDir "reports"

# Get date
$DateStr = Get-Date -Format "yyyyMMdd"
$LogFile = Join-Path $LogDir "report_$DateStr.log"

# Ensure directories exist
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force -ErrorAction SilentlyContinue | Out-Null
}
if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir -Force -ErrorAction SilentlyContinue | Out-Null
}

# Log function
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    try {
        $LogEntry | Out-File -FilePath $LogFile -Append -Encoding UTF8
    } catch {
        Write-Host "LOG ERROR: $_"
    }
    Write-Host $LogEntry
}

# Start execution
Write-Log "ETF Report Generation Started" "START"
Write-Log "ProjectDir: $ProjectDir"

# Check Python
if (-not (Test-Path $PythonPath)) {
    Write-Log "ERROR: Python not found at $PythonPath" "ERROR"
    exit 1
}

# Check script
if (-not (Test-Path $ScriptPath)) {
    Write-Log "ERROR: Script not found at $ScriptPath" "ERROR"
    exit 1
}

# Change to project directory
Set-Location $ProjectDir
Write-Log "Working directory changed to: $ProjectDir"

# Run report generation script
Write-Log "Running Python report generation script..." "INFO"

try {
    $Output = & $PythonPath $ScriptPath 2>&1
    $ExitCode = $LASTEXITCODE
    
    # Write output to log
    $Output | Out-File -FilePath $LogFile -Append -Encoding UTF8
    
    if ($ExitCode -eq 0) {
        Write-Log "Report generated successfully (Exit Code: $ExitCode)" "SUCCESS"
        
        # Check report file
        $ReportFile = Join-Path $ReportsDir "daily_report_$DateStr.md"
        if (Test-Path $ReportFile) {
            $ReportSize = (Get-Item $ReportFile).Length
            Write-Log "Report file: $ReportFile (Size: $ReportSize bytes)" "SUCCESS"
        } else {
            Write-Log "WARNING: Report file not found: $ReportFile" "WARNING"
        }
    } else {
        Write-Log "Report generation failed (Exit Code: $ExitCode)" "ERROR"
    }
} catch {
    Write-Log "Script execution exception: $_" "ERROR"
    $ExitCode = 1
}

Write-Log "ETF Report Generation Finished" "END"
exit $ExitCode
