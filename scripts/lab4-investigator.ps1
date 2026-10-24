param(
    [string]$PackagePath = 'E:\IT service managment\LAB4',
    [switch]$Stop
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $PSScriptRoot 'lab4-ai\compose.yml'
$env:LAB4_REPO = $repoPath.Replace('\', '/')
$env:LAB4_PACKAGE = (Resolve-Path -LiteralPath $PackagePath).Path.Replace('\', '/')

function Invoke-LabDocker {
    param([string[]]$DockerArgs)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & docker @DockerArgs 2>&1 | ForEach-Object { Write-Host ([string]$_) }
        $dockerExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldPreference
    }
    if ($dockerExit -ne 0) { throw "Docker failed (exit $dockerExit). Read the message above." }
}
$composeArgs = @('compose', '--project-name', 'itsm-lab4-ai', '--file', $composePath)
if ($Stop) {
    Invoke-LabDocker -DockerArgs ($composeArgs + @('stop'))
    return
}
foreach ($required in @('agent\requirements.txt', 'agent\agent.py', 'agent\prom_mcp.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $PackagePath $required))) {
        throw "Missing package file: $required"
    }
}
$snapshotPath = Join-Path $repoPath 'incident\tsdb-snapshot.tar.gz'
if (-not (Test-Path -LiteralPath $snapshotPath)) { throw 'Missing incident snapshot.' }
$snapshotHash = (Get-FileHash -LiteralPath $snapshotPath -Algorithm SHA256).Hash
if ($snapshotHash -ne '6DD2C5AAB7322A7C93D9B3C1251EDCCAA0176FBF4E0CF62B323E2F541B23E147') {
    throw 'This helper is for the confirmed lab4-rec-3 snapshot. Its checksum does not match.'
}
New-Item -ItemType Directory -Force -Path (Join-Path $repoPath 'ai-rca\second') | Out-Null
Write-Host '[1/4] Starting the recording and local model service...'
Invoke-LabDocker -DockerArgs ($composeArgs + @('up', '-d', '--wait', '--wait-timeout', '180', 'ollama', 'recording'))
Write-Host '[2/4] Downloading qwen3:1.7b (about 1.4 GB on the first run)...'
Invoke-LabDocker -DockerArgs ($composeArgs + @('exec', '-T', 'ollama', 'ollama', 'pull', 'qwen3:1.7b'))
Write-Host '[3/4] Building the course investigator with its pinned dependencies...'
Invoke-LabDocker -DockerArgs ($composeArgs + @('build', 'investigator'))
Write-Host '[4/4] Investigating. CPU inference can take several minutes; every finished step is saved in ai-rca/second/transcript.md.'
Invoke-LabDocker -DockerArgs ($composeArgs + @('run', '--rm', '--no-deps', 'investigator'))
Write-Host 'Saved: ai-rca/second/transcript.md and transcript.jsonl. The transcript still needs a scored ledger.'
Write-Host 'To stop these helper services later: .\scripts\lab4-investigator.ps1 -Stop'
