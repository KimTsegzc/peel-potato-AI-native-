param(
    [int]$Port = 8501,
    [string]$PythonOverride = "",
    [switch]$NoBrowser,
    [switch]$WeChat,
    [switch]$UseLauncherExe,
    [int]$WaitMilliseconds = 1200
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$StopScript = Join-Path $RepoRoot "Launcher\stop_frontend.ps1"
$StartScript = Join-Path $RepoRoot "Launcher\start_frontend_silent.ps1"

if (-not (Test-Path $StopScript)) {
    throw "Launcher stop script not found: $StopScript"
}

if (-not (Test-Path $StartScript)) {
    throw "Launcher start script not found: $StartScript"
}

$stopParams = @{ Port = $Port }
if ($PythonOverride) {
    $stopParams.PythonOverride = $PythonOverride
}
if ($UseLauncherExe) {
    $stopParams.UseLauncherExe = $true
}

$startParams = @{ Port = $Port }
if ($PythonOverride) {
    $startParams.PythonOverride = $PythonOverride
}
if ($NoBrowser) {
    $startParams.NoBrowser = $true
}
if ($WeChat) {
    $startParams.WeChat = $true
}
if ($UseLauncherExe) {
    $startParams.UseLauncherExe = $true
}

Write-Output "Stopping frontend on port $Port ..."
& $StopScript @stopParams

if ($WaitMilliseconds -gt 0) {
    Start-Sleep -Milliseconds $WaitMilliseconds
}

Write-Output "Starting frontend on port $Port ..."
& $StartScript @startParams
