param(
    [string]$RunDirectory = 'outputs/nvidia-two-flow-detection-dev4',
    [string]$BenchmarkIds = '',
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repo
$runPath = [IO.Path]::GetFullPath((Join-Path $repo $RunDirectory))
if (-not $runPath.StartsWith($repo + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Run directory must be inside the repository'
}
$statePath = Join-Path $repo 'cache/auto-push-dev4.json'
$codePaths = @(
    'src/engine.py', 'src/legacy_protocols/common.py', 'src/legacy_protocols/round_robin.py',
    'src/llm/mock.py', 'src/runner.py', 'src/simplified.py', 'src/run_two_flows.py',
    'configs/classification.simplified_a.yaml', 'configs/classification.simplified_b.yaml',
    'configs/detection.simplified_a.yaml', 'configs/detection.simplified_b.yaml',
    'docs/TWO_FLOW_SIM.md', 'scripts/auto_push_when_done.ps1'
)

function Git-Checked {
    param([string[]]$Arguments)
    $result = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments[0]) failed: $result" }
    return $result
}

function Save-State([string]$status, [string]$detail) {
    $state = @{status=$status; detail=$detail; updated_at=[DateTime]::UtcNow.ToString('o'); run=$RunDirectory}
    $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
}

function Check-Results {
    $comparisonPath = Join-Path $runPath 'comparison.json'
    if (-not (Test-Path -LiteralPath $comparisonPath)) { throw 'Benchmark did not produce comparison.json' }
    $comparison = Get-Content -LiteralPath $comparisonPath -Raw | ConvertFrom-Json
    foreach ($variant in @('A1', 'B1', 'A2', 'B2')) {
        $summary = Get-Content -LiteralPath (Join-Path $runPath "$variant/summary.json") -Raw | ConvertFrom-Json
        if ($summary.status -ne 'complete' -or $summary.count -ne 4 -or $summary.synthetic -ne $false) {
            throw "$variant is not a complete four-sample real-model run"
        }
        if ($comparison.summaries.$variant.status -ne 'complete') { throw "$variant comparison incomplete" }
    }
    if (@($comparison.samples).Count -ne 4) { throw 'Comparison must contain four samples' }
}

try {
    if ($CheckOnly) {
        Check-Results
        Write-Output 'Results complete; check-only mode made no git changes.'
        exit 0
    }
    New-Item -ItemType Directory -Path (Join-Path $repo 'cache') -Force | Out-Null
    $head = [string](Git-Checked @('rev-parse', 'HEAD'))
    $branch = [string](Git-Checked @('branch', '--show-current'))
    if ($branch -ne 'main') { throw 'Expected branch main' }
    $remote = [string](Git-Checked @('remote', 'get-url', '--push', 'origin'))
    if ($remote -ne 'https://github.com/HuyL13/test_debate_agents.git') { throw 'Unexpected push destination' }
    if (Git-Checked @('diff', '--cached', '--name-only')) { throw 'Index contains staged changes; refusing to mix them' }
    $hashes = @{}
    foreach ($path in $codePaths) { $hashes[$path] = (Get-FileHash -LiteralPath $path).Hash }
    $processes = @()
    foreach ($processNumber in ($BenchmarkIds -split ',')) {
        if ($processNumber) {
            $p = Get-Process -Id ([int]$processNumber) -ErrorAction SilentlyContinue
            if ($p) { $processes += @{Id=$p.Id; Started=$p.StartTime} }
        }
    }
    Save-State 'waiting' 'Waiting for the benchmark processes to exit and all four variants to complete.'
    $deadline = [DateTime]::UtcNow.AddHours(6)
    while ($true) {
        $alive = @($processes | Where-Object {
            $current = Get-Process -Id $_.Id -ErrorAction SilentlyContinue
            $current -and $current.StartTime -eq $_.Started
        })
        if ($alive.Count -eq 0) { break }
        if ([DateTime]::UtcNow -gt $deadline) { throw 'Timed out waiting for benchmark' }
        Start-Sleep -Seconds 15
    }
    Check-Results
    foreach ($path in $codePaths) {
        if ((Get-FileHash -LiteralPath $path).Hash -ne $hashes[$path]) { throw "Code changed while waiting: $path" }
    }
    if ([string](Git-Checked @('rev-parse', 'HEAD')) -ne $head -or
        [string](Git-Checked @('branch', '--show-current')) -ne $branch) { throw 'HEAD or branch changed while waiting' }
    if (Git-Checked @('diff', '--cached', '--name-only')) { throw 'Index changed while waiting' }
    if ([string](Git-Checked @('remote', 'get-url', '--push', 'origin')) -ne $remote) { throw 'Push destination changed' }
    $files = @($codePaths) + @(Get-ChildItem -LiteralPath $runPath -File -Recurse | Select-Object -ExpandProperty FullName)
    foreach ($file in $files) {
        if (Select-String -LiteralPath $file -Pattern '(nvapi-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,})' -Quiet) {
            throw 'Credential-like value found in selected files; push stopped'
        }
    }
    Save-State 'committing' 'Benchmark complete; committing selected flow code and run logs.'
    Git-Checked (@('add', '--') + $codePaths) | Out-Null
    Git-Checked @('add', '-f', '--', $RunDirectory) | Out-Null
    Git-Checked @('diff', '--cached', '--check') | Out-Null
    Git-Checked @('commit', '-m', 'Add simplified A/B flows and four-sample NVIDIA benchmark traces') | Out-Null
    $commit = [string](Git-Checked @('rev-parse', 'HEAD'))
    Save-State 'pushing' $commit
    Git-Checked @('push', 'origin', "${commit}:refs/heads/main") | Out-Null
    Save-State 'pushed' $commit
} catch {
    if (-not $CheckOnly) { Save-State 'failed' $_.Exception.Message }
    Write-Error $_.Exception.Message
    exit 1
}
