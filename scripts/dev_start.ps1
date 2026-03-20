[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RootDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $RootDir

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        $separatorIndex = $trimmed.IndexOf("=")
        if ($separatorIndex -lt 1) {
            continue
        }

        $name = $trimmed.Substring(0, $separatorIndex).Trim()
        $value = $trimmed.Substring($separatorIndex + 1).Trim().Trim('"')
        [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

function Resolve-PythonCommand {
    if ($env:PYTHON_BIN) {
        return $env:PYTHON_BIN
    }

    $candidates = @("python", "python3", "py")
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    throw "Missing required command: python"
}

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

function Require-File {
    param(
        [string]$Path,
        [string]$Message
    )

    if (-not (Test-Path $Path -PathType Leaf)) {
        throw $Message
    }
}

function Invoke-NativeCommand {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($ArgumentList -join ' ')"
    }
}

function Test-PythonHasPip {
    param([string]$PythonExecutable)

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $PythonExecutable -m pip --version 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [string]$Name,
        [int]$Attempts = 40
    )

    for ($i = 0; $i -lt $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -lt 500) {
                Write-Host "$Name is ready at $Url"
                return
            }
        }
        catch {
        }

        Start-Sleep -Seconds 1
    }

    throw "Timed out waiting for $Name at $Url"
}

Import-DotEnv (Join-Path $RootDir ".env")

$LogDir = Join-Path $RootDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$PythonBin = Resolve-PythonCommand
$VenvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $RootDir ".venv" }
$DatasetRoot = if ($env:DATASET_ROOT) { $env:DATASET_ROOT } else { Join-Path $RootDir "data\liar" }
$ClassicalArtifactDir = if ($env:CLASSICAL_ARTIFACT_DIR) { $env:CLASSICAL_ARTIFACT_DIR } else { Join-Path $RootDir "backend\Services\Ml\artifacts" }
$TempDir = Join-Path $RootDir ".tmp"
$PipCacheDir = Join-Path $RootDir ".pip-cache"
$NpmCacheDir = Join-Path $RootDir ".npm-cache"

New-Item -ItemType Directory -Force -Path $TempDir, $PipCacheDir, $NpmCacheDir | Out-Null
[System.Environment]::SetEnvironmentVariable("TEMP", $TempDir, "Process")
[System.Environment]::SetEnvironmentVariable("TMP", $TempDir, "Process")
[System.Environment]::SetEnvironmentVariable("TMPDIR", $TempDir, "Process")
[System.Environment]::SetEnvironmentVariable("PIP_CACHE_DIR", $PipCacheDir, "Process")
[System.Environment]::SetEnvironmentVariable("npm_config_cache", $NpmCacheDir, "Process")

if (Test-Path (Join-Path $VenvDir "Scripts\python.exe")) {
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    if (Test-PythonHasPip $VenvPython) {
        $PythonBin = $VenvPython
    }
}

[System.Environment]::SetEnvironmentVariable("ASPNETCORE_ENVIRONMENT", $(if ($env:ASPNETCORE_ENVIRONMENT) { $env:ASPNETCORE_ENVIRONMENT } else { "Development" }), "Process")
[System.Environment]::SetEnvironmentVariable("ASPNETCORE_URLS", $(if ($env:ASPNETCORE_URLS) { $env:ASPNETCORE_URLS } else { "http://localhost:5000" }), "Process")
[System.Environment]::SetEnvironmentVariable("BertService__Url", $(if ($env:BertService__Url) { $env:BertService__Url } else { "http://localhost:8001" }), "Process")
[System.Environment]::SetEnvironmentVariable("VITE_API_BASE_URL", $(if ($env:VITE_API_BASE_URL) { $env:VITE_API_BASE_URL } else { "http://localhost:5000" }), "Process")
[System.Environment]::SetEnvironmentVariable("MachineLearning__PythonExecutable", $(if ($env:MachineLearning__PythonExecutable) { $env:MachineLearning__PythonExecutable } else { $PythonBin }), "Process")

Require-Command "dotnet"
Require-Command "npm.cmd"

if (-not (Test-Path "frontend/node_modules")) {
    throw "Frontend dependencies are missing. Run .\scripts\train_all.ps1 first."
}

Require-File (Join-Path $DatasetRoot "train.tsv") "LIAR dataset is missing. Run scripts/setup_liar_dataset.py first."
Require-File (Join-Path $DatasetRoot "valid.tsv") "LIAR dataset is incomplete. Expected valid.tsv under $DatasetRoot."
Require-File (Join-Path $DatasetRoot "test.tsv") "LIAR dataset is incomplete. Expected test.tsv under $DatasetRoot."
Require-File (Join-Path $ClassicalArtifactDir "tfidf_vectorizer.joblib") "Classical artifacts are missing. Run .\scripts\train_all.ps1 first."
Require-File (Join-Path $ClassicalArtifactDir "logistic_regression.joblib") "Classical artifacts are missing. Run .\scripts\train_all.ps1 first."
Require-File (Join-Path $ClassicalArtifactDir "random_forest.joblib") "Classical artifacts are missing. Run .\scripts\train_all.ps1 first."

$BertLog = Join-Path $LogDir "bert_service.log"
$BertErrorLog = Join-Path $LogDir "bert_service.err.log"
$BackendLog = Join-Path $LogDir "backend.log"
$BackendErrorLog = Join-Path $LogDir "backend.err.log"

$BertProcess = $null
$BackendProcess = $null

try {
    Write-Host "Starting bert_service..."
    $BertProcess = Start-Process -FilePath $PythonBin `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001") `
        -WorkingDirectory (Join-Path $RootDir "bert_service") `
        -RedirectStandardOutput $BertLog `
        -RedirectStandardError $BertErrorLog `
        -PassThru

    Wait-ForUrl -Url "http://127.0.0.1:8001/health" -Name "bert_service"

    Write-Host "Starting backend..."
    $BackendProcess = Start-Process -FilePath "dotnet" `
        -ArgumentList @("run", "--project", "backend/MisinformationRiskAssessment.Api.csproj") `
        -WorkingDirectory $RootDir `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendErrorLog `
        -PassThru

    Wait-ForUrl -Url "http://127.0.0.1:5000/api/health" -Name "backend API"

    Write-Host "Starting frontend..."
    Write-Host "Logs:"
    Write-Host "  bert_service: $BertLog"
    Write-Host "  backend:      $BackendLog"
    Write-Host "Frontend will run in the current terminal. Press Ctrl+C to stop all services."

    Set-Location (Join-Path $RootDir "frontend")
    Invoke-NativeCommand "npm.cmd" @("run", "dev:host")
}
finally {
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Stop-Process -Id $BackendProcess.Id -Force
    }

    if ($BertProcess -and -not $BertProcess.HasExited) {
        Stop-Process -Id $BertProcess.Id -Force
    }
}
