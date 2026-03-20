[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $RootDir

$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }

& $PythonBin "scripts/evaluate_hybrid.py" @ArgsList
if ($LASTEXITCODE -ne 0) {
    throw "Benchmark run failed with exit code $LASTEXITCODE."
}
