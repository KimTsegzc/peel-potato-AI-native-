param(
    [int]$Port = 8501
)

$ErrorActionPreference = "SilentlyContinue"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PidFile = Join-Path $RepoRoot ".streamlit\frontend-$Port.pid"

$stopped = $false

# --- Stop by port listener ---
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $listenerPids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($listenerPid in $listenerPids) {
        $proc = Get-Process -Id $listenerPid -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
            $stopped = $true
            Write-Output "Stopped listener process PID $listenerPid ($($proc.ProcessName))"
        }
    }
}

# --- Stop by PID file ---
if (Test-Path $PidFile) {
    $pidValue = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($pidValue -match '^\d+$') {
        $proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id ([int]$pidValue) -Force -ErrorAction SilentlyContinue
            $stopped = $true
            Write-Output "Stopped PID-file process PID $pidValue ($($proc.ProcessName))"
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

if ($stopped) {
    Write-Output "Frontend stopped for port $Port"
} else {
    Write-Output "No running frontend found for port $Port"
}