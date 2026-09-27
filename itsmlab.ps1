# itsmlab.ps1 - run the course checker (itsmlab) as a container against the current directory (Windows).
#
#   .\itsmlab.ps1 doctor
#   .\itsmlab.ps1 verify 1 --json report.json
#   .\itsmlab.ps1 submit 1 --kind submission --tag lab1/v1
#
# Every argument is passed through to itsmlab. The image comes from, in order of precedence:
#   1. the environment variable ITSMLAB_IMAGE,
#   2. "checker_image:" in .\itsmlab.yaml,
#   3. ghcr.io/swasik/itsmlab:2026.
# The current directory is mounted at /work inside the container, and the Docker Desktop socket is
# mounted so that the checker can run "docker compose" for your service.
# If PowerShell refuses to run scripts, allow local scripts once (no administrator rights needed):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    [Console]::Error.WriteLine("itsmlab.ps1: docker was not found. Install Docker Desktop (PREWORK.md, step 1), start it, open a new PowerShell window and rerun.")
    exit 2
}

$defaultImage = "ghcr.io/swasik/itsmlab:2026"
$image = ""
if (Test-Path -LiteralPath "itsmlab.yaml") {
    foreach ($line in Get-Content -LiteralPath "itsmlab.yaml") {
        if ($line -match '^checker_image:\s*"?([^"#\s]+)"?') { $image = $Matches[1]; break }
    }
}
if ($env:ITSMLAB_IMAGE) { $image = $env:ITSMLAB_IMAGE }
if (-not $image) { $image = $defaultImage }

$here = (Get-Location).Path
& docker run --rm -v "${here}:/work" -w /work -v /var/run/docker.sock:/var/run/docker.sock $image @args
exit $LASTEXITCODE
