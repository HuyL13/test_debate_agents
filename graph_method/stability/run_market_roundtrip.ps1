param([string]$Name = 'full_train_market_gptoss120b_roundtrip_r1', [int]$Limit = 0)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Name -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid run name' }
if ($Limit -lt 0) { throw 'Limit must be zero or positive' }
$env:PYTHONIOENCODING = 'utf-8'
$runnerArgs = @('-u','roundtrip_resume.py','--name',$Name,'--workers','4')
if ($Limit -gt 0) { $runnerArgs += @('--limit',[string]$Limit) }
& .\.venv-syntax\Scripts\python.exe @runnerArgs *>&1 | Tee-Object -FilePath ($Name + '.log') -Append
if ($LASTEXITCODE -ne 0) { throw "Roundtrip process exited with code $LASTEXITCODE" }
