param(
    [switch]$InstallMl
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
$pythonBackendRoot = Join-Path $repoRoot "python-backend"
$venvPython = Join-Path $pythonBackendRoot ".venv\\Scripts\\python.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python is required in PATH."
}

if (-not (Test-Path $venvPython)) {
    Push-Location $pythonBackendRoot
    python -m uv venv ".venv" | Out-Null
    Pop-Location
}

Push-Location $pythonBackendRoot
python -m uv sync --python "$venvPython" | Out-Null
if ($InstallMl) {
    python -m uv sync --python "$venvPython" --extra ml | Out-Null
}
Pop-Location

& $venvPython "$repoRoot/python-backend/scripts/smoke-indicator-service.py"
