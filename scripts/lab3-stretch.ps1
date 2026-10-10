# ai-generated: 100% - Codex prepared repeatable real measurements and a local model call.
[CmdletBinding()]
param([ValidateSet('all', 'gap', 'genai')][string]$Part = 'all')

$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$rootCompose = Join-Path $repoPath 'docker-compose.yml'
$aiCompose = Join-Path $repoPath 'genai\docker-compose.yml'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Invoke-LabHttp {
    param(
        [string]$Url,
        [ValidateSet('Get', 'Post', 'Delete')][string]$Method = 'Get',
        [string]$Body = '',
        [int]$TimeoutSec = 10
    )
    # Toxiproxy rejects Mozilla/* user agents, including PowerShell 5.1's default.
    $request = @{
        Uri = $Url
        Method = $Method
        UserAgent = 'itsm-lab3-script/1.0'
        TimeoutSec = $TimeoutSec
        ErrorAction = 'Stop'
    }
    if ($Body) {
        $request.Body = $Body
        $request.ContentType = 'application/json'
    }
    Invoke-RestMethod @request
}

function Invoke-Docker {
    param([string[]]$DockerArgs, [string]$LogFile = '')
    $oldPreference = $ErrorActionPreference
    $capture = New-Object System.Text.StringBuilder
    try {
        # PS 5.1 treats native stderr (including ordinary Docker progress) as ErrorRecords.
        # Render it as text, but still fail on a nonzero native exit code.
        $ErrorActionPreference = 'Continue'
        & docker @DockerArgs 2>&1 | ForEach-Object {
            $line = $_.ToString() -replace '\x1b\[[0-?]*[ -/]*[@-~]', ''
            Write-Host $line
            [void]$capture.AppendLine($line)
        }
        $dockerExit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $oldPreference
        if ($LogFile) { [IO.File]::WriteAllText($LogFile, $capture.ToString(), $utf8NoBom) }
    }
    if ($dockerExit -ne 0) { throw "Docker returned exit code $dockerExit. Fix the error above before continuing." }
}

function Wait-Http {
    param([string]$Url)
    $deadline = [DateTime]::UtcNow.AddSeconds(120)
    $lastError = 'no response'
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            Invoke-LabHttp -Url $Url -TimeoutSec 5 | Out-Null
            return
        }
        catch {
            $lastError = $_.Exception.Message
            if ($_.ErrorDetails.Message) { $lastError += ' ' + $_.ErrorDetails.Message }
            if ($_.Exception.Response) {
                $status = [int]$_.Exception.Response.StatusCode
                if ($status -ge 400 -and $status -lt 500) {
                    throw "Service rejected the readiness request: $Url (HTTP $status). $lastError"
                }
            }
            Start-Sleep -Seconds 2
        }
    }
    throw "Service did not become ready: $Url. Last error: $lastError"
}

function Read-Seconds {
    param([string]$Text, [string]$Pattern)
    $found = [regex]::Match($Text, $Pattern, [Text.RegularExpressions.RegexOptions]::Multiline)
    if (-not $found.Success) { throw 'Measurement output has no expected p99 line. No result will be invented.' }
    $number = [double]::Parse($found.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture)
    if ($found.Groups[2].Value -eq 'ms') { $number /= 1000.0 }
    if ($number -le 0 -or [double]::IsNaN($number) -or [double]::IsInfinity($number)) {
        throw 'The measured percentile is invalid.'
    }
    return $number
}

function Save-Gap {
    param([string]$LogFile)
    $logText = [IO.File]::ReadAllText($LogFile)
    $client = Read-Seconds $logText '^\s*q \(p99\)\s+([0-9]+(?:\.[0-9]+)?)\s*(ms|s)\b'
    $server = Read-Seconds $logText "your histogram's own p99 over the run:\s*([0-9]+(?:\.[0-9]+)?)\s*(ms|s)\b"
    $gap = [Math]::Round($client - $server, 7)
    if ($gap -le 0) { throw 'The measured client-server gap is not positive. Inspect lab3-load-gap.txt.' }
    $result = [ordered]@{
        toxic = [ordered]@{type = 'latency'; latency = 100; jitter = 10}
        client_p99_seconds = $client
        server_p99_seconds = $server
        gap_seconds = $gap
    }
    $culture = [Globalization.CultureInfo]::InvariantCulture
    $readme = @'
<!-- ai-generated: 100% - Codex wrote the explanation; numerical results come from an actual Toxiproxy run. -->
# Pomiar opoznienia klienta i serwera

Pomiar UTC: @@TIME@@. Profil kb-index: wojbra1993, tak samo jak login w itsmlab.yaml.
Rzeczywisty pomiar itsmlab load 3: 5 sekund rozgrzewki, potem 60 sekund ruchu
40 zadan na sekunde. Klient kierowal zadania /kb/search przez Toxiproxy do svcdesk.
Toxic dzialal downstream z toxicity=1, latency=100 ms i jitter=10 ms.

Z tego samego przebiegu: p99 klienta = @@CLIENT@@ s, p99 serwera = @@SERVER@@ s.
gap_seconds = p99 klienta - p99 serwera = @@GAP@@ s. Wartosci zapisane w gap.json
pochodza z linii q (p99) oraz your histogram's own p99 over the run w rzeczywistym
wyjsciu checkera. Nie wpisywalem oczekiwanych 100 ms w miejsce wyniku pomiaru.

Klient mierzy czas do otrzymania odpowiedzi przez proxy. Histogram w aplikacji
mierzy wykonanie zadania po stronie serwera, w tym oczekiwanie na kb-index,
do wyslania ostatniego fragmentu odpowiedzi. Opoznienie wstawione przez proxy
jest poza aplikacja, wiec zwieksza czas klienta bez takiego samego wzrostu
czasu serwera. Ten sam serwer moze zatem miec dobry histogram i nadal dawac
uzytkownikowi wyraznie wolniejsza odpowiedz z powodu sieci.

P99 serwera jest estymata histogram_quantile(0.99) z przyrostow bucketow w oknie
pomiaru. P99 klienta pochodzi z oha, z korekta opoznienia planowanego ruchu.
Odejmowanie tych percentyli nie jest pomiarem opoznienia jednej konkretnej
odpowiedzi. Jitter, losowy profil kb-index, granice bucketow i obciazenie hosta
powoduja, ze roznica nie musi wynosic dokladnie 0.100 s. Checker powtarza probe
przez 30 sekund i porownuje roznice z tolerancja max(15 ms, 30% swojej roznicy).

Powtorzenie z katalogu repozytorium: .\scripts\lab3-stretch.ps1 -Part gap.
Skrypt stawia svcdesk, kb-index i Toxiproxy, konfiguruje toxic przez API,
uruchamia checker w tej samej sieci Dockera, zapisuje wyniki i zatrzymuje
wylacznie swoj projekt pomiarowy. Log lokalny: lab3-load-gap.txt.
'@
    $readme = $readme.Replace('@@TIME@@', [DateTime]::UtcNow.ToString('o')).Replace('@@CLIENT@@', $client.ToString('F7', $culture)).Replace('@@SERVER@@', $server.ToString('F7', $culture)).Replace('@@GAP@@', $gap.ToString('F7', $culture))
    [void][IO.Directory]::CreateDirectory((Join-Path $repoPath 'gap'))
    [IO.File]::WriteAllText((Join-Path $repoPath 'gap.json'), ($result | ConvertTo-Json -Depth 4), $utf8NoBom)
    [IO.File]::WriteAllText((Join-Path $repoPath 'gap\README.md'), $readme, $utf8NoBom)
    Write-Host ('Recorded real gap: {0} ms.' -f ($gap * 1000)) -ForegroundColor Green
}

Push-Location $repoPath
$transcriptStarted = $false
try {
    Start-Transcript -Path (Join-Path $repoPath "lab3-stretch-$Part.log") -Force | Out-Null
    $transcriptStarted = $true
    Invoke-Docker -DockerArgs @('info', '--format', '{{.ServerVersion}}')
    if ($Part -in @('all', 'gap')) {
        Write-Host '1. Measuring latency through Toxiproxy (about two minutes after the build).' -ForegroundColor Cyan
        $gapCompose = @('compose', '-p', 'itsm-lab3-gap', '-f', $rootCompose, '--profile', 'gap')
        try {
            Invoke-Docker -DockerArgs ($gapCompose + @('up', '-d', '--build', 'svcdesk', 'kb-index', 'toxiproxy'))
            Wait-Http 'http://localhost:8080/health'
            Wait-Http 'http://localhost:8081/healthz'
            Wait-Http 'http://localhost:8474/version'
            # A previous interrupted run can leave the named proxy. Remove that one only.
            $proxies = Invoke-LabHttp -Url 'http://localhost:8474/proxies'
            if ($proxies.PSObject.Properties.Name -contains 'svcdesk') {
                Invoke-LabHttp -Method Delete -Url 'http://localhost:8474/proxies/svcdesk' | Out-Null
            }
            Invoke-LabHttp -Method Post -Url 'http://localhost:8474/proxies' -Body '{"name":"svcdesk","listen":"0.0.0.0:8666","upstream":"svcdesk:8080","enabled":true}' | Out-Null
            Invoke-LabHttp -Method Post -Url 'http://localhost:8474/proxies/svcdesk/toxics' -Body '{"type":"latency","stream":"downstream","toxicity":1.0,"attributes":{"latency":100,"jitter":10}}' | Out-Null
            $checkerImage = 'ghcr.io/swasik/itsmlab:2026'
            foreach ($line in Get-Content -LiteralPath (Join-Path $repoPath 'itsmlab.yaml')) {
                if ($line -match '^checker_image:\s*"?([^"#\s]+)"?') { $checkerImage = $Matches[1]; break }
            }
            if ($env:ITSMLAB_IMAGE) { $checkerImage = $env:ITSMLAB_IMAGE }
            $loadLog = Join-Path $repoPath 'lab3-load-gap.txt'
            Invoke-Docker -DockerArgs @('run', '--rm', '--network', 'itsm-lab3-gap_default', '-v', "${repoPath}:/work", '-w', '/work', '-v', '/var/run/docker.sock:/var/run/docker.sock', $checkerImage, 'load', '3', '--base-url', 'http://toxiproxy:8666', '--service-url', 'kb-index=http://kb-index:8080') -LogFile $loadLog
            Save-Gap $loadLog
        }
        finally {
            Invoke-Docker -DockerArgs ($gapCompose + @('down'))
        }
    }
    if ($Part -in @('all', 'genai')) {
        Write-Host '2. Preparing local Ollama and Qwen. The first run downloads Docker images and a 400 MB model.' -ForegroundColor Cyan
        $aiCommand = @('compose', '-p', 'itsm-lab3-ai', '-f', $aiCompose)
        try {
            Invoke-Docker -DockerArgs ($aiCommand + @('build', 'capture'))
            Invoke-Docker -DockerArgs ($aiCommand + @('up', '-d', '--wait', '--wait-timeout', '180', 'ollama'))
            Invoke-Docker -DockerArgs ($aiCommand + @('exec', '-T', 'ollama', 'ollama', 'pull', 'qwen2.5:0.5b'))
            Invoke-Docker -DockerArgs ($aiCommand + @('run', '--rm', '--no-deps', 'capture'))
        }
        finally {
            # Keep the named model volume so another run need not download it again.
            Invoke-Docker -DockerArgs ($aiCommand + @('down'))
        }
    }
    Write-Host 'DONE. The real Stretch evidence is saved. Next: .\itsmlab.ps1 verify 3 --json report.json' -ForegroundColor Green
}
finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
    Pop-Location
}
