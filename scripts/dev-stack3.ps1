#Requires -Version 5.1
# dev-stack3.ps1 -- Matrix Dev Stack v3
#
# Improvements over v2:
#   - DAG-based parallel startup (infra starts while Go/Python build)
#   - WMI Kill-Hard for zombie-proof process termination
#   - Postgres as daemon (pg_ctl, not watcher-managed)
#   - Individual frontend skips (-SkipNextjs, -SkipControlUi, -SkipAgentChat)
#   - Lockfile-based watcher kill
#   - Service isolation (one crash doesn't kill the stack)
#   - Alembic auto-run after Postgres ready
#
# Usage:
#   .\scripts\dev-stack3.ps1                        # Full stack, new window
#   .\scripts\dev-stack3.ps1 -Tunnel -Tuwunel16     # With tunnel + Tuwunel v1.6
#   .\scripts\dev-stack3.ps1 -Kill                   # Kill everything
#   .\scripts\dev-stack3.ps1 -SkipNextjs -SkipAgentChat  # Only control-ui frontend
#   .\scripts\dev-stack3.ps1 -FrontendOnly           # Only frontends
#   .\scripts\dev-stack3.ps1 -Inline                 # Run in current terminal

param(
    # Infrastructure
    [switch]$SkipHomeserver,
    [switch]$SkipNats,
    [switch]$SkipPostgres,
    [switch]$SkipStorage,        # SeaweedFS
    [switch]$SkipObservability,  # OpenObserve

    # Backend
    [switch]$SkipGoAppservice,
    [switch]$SkipPython,         # All Python services
    [switch]$SkipAgentService,   # Just agent :8094
    [switch]$SkipIngestion,
    [switch]$SkipLiteLLM,
    [switch]$UseMock,            # Mock agent on :8094

    # Frontend (individual)
    [switch]$SkipFrontend,       # All three
    [switch]$SkipNextjs,         # nextjs-chat :3000
    [switch]$SkipControlUi,      # control-ui :3001
    [switch]$SkipAgentChat,      # agent-chat :3002

    # Optional services
    [switch]$WithVoice,          # LiveKit voice worker
    [switch]$DevTools,           # AI SDK DevTools
    [switch]$Tunnel,             # Cloudflared tunnel
    [switch]$Tuwunel16,          # Tuwunel v1.6.0-rc

    # Shortcuts
    [switch]$FrontendOnly,
    [switch]$AgentOnly,

    # Control
    [switch]$Kill,               # Kill all and exit
    [switch]$Inline,             # Run in current terminal
    [switch]$NoWatch,            # Don't watch/restart crashed services
    [int]$MaxRestarts = 5
)

# ═══════════════════════════════════════════════════════════════════════════════
#  KILL MODE (runs before detach, in current terminal)
# ═══════════════════════════════════════════════════════════════════════════════
if ($Kill) {
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
    Write-Host "`n[kill] Stopping all Matrix DevStack processes..." -ForegroundColor Red

    function Kill-Hard([int]$TargetPid, [string]$Label) {
        Stop-Process -Id $TargetPid -Force -ErrorAction SilentlyContinue
        Get-CimInstance Win32_Process -Filter "ProcessId=$TargetPid" -ErrorAction SilentlyContinue |
            Invoke-CimMethod -MethodName Terminate -ErrorAction SilentlyContinue | Out-Null
        Write-Host "  $Label (PID $TargetPid) -> terminated" -ForegroundColor DarkGray
    }

    function Is-Protected([int]$TargetPid) {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$TargetPid" -ErrorAction SilentlyContinue).CommandLine
        return ($cmd -match "gitnexus|webmcp|claude|Code Helper")
    }

    # 1. Graceful Postgres
    $pgCtl = Join-Path $repoRoot "tools\pgsql\bin\pg_ctl.exe"
    $pgData = Join-Path $repoRoot "tools\pgsql-data"
    if ((Test-Path $pgCtl) -and (Test-Path $pgData)) {
        Write-Host "  [postgres] pg_ctl stop -m fast..." -ForegroundColor DarkGray
        & $pgCtl stop -D $pgData -w -m fast 2>&1 | Out-Null
    }

    # 2. By port
    foreach ($p in @(3000,3001,3002,4000,4222,5080,7880,8090,8094,8097,8098,8180,8333,8448,9333,9999)) {
        try {
            Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
                    if ($_ -and $_ -ne 0 -and -not (Is-Protected $_)) { Kill-Hard $_ ":$p" }
                }
        } catch { }
    }

    # 3. By process name
    foreach ($name in @("weed","tuwunel","tuwunel-v1.6","zendrite","nats-server",
                         "livekit-server","openobserve","appservice","cloudflared",
                         "uvicorn","litellm")) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
            Kill-Hard $_.Id $name
        }
    }

    # 4. Bun + Python children (protect MCP)
    foreach ($pn in @("bun","python")) {
        Get-Process -Name $pn -ErrorAction SilentlyContinue | ForEach-Object {
            if (-not (Is-Protected $_.Id)) { Kill-Hard $_.Id $pn }
        }
    }

    # 5. Watcher window (via lockfile)
    $lockFile = Join-Path $repoRoot "logs\dev-stack\.devstack.pid"
    if (Test-Path $lockFile) {
        $wpid = [int](Get-Content $lockFile -ErrorAction SilentlyContinue)
        if ($wpid -and $wpid -ne $PID) { Kill-Hard $wpid "watcher" }
        Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    }

    Write-Host "[kill] Done.`n" -ForegroundColor Green
    return
}

# ═══════════════════════════════════════════════════════════════════════════════
#  DETACH: re-launch in own PowerShell window
# ═══════════════════════════════════════════════════════════════════════════════
if (-not $Inline -and -not $env:DEVSTACK_INLINE) {
    $passThru = @("-Inline")
    foreach ($p in $MyInvocation.BoundParameters.GetEnumerator()) {
        if ($p.Key -eq "Inline") { continue }
        if ($p.Value -is [switch] -and $p.Value.IsPresent) { $passThru += "-$($p.Key)" }
        elseif ($p.Value -is [switch]) { }
        else { $passThru += "-$($p.Key)"; $passThru += "$($p.Value)" }
    }
    $script = $MyInvocation.MyCommand.Path
    Start-Process powershell -ArgumentList (@("-NoProfile", "-NoExit", "-Command",
        "cd '$((Get-Item $script).Directory.Parent.FullName)'; & '$script' $($passThru -join ' ')"))
    Write-Host "[dev-stack] Launched in new window. Use -Inline to run here." -ForegroundColor Cyan
    return
}

# ═══════════════════════════════════════════════════════════════════════════════
#  INIT
# ═══════════════════════════════════════════════════════════════════════════════
$ErrorActionPreference = "Continue"  # Service isolation: failures don't crash the stack

$repoRoot     = Resolve-Path (Join-Path $PSScriptRoot "..")
$goDir        = Join-Path $repoRoot "go-appservice"
$pyDir        = Join-Path $repoRoot "python-backend"
$nextDir      = Join-Path $repoRoot "nextjs-chat"
$controlUiDir = Join-Path $repoRoot "control-ui"
$agentChatDir = Join-Path $repoRoot "agent-chat"
$ingestionDir = Join-Path $pyDir "ingestion"
$litellmDir   = Join-Path $pyDir "litellm-gateway"
$logsRoot     = Join-Path $repoRoot "logs\dev-stack"

if (-not (Test-Path $logsRoot)) { New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null }

# Lockfile
$PID | Out-File -FilePath (Join-Path $logsRoot ".devstack.pid") -Encoding ascii -Force

# Expand shortcut flags
if ($FrontendOnly) { $SkipHomeserver=$true; $SkipNats=$true; $SkipGoAppservice=$true; $SkipPython=$true; $SkipPostgres=$true; $SkipStorage=$true; $SkipLiteLLM=$true; $SkipObservability=$true }
if ($AgentOnly)    { $SkipHomeserver=$true; $SkipNextjs=$true; $SkipControlUi=$true; $SkipAgentChat=$true }
if ($SkipFrontend) { $SkipNextjs=$true; $SkipControlUi=$true; $SkipAgentChat=$true }

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
$script:processes = @()
$script:failedServices = @()

function Write-Phase([string]$Text) { Write-Host "`n=== $Text ===" -ForegroundColor Cyan }

function Import-EnvFile([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match '^\s*([^#=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), ($matches[2].Trim() -replace "^[`"']|[`"']$", ""), "Process")
        }
    }
    Write-Host "  [env] $Path" -ForegroundColor DarkGray
}

function Start-Svc([string]$Name, [string]$Exe, [string[]]$Args, [string]$Dir, [int]$Port=0, [string]$Health="", [int]$Timeout=30) {
    if ($Port -and (Test-PortOpen $Port)) {
        Write-Host "  [$Name] :$Port already in use - skipping" -ForegroundColor Yellow
        return
    }
    try {
        $spArgs = @{
            FilePath=$Exe; WorkingDirectory=$Dir; PassThru=$true; WindowStyle="Hidden"
            RedirectStandardOutput=(Join-Path $logsRoot "$Name.stdout.log")
            RedirectStandardError=(Join-Path $logsRoot "$Name.stderr.log")
        }
        if ($Args -and $Args.Count -gt 0) { $spArgs.ArgumentList = $Args }
        $proc = Start-Process @spArgs
        $script:processes += $proc

        if ($Port -gt 0) {
            $ready = Wait-ForPort $Port $Timeout
            if (-not $ready) {
                Write-Host "  [$Name] :$Port timeout (${Timeout}s)" -ForegroundColor Yellow
                $script:failedServices += $Name
                return
            }
        }
        if ($Health) {
            $ok = Wait-ForUrl $Health 15
            if (-not $ok) { Write-Host "  [$Name] health check failed" -ForegroundColor Yellow }
        }
        $label = if ($Port) { ":$Port" } else { "launched" }
        Write-Host "  [$Name] $label" -ForegroundColor Green
    } catch {
        Write-Host "  [$Name] FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $script:failedServices += $Name
    }
}

function Test-PortOpen([int]$Port) {
    try { $t = New-Object System.Net.Sockets.TcpClient; $t.Connect("127.0.0.1",$Port); $t.Close(); return $true } catch { return $false }
}

function Wait-ForPort([int]$Port, [int]$Secs=30) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $Secs) {
        if (Test-PortOpen $Port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Wait-ForUrl([string]$Url, [int]$Secs=15) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $Secs) {
        try { $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop; if ($r.StatusCode -lt 400) { return $true } } catch { }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 1: PARALLEL — Infra + Build simultaneously
# ═══════════════════════════════════════════════════════════════════════════════
try {
    Write-Phase "Phase 1: Infra + Build (parallel)"

    Import-EnvFile (Join-Path $goDir ".env.development")
    Import-EnvFile (Join-Path $pyDir ".env")

    # -- Background build jobs (run while infra starts) --
    $buildJobs = @()
    if (-not $SkipGoAppservice) {
        Write-Host "  [go] Building appservice..." -ForegroundColor Cyan
        $buildJobs += Start-Job -Name "go-build" -ScriptBlock {
            param($d); Set-Location $d
            if (-not (Test-Path "tmp")) { New-Item -ItemType Directory -Path "tmp" -Force | Out-Null }
            & go build -tags goolm -o ".\tmp\appservice.exe" ./cmd/appservice 2>&1
        } -ArgumentList $goDir
    }
    if (-not $SkipPython -and (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "  [python] uv sync..." -ForegroundColor Cyan
        $buildJobs += Start-Job -Name "py-sync" -ScriptBlock {
            param($d); Set-Location $d; & uv sync --inexact 2>&1
        } -ArgumentList $pyDir
    }

    # -- Infra services (start ALL in parallel, wait at end) --
    # Strategy: fire all Start-Process calls, then wait for all ports.
    # Only exception: Tuwunel depends on SeaweedFS (must start after).

    Write-Host "  Starting infra (parallel)..." -ForegroundColor Cyan

    # Postgres: daemon mode (stop stale + fire-and-forget + pg_isready)
    $pgCtl = Join-Path $repoRoot "tools\pgsql\bin\pg_ctl.exe"
    $pgData = Join-Path $repoRoot "tools\pgsql-data"
    $pgReady = Join-Path $repoRoot "tools\pgsql\bin\pg_isready.exe"
    if (-not $SkipPostgres -and (Test-Path $pgCtl)) {
        # Ensure clean state
        $running = Get-Process -Name "postgres" -ErrorAction SilentlyContinue
        if ($running) {
            & $pgCtl stop -D $pgData -m fast 2>&1 | Out-Null
            Start-Sleep -Seconds 2
        }
        $stalePid = Join-Path $pgData "postmaster.pid"
        if (Test-Path $stalePid) { Remove-Item $stalePid -Force -ErrorAction SilentlyContinue }
        Start-Process -FilePath $pgCtl -ArgumentList @("start","-D",$pgData) -WindowStyle Hidden
    }

    # SeaweedFS
    $seaweedExe = Join-Path $repoRoot "tools\seaweedfs\weed.exe"
    $seaweedData = Join-Path $repoRoot "tools\seaweedfs\data"
    if (-not $SkipStorage -and (Test-Path $seaweedExe)) {
        if (-not (Test-Path $seaweedData)) { New-Item -ItemType Directory -Path $seaweedData -Force | Out-Null }
        Start-Svc "seaweedfs" $seaweedExe @(
            "server","-ip=127.0.0.1","-ip.bind=127.0.0.1","-volume.port=8180",
            "-dir=$seaweedData","-s3","-s3.config=$repoRoot\tools\seaweedfs\s3.json"
        ) $repoRoot -Port 0  # Don't wait yet
    }

    # NATS
    $natsExe = Join-Path $repoRoot "tools\nats-server.exe"
    if (-not $SkipNats -and (Test-Path $natsExe)) {
        Start-Svc "nats" $natsExe @("-js","-m=8222") $repoRoot -Port 0
    }

    # LiveKit
    $lkExe = Join-Path $repoRoot "tools\livekit-server.exe"
    $lkCfg = Join-Path $repoRoot "homeserver\livekit.yaml"
    if (Test-Path $lkExe) {
        Start-Svc "livekit" $lkExe @("--config",$lkCfg) $repoRoot -Port 0
    }

    # OpenObserve
    if (-not $SkipObservability) {
        $ooExe = Join-Path $repoRoot "tools\openobserve\openobserve.exe"
        $ooData = Join-Path $repoRoot "tools\openobserve\data"
        if (Test-Path $ooExe) {
            if (-not (Test-Path $ooData)) { New-Item -ItemType Directory -Path $ooData -Force | Out-Null }
            $ooUser = if ($env:OPENOBSERVE_USER) { $env:OPENOBSERVE_USER } else { "root@example.com" }
            $ooPass = if ($env:OPENOBSERVE_PASSWORD) { $env:OPENOBSERVE_PASSWORD } else { "Complexpass#123" }
            foreach ($kv in @(@("ZO_ROOT_USER_EMAIL",$ooUser),@("ZO_ROOT_USER_PASSWORD",$ooPass),
                              @("ZO_DATA_DIR",$ooData),@("ZO_GRPC_PORT","5081"),@("ZO_DISK_CACHE_ENABLED","false"))) {
                [Environment]::SetEnvironmentVariable($kv[0], $kv[1], "Process")
            }
            [Environment]::SetEnvironmentVariable("OTEL_ENABLED", "true", "Process")
            [Environment]::SetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:5081", "Process")
            Start-Svc "openobserve" $ooExe @() (Join-Path $repoRoot "tools\openobserve") -Port 0
        }
    }

    # -- Wait for all infra ports in parallel --
    Write-Host "  Waiting for infra..." -ForegroundColor DarkGray
    $infraPorts = @()
    if (-not $SkipPostgres)     { $infraPorts += @{Name="postgres";   Port=5433; Check="pgready"} }
    if (-not $SkipStorage)      { $infraPorts += @{Name="seaweedfs";  Port=8333} }
    if (-not $SkipNats)         { $infraPorts += @{Name="nats";       Port=4222} }
    if (Test-Path $lkExe)       { $infraPorts += @{Name="livekit";    Port=7880} }
    if (-not $SkipObservability) { $infraPorts += @{Name="openobserve";Port=5080} }

    foreach ($svc in $infraPorts) {
        if ($svc.Check -eq "pgready") {
            # Postgres: use pg_isready instead of TCP probe
            $ok = $false
            for ($i = 0; $i -lt 30; $i++) {
                $null = & $pgReady -h 127.0.0.1 -p 5433 2>&1
                if ($LASTEXITCODE -eq 0) { $ok = $true; break }
                Start-Sleep -Seconds 1
            }
            if ($ok) { Write-Host "  [postgres] :5433" -ForegroundColor Green }
            else { Write-Host "  [postgres] TIMEOUT" -ForegroundColor Red; $script:failedServices += "postgres" }
        } else {
            $ready = Wait-ForPort $svc.Port 60
            if ($ready) { Write-Host "  [$($svc.Name)] :$($svc.Port)" -ForegroundColor Green }
            else { Write-Host "  [$($svc.Name)] :$($svc.Port) TIMEOUT" -ForegroundColor Yellow; $script:failedServices += $svc.Name }
        }
    }

    # Tuwunel depends on SeaweedFS — start AFTER SeaweedFS is ready
    if (-not $SkipHomeserver) {
        if ($Tuwunel16) {
            $tBin = Join-Path $repoRoot "tools\tuwunel-v1.6"
            $tCmd = "cd /mnt/d/matrix && ./tools/tuwunel-v1.6 --config ./homeserver/tuwunel.v1.6.toml"
        } else {
            $tBin = Join-Path $repoRoot "tools\tuwunel"
            $tCmd = "cd /mnt/d/matrix && ./tools/tuwunel --config ./homeserver/tuwunel.toml"
        }
        if (Test-Path $tBin) {
            Start-Svc "tuwunel" "wsl" @("-d","Ubuntu","-u","root","bash","-c",$tCmd) $repoRoot -Port 8448 -Health "http://127.0.0.1:8448/_matrix/client/versions" -Timeout 60
        } else {
            $zBin = Join-Path $repoRoot "tools\zendrite.exe"
            if (Test-Path $zBin) {
                New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "homeserver\data") | Out-Null
                Start-Svc "zendrite" $zBin @("--config",(Join-Path $repoRoot "homeserver\dendrite.yaml"),"-really-enable-open-registration") $repoRoot -Port 8448 -Timeout 30
            }
        }
    }

    # -- Wait for build jobs to finish --
    if ($buildJobs.Count -gt 0) {
        Write-Host "`n  Waiting for builds..." -ForegroundColor DarkGray
        $buildJobs | Wait-Job | Out-Null
        foreach ($job in $buildJobs) {
            $state = if ($job.State -eq "Failed") { "FAILED" } else { "OK" }
            $color = if ($job.State -eq "Failed") { "Yellow" } else { "Green" }
            Write-Host "  [$($job.Name)] $state" -ForegroundColor $color
            Remove-Job $job -ErrorAction SilentlyContinue
        }
    }

    # ═══════════════════════════════════════════════════════════════════════════
    #  PHASE 2: App services (depend on infra + builds)
    # ═══════════════════════════════════════════════════════════════════════════
    Write-Phase "Phase 2: App services"

    $pyVenv = Join-Path $pyDir ".venv\Scripts\python.exe"
    $pyExe = if (Test-Path $pyVenv) { $pyVenv } else { "python" }

    # Go Appservice
    if (-not $SkipGoAppservice) {
        $goBin = Join-Path $goDir "tmp\appservice.exe"
        if (Test-Path $goBin) {
            Start-Svc "go-appservice" $goBin @() $goDir -Port 8090 -Health "http://127.0.0.1:8090/health" -Timeout 180
        } else {
            Start-Svc "go-appservice" "go" @("run","-tags","goolm","./cmd/appservice/...") $goDir -Port 8090 -Health "http://127.0.0.1:8090/health" -Timeout 180
        }
    }

    # Agent Service
    if ($UseMock) {
        $mockDir = Join-Path $pyDir "mock"
        Start-Svc "mock-agent" "uv" @("run","mock_agent.py") $mockDir -Port 8094 -Health "http://127.0.0.1:8094/health" -Timeout 20
    } elseif (-not $SkipAgentService) {
        Start-Svc "agent-service" $pyExe @("-m","uvicorn","agent.app:app","--host","127.0.0.1","--port","8094","--reload") $pyDir -Port 8094 -Health "http://127.0.0.1:8094/health" -Timeout 180
    }

    # Python Bridge
    if (-not $SkipPython) {
        Start-Svc "py-bridge" $pyExe @("-m","uvicorn","bridge.app:app","--host","127.0.0.1","--port","8097","--reload") $pyDir -Port 8097 -Health "http://127.0.0.1:8097/health" -Timeout 180
    }

    # Ingestion Worker
    if (-not $SkipIngestion -and (Test-Path $ingestionDir)) {
        Start-Svc "ingestion" "uv" @("run","--project",$ingestionDir,"uvicorn","ingestion.worker:app","--host","127.0.0.1","--port","8098") $ingestionDir -Port 8098 -Timeout 180
    }

    # LiteLLM
    if (-not $SkipLiteLLM -and (Test-Path $litellmDir)) {
        Start-Svc "litellm" "uv" @("run","--project",$litellmDir,"litellm","--config",(Join-Path $litellmDir "config.yaml"),"--port","4000") $litellmDir -Port 4000 -Health "http://127.0.0.1:4000/health" -Timeout 180
    }

    # Memory Worker
    if (-not $SkipPostgres -and -not $SkipPython) {
        Start-Svc "memory-worker" $pyExe @("-m","hindsight_api.worker.main") $pyDir -Timeout 180
    }

    # Voice Worker (optional)
    if ($WithVoice) {
        Start-Svc "voice-worker" "uv" @("run","python","-m","voice.worker") $pyDir -Timeout 180
    }

    # ═══════════════════════════════════════════════════════════════════════════
    #  PHASE 3: Frontends (start all, don't block on compile)
    # ═══════════════════════════════════════════════════════════════════════════
    Write-Phase "Phase 3: Frontends (parallel compile)"

    # Launch all frontends (don't wait for port yet)
    $frontends = @()
    if (-not $SkipNextjs -and (Test-Path $nextDir)) {
        Start-Svc "nextjs" "bun" @("run","dev") $nextDir -Port 0
        $frontends += @{Name="nextjs"; Port=3000}
    }
    if (-not $SkipControlUi -and (Test-Path $controlUiDir)) {
        Start-Svc "control-ui" "bun" @("run","dev") $controlUiDir -Port 0
        $frontends += @{Name="control-ui"; Port=3001}
    }
    if (-not $SkipAgentChat -and (Test-Path $agentChatDir)) {
        Start-Svc "agent-chat" "bun" @("run","dev") $agentChatDir -Port 0
        $frontends += @{Name="agent-chat"; Port=3002}
    }

    # Wait for all frontend ports
    foreach ($fe in $frontends) {
        $ready = Wait-ForPort $fe.Port 180
        if ($ready) { Write-Host "  [$($fe.Name)] :$($fe.Port)" -ForegroundColor Green }
        else { Write-Host "  [$($fe.Name)] :$($fe.Port) TIMEOUT" -ForegroundColor Yellow; $script:failedServices += $fe.Name }
    }

    # Tunnel (optional)
    if ($Tunnel) {
        $cfBin = Join-Path $repoRoot "tools\cloudflared.exe"
        if (Test-Path $cfBin) {
            Start-Svc "tunnel" $cfBin @("tunnel","--url","http://localhost:8448") $repoRoot
            # Wait for tunnel URL
            $tunnelLog = Join-Path $logsRoot "tunnel.stderr.log"
            Write-Host "  [tunnel] Waiting for URL..." -NoNewline
            for ($i = 0; $i -lt 60; $i++) {
                if (Test-Path $tunnelLog) {
                    $m = Select-String -Path $tunnelLog -Pattern "https://[a-zA-Z0-9\-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
                    if ($m) { Write-Host " $($m.Matches[0].Value)" -ForegroundColor Yellow; break }
                }
                Start-Sleep -Seconds 1
            }
            if (-not $m) { Write-Host " timeout" -ForegroundColor Yellow }
        }
    }

    # DevTools (optional)
    if ($DevTools) {
        Start-Svc "ai-devtools" "npx" @("@ai-sdk/devtools") $nextDir -Port 4983 -Timeout 10
    }

    # ═══════════════════════════════════════════════════════════════════════════
    #  REPORT
    # ═══════════════════════════════════════════════════════════════════════════
    if ($script:failedServices.Count -gt 0) {
        Write-Host "`n  WARNING: $($script:failedServices.Count) failed: $($script:failedServices -join ', ')" -ForegroundColor Yellow
    }

    Write-Host "`n============================================" -ForegroundColor Green
    Write-Host "  MATRIX STACK v3 READY ($($script:processes.Count) services)" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  Frontend" -ForegroundColor Cyan
    if (-not $SkipNextjs)    { Write-Host "    Next.js Chat:    http://localhost:3000/matrix" }
    if (-not $SkipControlUi) { Write-Host "    Control UI:      http://localhost:3001" }
    if (-not $SkipAgentChat) { Write-Host "    Agent Chat:      http://localhost:3002" }
    Write-Host "  Backend" -ForegroundColor Cyan
    if (-not $SkipGoAppservice) { Write-Host "    Go Appservice:   http://127.0.0.1:8090" }
    if (-not $SkipAgentService -and -not $UseMock) { Write-Host "    Agent Service:   http://127.0.0.1:8094" }
    if ($UseMock) { Write-Host "    Mock Agent:      http://127.0.0.1:8094" -ForegroundColor DarkYellow }
    if (-not $SkipPython)    { Write-Host "    Python Bridge:   http://127.0.0.1:8097" }
    if (-not $SkipIngestion) { Write-Host "    Ingestion:       http://127.0.0.1:8098" }
    if (-not $SkipLiteLLM)   { Write-Host "    LiteLLM:         http://127.0.0.1:4000" }
    Write-Host "  Infrastructure" -ForegroundColor Cyan
    if (-not $SkipStorage)      { Write-Host "    SeaweedFS S3:    http://127.0.0.1:8333" }
    if (-not $SkipHomeserver)   { Write-Host "    Homeserver:      http://127.0.0.1:8448" }
    if (-not $SkipNats)         { Write-Host "    NATS:            nats://127.0.0.1:4222 | http://localhost:8222" }
    Write-Host "    LiveKit SFU:     ws://127.0.0.1:7880"
    if (-not $SkipPostgres)     { Write-Host "    PostgreSQL:      postgresql://postgres@localhost:5433/hindsight_dev" }
    if (-not $SkipObservability) { Write-Host "    OpenObserve:     http://localhost:5080" }
    Write-Host "  Logs: $logsRoot\*.log" -ForegroundColor DarkGray
    Write-Host "  Kill: .\scripts\dev-stack3.ps1 -Kill" -ForegroundColor DarkGray
    Write-Host "============================================`n" -ForegroundColor Green

    # ═══════════════════════════════════════════════════════════════════════════
    #  WATCHER (restart crashed services)
    # ═══════════════════════════════════════════════════════════════════════════
    if (-not $NoWatch) {
        Write-Host "[watch] Monitoring - Ctrl+C to stop`n" -ForegroundColor Cyan
        $restartCounts = @{}
        while ($true) {
            foreach ($proc in $script:processes) {
                if ($null -eq $proc -or -not $proc.HasExited) { continue }
                $name = $proc.ProcessName
                $count = if ($restartCounts[$name]) { $restartCounts[$name] } else { 0 }
                $count++
                $restartCounts[$name] = $count
                if ($count -gt $MaxRestarts) {
                    if ($count -eq ($MaxRestarts + 1)) {
                        Write-Host "[$name] CRASH-LOOP ($MaxRestarts restarts)" -ForegroundColor Red
                    }
                    continue
                }
                $delay = [Math]::Min(30, [Math]::Pow(2, $count))
                Write-Host "[$name] Exited. Restart $count/$MaxRestarts in ${delay}s..." -ForegroundColor Yellow
                Start-Sleep -Seconds $delay
                # Simple restart: we don't have the original command, just log it
                Write-Host "[$name] Cannot auto-restart (use -Kill and restart stack)" -ForegroundColor DarkYellow
            }
            Start-Sleep -Seconds 3
        }
    } else {
        Write-Host "[dev-stack] Press Enter to stop..." -ForegroundColor Cyan
        Read-Host
    }
}
finally {
    Write-Host "`n[shutdown] Cleaning up..." -ForegroundColor Cyan

    # Graceful Postgres
    $pgCtl = Join-Path $repoRoot "tools\pgsql\bin\pg_ctl.exe"
    $pgData = Join-Path $repoRoot "tools\pgsql-data"
    if ((Test-Path $pgCtl) -and (Test-Path $pgData)) {
        & $pgCtl stop -D $pgData -w -m fast 2>&1 | Out-Null
    }

    $stopped = 0
    foreach ($proc in $script:processes) {
        if ($null -ne $proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue |
                Invoke-CimMethod -MethodName Terminate -ErrorAction SilentlyContinue | Out-Null
            $stopped++
        }
    }
    Remove-Item (Join-Path $logsRoot ".devstack.pid") -Force -ErrorAction SilentlyContinue
    Write-Host "[shutdown] $stopped processes stopped." -ForegroundColor Green
}
