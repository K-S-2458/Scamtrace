param (
    [Parameter(Position=0)]
    [string]$Target = "test"
)

$ErrorActionPreference = "Stop"

$PYTHON = ".venv\Scripts\python.exe"
$PIP = ".venv\Scripts\pip.exe"
$PYTEST = ".venv\Scripts\pytest.exe"

switch ($Target) {
    "install" {
        Write-Host "Installing dependencies..."
        if (-not (Test-Path ".venv")) {
            python -m venv .venv
        }
        & $PIP install --upgrade pip
        & $PIP install -r backend/requirements.txt
        if (Test-Path "frontend\package.json") {
            Set-Location frontend
            npm install
            Set-Location ..
        }
    }
    "test" {
        Write-Host "Running backend test suite..."
        & $PYTEST backend/tests -v
    }
    "run-backend" {
        Write-Host "Starting SCAMTRACE backend API..."
        & $PYTHON -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
    }
    "run-frontend" {
        Write-Host "Starting SCAMTRACE frontend UI..."
        Set-Location frontend
        npm run dev
        Set-Location ..
    }
    "reproduce-experiments" {
        Write-Host "Running data generation and benchmark reproductions..."
        & $PYTHON experiments/generate_synthetic.py
        & $PYTHON experiments/run_all.py
    }
    default {
        Write-Host "Unknown target: $Target. Available: install, test, run-backend, run-frontend, reproduce-experiments"
        exit 1
    }
}

