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

Import-DotEnv (Join-Path $RootDir ".env")

$PythonBin = Resolve-PythonCommand
$VenvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $RootDir ".venv" }
$DatasetRoot = if ($env:DATASET_ROOT) { $env:DATASET_ROOT } else { Join-Path $RootDir "data\liar" }
$ClassicalArtifactDir = if ($env:CLASSICAL_ARTIFACT_DIR) { $env:CLASSICAL_ARTIFACT_DIR } else { Join-Path $RootDir "backend\Services\Ml\artifacts" }
$BertOutputDir = if ($env:BERT_OUTPUT_DIR) { $env:BERT_OUTPUT_DIR } else { Join-Path $RootDir "bert_service\models\distilbert-liar" }
$BertSetupMode = if ($env:BERT_SETUP_MODE) { $env:BERT_SETUP_MODE } else { "pretrained" }
$TempDir = Join-Path $RootDir ".tmp"
$PipCacheDir = Join-Path $RootDir ".pip-cache"
$NpmCacheDir = Join-Path $RootDir ".npm-cache"

New-Item -ItemType Directory -Force -Path $TempDir, $PipCacheDir, $NpmCacheDir | Out-Null
[System.Environment]::SetEnvironmentVariable("TEMP", $TempDir, "Process")
[System.Environment]::SetEnvironmentVariable("TMP", $TempDir, "Process")
[System.Environment]::SetEnvironmentVariable("TMPDIR", $TempDir, "Process")
[System.Environment]::SetEnvironmentVariable("PIP_CACHE_DIR", $PipCacheDir, "Process")
[System.Environment]::SetEnvironmentVariable("npm_config_cache", $NpmCacheDir, "Process")

Require-Command "npm.cmd"

if (-not (Test-Path $VenvDir)) {
    Invoke-NativeCommand $PythonBin @("-m", "venv", $VenvDir)
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$RuntimePython = $PythonBin

if ((Test-Path $VenvPython) -and (Test-PythonHasPip $VenvPython)) {
    $RuntimePython = $VenvPython
}
elseif (Test-Path $VenvPython) {
    Write-Warning "Virtual environment was created without pip. Falling back to the base interpreter at $PythonBin."
}
elseif (-not (Test-PythonHasPip $PythonBin)) {
    throw "Python environment does not provide pip: $PythonBin"
}

Invoke-NativeCommand $RuntimePython @("-m", "pip", "install", "--upgrade", "pip")
Invoke-NativeCommand $RuntimePython @("-m", "pip", "install", "-r", "backend/Services/Ml/requirements.txt")
Invoke-NativeCommand $RuntimePython @("-m", "pip", "install", "-r", "bert_service/requirements.txt")

Invoke-NativeCommand "npm.cmd" @("--prefix", "frontend", "install")

Invoke-NativeCommand $RuntimePython @("scripts/setup_liar_dataset.py", "--output-dir", $DatasetRoot)

Invoke-NativeCommand $RuntimePython @(
    "backend/Services/Ml/train_classical_models.py",
    "--dataset-root",
    $DatasetRoot,
    "--output-dir",
    $ClassicalArtifactDir
)

Invoke-NativeCommand $RuntimePython @(
    "bert_service/train.py",
    "--mode",
    $BertSetupMode,
    "--dataset-root",
    $DatasetRoot,
    "--output-dir",
    $BertOutputDir
)

Write-Host ""
Write-Host "Training setup complete."
Write-Host "Classical artifacts: $ClassicalArtifactDir"
Write-Host "BERT model directory: $BertOutputDir"
Write-Host "Next step: .\scripts\dev_start.ps1"
