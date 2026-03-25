param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonPath = Join-Path $RepoRoot ".venv311\Scripts\python.exe"
$AppPath = Join-Path $RepoRoot "Gateway\Front\app.py"
$RuntimeDir = Join-Path $RepoRoot ".streamlit"
$PidFile = Join-Path $RuntimeDir "frontend-$Port.pid"
$StdoutLog = Join-Path $RuntimeDir "frontend-$Port.out.log"
$StderrLog = Join-Path $RuntimeDir "frontend-$Port.err.log"

if (-not (Test-Path $PythonPath)) {
    throw "python.exe not found: $PythonPath"
}

if (-not (Test-Path $AppPath)) {
    throw "Frontend app not found: $AppPath"
}

if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir | Out-Null
}

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $existingPids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($existingPid in $existingPids) {
        Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 800
}

$process = Start-Process `
    -FilePath $PythonPath `
    -ArgumentList @('-m', 'streamlit', 'run', $AppPath, '--server.headless', 'true', '--server.port', $Port) `
    -WorkingDirectory $RepoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -PassThru

Set-Content -Path $PidFile -Value $process.Id -Encoding ascii
Write-Output "Frontend started silently on http://localhost:$Port (PID $($process.Id))"