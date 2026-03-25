param(
    [int]$Port = 8501,
    [string]$PythonOverride = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$AppPath = Join-Path $RepoRoot "Gateway\Front\app.py"
$RuntimeDir = Join-Path $RepoRoot ".streamlit"
$PidFile = Join-Path $RuntimeDir "frontend-$Port.pid"
$StdoutLog = Join-Path $RuntimeDir "frontend-$Port.out.log"
$StderrLog = Join-Path $RuntimeDir "frontend-$Port.err.log"

# --- Resolve Python executable (priority: override > local venv > conda > PATH) ---
function Find-Python {
    # 1. Explicit override
    if ($PythonOverride -and (Test-Path $PythonOverride)) {
        return $PythonOverride
    }

    # 2. Local virtual environments (common names)
    foreach ($venvDir in @(".venv311", ".venv", "venv", ".venv312", ".venv310")) {
        $candidate = Join-Path $RepoRoot "$venvDir\Scripts\python.exe"
        if (Test-Path $candidate) { return $candidate }
    }

    # 3. Active conda environment
    if ($env:CONDA_PREFIX) {
        $condaPython = Join-Path $env:CONDA_PREFIX "python.exe"
        if (Test-Path $condaPython) { return $condaPython }
    }

    # 4. System PATH
    $systemPython = Get-Command python -ErrorAction SilentlyContinue |
                    Select-Object -First 1 -ExpandProperty Source
    if ($systemPython) { return $systemPython }

    return $null
}

$PythonPath = Find-Python
if (-not $PythonPath) {
    throw "No Python found. Install a venv, conda env, or add python to PATH. Or pass -PythonOverride <path>."
}

if (-not (Test-Path $AppPath)) {
    throw "Frontend app not found: $AppPath"
}

if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir | Out-Null
}

# --- Stop any existing process on the target port ---
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $existingPids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($existingPid in $existingPids) {
        Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 800
}

# --- Launch Streamlit ---
Write-Output "Using Python: $PythonPath"

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