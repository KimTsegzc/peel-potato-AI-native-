param(
    [string]$PythonOverride = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LauncherScript = Join-Path $RepoRoot "Launcher\Go_XIEXin.py"
$SourceIconIco = Join-Path $RepoRoot "Launcher\Go_XIEXin.ico"
$BuildRoot = Join-Path $RepoRoot ".build\pyinstaller"
$BuildIconIco = Join-Path $BuildRoot "Go_XIEXin.multisize.ico"
$PrimaryExe = Join-Path $RepoRoot "Go_XIEXin.exe"
$FreshExe = Join-Path $RepoRoot "Go_XIEXin_fresh.exe"
$WorkDir = Join-Path $BuildRoot "work"
$SpecDir = Join-Path $BuildRoot "spec"

function Find-Python {
    if ($PythonOverride -and (Test-Path $PythonOverride)) {
        return $PythonOverride
    }

    foreach ($venvDir in @(".venv311", ".venv", "venv", ".venv312", ".venv310")) {
        $candidate = Join-Path $RepoRoot "$venvDir\Scripts\python.exe"
        if (Test-Path $candidate) { return $candidate }
    }

    if ($env:CONDA_PREFIX) {
        $condaPython = Join-Path $env:CONDA_PREFIX "python.exe"
        if (Test-Path $condaPython) { return $condaPython }
    }

    $systemPython = Get-Command python -ErrorAction SilentlyContinue |
                    Select-Object -First 1 -ExpandProperty Source
    if ($systemPython) { return $systemPython }

    return $null
}

if (-not (Test-Path $LauncherScript)) {
    throw "Launcher script not found: $LauncherScript"
}

$PythonPath = Find-Python
if (-not $PythonPath) {
    throw "No Python found. Install a venv, conda env, or add python to PATH. Or pass -PythonOverride <path>."
}

if (-not (Test-Path $SourceIconIco)) {
    throw "Icon file not found: $SourceIconIco"
}

New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
New-Item -ItemType Directory -Force -Path $SpecDir | Out-Null

& $PythonPath -c "from pathlib import Path; from PIL import Image; src = Path(r'$SourceIconIco'); dst = Path(r'$BuildIconIco'); img = Image.open(src).convert('RGBA'); dst.parent.mkdir(parents=True, exist_ok=True); img.save(dst, format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"

if (-not (Test-Path $BuildIconIco)) {
    throw "Normalized build icon was not created: $BuildIconIco"
}

& $PythonPath -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Go_XIEXin `
    --icon $BuildIconIco `
    --distpath $RepoRoot `
    --workpath $WorkDir `
    --specpath $SpecDir `
    $LauncherScript

if (Test-Path $PrimaryExe) {
    Copy-Item $PrimaryExe $FreshExe -Force
}