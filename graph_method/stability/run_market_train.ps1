param(
    [string]$Name = 'full_train_market_gptoss120b_r1',
    [int]$Limit = 0
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Name -notmatch '^[A-Za-z0-9_-]+$') { throw 'Name must contain only letters, digits, underscore or hyphen.' }
if ($Limit -lt 0) { throw 'Limit must be zero (full train) or positive.' }
$env:GRAPH_API_PROVIDER = 'market'
$env:GRAPH_MODEL_OVERRIDE = 'gpt-oss-120b'
$env:GRAPH_API_CONCURRENCY = '4'
$env:GRAPH_MARKET_OUTPUT_MODE = 'prompt_json'
$env:PYTHONIOENCODING = 'utf-8'
$pythonPath = Join-Path $PSScriptRoot '.venv-syntax\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Missing syntax Python environment.' }
if (-not (Test-Path -LiteralPath 'full_train_manifest.json')) { throw 'Missing full_train_manifest.json.' }
$runLock = [System.IO.File]::Open((Join-Path $PSScriptRoot ($Name + '.run.lock')), [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
try {
    $runnerArgs = @('-u','pipeline_v2.py','--manifest','full_train_manifest.json','--source-model','gpt-oss-120b','--source-mode','decomposed','--source-examples','--warrant-mode','slots','--workers','4','--interval','1','--name',$Name)
    if ($Limit -gt 0) { $runnerArgs += @('--limit', [string]$Limit) }
    $logPath = Join-Path $PSScriptRoot ($Name + '.log')
    "Starting Market gpt-oss-120b;4workers;prompt_json;limit=$Limit" | Tee-Object -FilePath $logPath -Append
    & $pythonPath @runnerArgs *>&1 | Tee-Object -FilePath $logPath -Append
    $runnerExit = $LASTEXITCODE
    if ($runnerExit -ne 0) { throw "Training process exited with code $runnerExit" }
    $metrics = Get-Content -LiteralPath ($Name + '_metrics.json') -Raw | ConvertFrom-Json
    if ($metrics.stopped_early) { Write-Warning ('Stopped by source failure guard: ' + $metrics.stop_reason) }
} finally {
    $runLock.Dispose()
}
