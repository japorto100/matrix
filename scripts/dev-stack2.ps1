# dev-stack2.ps1 -- Matrix Dev Stack (v2)
# Usage: .\scripts\dev-stack2.ps1 [-UseMock] [-Tunnel] [-SkipHomeserver] [-SkipNats] [-SkipPostgres] ...
# By default opens its own PowerShell window. Use -Inline to run in current terminal.
# Design: 3 phases (Prepare -> Register+Start -> Watch)
#
# Port 8094 behavior (changed 08.04.2026 for Slice 7):
#   Default:   Real agent-service (agent.app:app) with all /api/v1/control/* routes
#   -UseMock:  LLM Mock Agent (only /api/v1/agent/chat + /health, no control API)
#   -SkipAgentService: neither starts (port 8094 free for manual runs)

param(
    [switch]$SkipHomeserver,
    [switch]$SkipNats,
    [switch]$SkipPostgres,
    [switch]$SkipGoAppservice,
    [switch]$SkipPython,
    [switch]$SkipFrontend,
    [switch]$UseMock,            # Slice 7: opt-in — use LLM mock on :8094 instead of real agent-service
    [switch]$SkipAgentService,   # Skip the real Python agent service (:8094) — main runtime
    [switch]$SkipControlUi,
    [switch]$SkipStorage,
    [switch]$SkipIngestion,
    [switch]$SkipLiteLLM,
    [switch]$DevTools,
    [switch]$WithVoice,
    [switch]$Tunnel,
    [switch]$FrontendOnly,
    [switch]$AgentOnly,
    [switch]$Inline,
    [int]$WaitSeconds = 0,
    [bool]$Watch = $true,
    [int]$MaxRestarts = 5
)

# -- Detach: re-launch in own PowerShell window unless -Inline was passed
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

$ErrorActionPreference = "Stop"

# -- Paths -------------------------------------------------------------------
$repoRoot    = Resolve-Path (Join-Path $PSScriptRoot "..")
$goDir       = Join-Path $repoRoot "go-appservice"
$pyDir       = Join-Path $repoRoot "python-backend"
$nextDir     = Join-Path $repoRoot "nextjs-chat"
$controlUiDir = Join-Path $repoRoot "control-ui"
$ingestionDir = Join-Path $repoRoot "python-backend/ingestion"
$mockDir     = Join-Path $repoRoot "python-backend/mock"
$logsRoot    = Join-Path $repoRoot "logs\dev-stack"
$seaweedExe  = Join-Path $repoRoot "tools\seaweedfs\weed.exe"
$seaweedDataDir = Join-Path $repoRoot "tools\seaweedfs\data"

# -- State -------------------------------------------------------------------
$script:services       = [ordered]@{}
$script:processes      = @()
$script:failedServices = @()

# -- Core Functions ----------------------------------------------------------

function Write-Phase([string]$Text) {
    Write-Host "`n--- $Text ---" -ForegroundColor Cyan
}

function Import-EnvFile([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match '^\s*([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim() -replace "^[`"']|[`"']$", ""
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "[env] Loaded $Path" -ForegroundColor DarkGray
}

function Start-LoggedProcess([string]$Name, [string]$FilePath, [string[]]$ArgumentList, [string]$WorkingDirectory) {
    if (-not (Test-Path $logsRoot)) { New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null }
    $spArgs = @{
        FilePath               = $FilePath
        WorkingDirectory       = $WorkingDirectory
        PassThru               = $true
        WindowStyle            = "Hidden"
        RedirectStandardOutput = (Join-Path $logsRoot "$Name.stdout.log")
        RedirectStandardError  = (Join-Path $logsRoot "$Name.stderr.log")
    }
    if ($ArgumentList -and $ArgumentList.Count -gt 0) { $spArgs.ArgumentList = $ArgumentList }
    return Start-Process @spArgs
}

function Stop-OwnedListenerOnPort([int]$Port, [string]$Name) {
    try {
        $portPids = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
        $ownPids = $script:processes | Where-Object { $null -ne $_ } | ForEach-Object { $_.Id }
        foreach ($pid in $portPids) {
            if ($null -eq $pid) { continue }
            if ($ownPids -and $pid -notin $ownPids) {
                $ext = Get-Process -Id $pid -ErrorAction SilentlyContinue
                Write-Host "[$Name] Port $Port held by external '$($ext.ProcessName)' (PID $pid) - skipping" -ForegroundColor Yellow
                continue
            }
            Write-Host "[$Name] Freeing port $Port (PID $pid)" -ForegroundColor DarkGray
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    } catch { }
}

function Test-PortInUse([int]$Port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    } catch { return $false }
}

function Wait-ForPort([int]$Port, [string]$Name, [int]$TimeoutSecs = 30) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSecs) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", $Port)
            $tcp.Close()
            return $true
        } catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

function Wait-ForHealth([string]$Url, [string]$Name, [int]$TimeoutSecs = 15) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSecs) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { return $true }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

function Register-Service {
    param(
        [string]$Name,
        [int]$Port,
        [scriptblock]$StartAction,
        [string]$HealthUrl = "",
        [int]$TimeoutSecs  = 30,
        [string]$Tier      = "app"
    )
    $script:services[$Name] = [ordered]@{
        Name         = $Name
        Port         = $Port
        StartAction  = $StartAction
        HealthUrl    = $HealthUrl
        TimeoutSecs  = $TimeoutSecs
        Tier         = $Tier
        Process      = $null
        RestartCount = 0
        CrashLoop    = $false
    }
}

function Start-Service([string]$Name) {
    $svc = $script:services[$Name]
    if ($null -eq $svc) { throw "Service not registered: $Name" }
    Stop-OwnedListenerOnPort -Port $svc.Port -Name $Name
    $proc = & $svc.StartAction
    $svc.Process = $proc
    $script:services[$Name] = $svc
    $script:processes += $proc
    return $proc
}

function Start-ServiceSafe([string]$Name) {
    $svc = $script:services[$Name]
    if ($null -eq $svc) { return }
    if (Test-PortInUse $svc.Port) {
        Write-Host "[$Name] Already running on :$($svc.Port) - skipping" -ForegroundColor Green
        return
    }
    try {
        Start-Service -Name $Name | Out-Null
        $portReady = Wait-ForPort -Port $svc.Port -Name $Name -TimeoutSecs $svc.TimeoutSecs
        if (-not $portReady) {
            Write-Host "[$Name] Port timeout after $($svc.TimeoutSecs)s" -ForegroundColor Yellow
            $script:failedServices += $Name
            return
        }
        if ($svc.HealthUrl) {
            $healthy = Wait-ForHealth -Url $svc.HealthUrl -Name $Name -TimeoutSecs 15
            if (-not $healthy) { Write-Host "[$Name] Health check failed (continuing)" -ForegroundColor Yellow }
        }
        Write-Host "[$Name] Ready on :$($svc.Port)" -ForegroundColor Green
    } catch {
        Write-Host "[$Name] Start failed: $($_.Exception.Message)" -ForegroundColor Yellow
        $script:failedServices += $Name
    }
}

# ==============================================================================
#  PHASE A -- PREPARE
# ==============================================================================
try {
    Write-Phase "Phase A: Prepare"

    # Load env files
    Import-EnvFile (Join-Path $goDir ".env.development")
    Import-EnvFile (Join-Path $pyDir ".env")

    # Shortcut flags
    if ($FrontendOnly) { $SkipHomeserver = $true; $SkipNats = $true; $SkipGoAppservice = $true; $SkipPython = $true }
    if ($AgentOnly)    { $SkipHomeserver = $true; $SkipFrontend = $true }

    # Go pre-build + Python deps + Next.js compile — all in parallel background jobs
    $prepJobs = @()

    if (-not $SkipGoAppservice) {
        Write-Host "[go] Pre-building appservice (background)..." -ForegroundColor Cyan
        $goBuildDir = $goDir
        $prepJobs += Start-Job -Name "go-prebuild" -ScriptBlock {
            param($dir)
            Set-Location $dir
            if (-not (Test-Path "tmp")) { New-Item -ItemType Directory -Path "tmp" -Force | Out-Null }
            & go build -tags goolm -o ".\tmp\appservice.exe" ./cmd/appservice 2>&1
        } -ArgumentList $goBuildDir
    }

    if (-not $SkipPython -and (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "[python] Syncing dependencies (background)..." -ForegroundColor Cyan
        $pyDepDir = $pyDir
        $prepJobs += Start-Job -Name "py-sync" -ScriptBlock {
            param($dir)
            Set-Location $dir
            & uv sync --inexact 2>&1
        } -ArgumentList $pyDepDir
    }

    # Wait for all prep jobs
    if ($prepJobs.Count -gt 0) {
        $prepJobs | Wait-Job | Out-Null
        foreach ($job in $prepJobs) {
            $output = Receive-Job -Job $job -ErrorAction SilentlyContinue
            if ($job.State -eq "Failed") {
                Write-Host "[$($job.Name)] Failed: $output" -ForegroundColor Yellow
            } else {
                Write-Host "[$($job.Name)] OK" -ForegroundColor Green
            }
            Remove-Job -Job $job -ErrorAction SilentlyContinue
        }
    }

    # ===========================================================================
    #  PHASE B -- REGISTER + START
    # ===========================================================================
    Write-Phase "Phase B: Register"

    # -- Tier: infra --

    if (-not $SkipHomeserver) {
        $tuwunelBin = Join-Path $repoRoot "tools\tuwunel"
        $tuwunelCfg = Join-Path $repoRoot "homeserver\tuwunel.toml"
        $zendriteBin = Join-Path $repoRoot "tools\zendrite.exe"
        $zendriteCfg = Join-Path $repoRoot "homeserver\dendrite.yaml"  # Config-Format kompatibel mit Zendrite

        if (Test-Path $tuwunelBin) {
            Register-Service -Name "tuwunel" -Port 8448 -Tier "infra" -TimeoutSecs 30 `
                -HealthUrl "http://127.0.0.1:8448/_matrix/client/versions" -StartAction {
                # Tuwunel = Linux binary, needs WSL
                Start-LoggedProcess -Name "tuwunel" -FilePath "wsl" `
                    -ArgumentList @("-d", "Ubuntu", "-u", "root", "bash", "-c",
                        "cd /mnt/d/matrix && ./tools/tuwunel --config ./homeserver/tuwunel.toml") `
                    -WorkingDirectory $repoRoot
            }
        } elseif (Test-Path $zendriteBin) {
            # Zendrite = Community-Fork von Dendrite, Go, Windows-native
            Register-Service -Name "zendrite" -Port 8448 -Tier "infra" -TimeoutSecs 20 -StartAction {
                New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "homeserver\data") | Out-Null
                Start-LoggedProcess -Name "zendrite" -FilePath $zendriteBin `
                    -ArgumentList @("--config", $zendriteCfg, "-really-enable-open-registration") `
                    -WorkingDirectory $repoRoot
            }
        } else {
            Write-Host "[homeserver] No binary found (tools/tuwunel or tools/zendrite.exe)" -ForegroundColor Red
            Write-Host "  Tuwunel: Linux binary in tools/tuwunel (via WSL1)" -ForegroundColor DarkGray
            Write-Host "  Zendrite: go build -o tools/zendrite.exe ./cmd/zendrite/ (from tools/zendrite-src)" -ForegroundColor DarkGray
        }
    }

    if (-not $SkipNats) {
        $natsExe = Join-Path $repoRoot "tools\nats-server.exe"
        if (Test-Path $natsExe) {
            Register-Service -Name "nats" -Port 4222 -Tier "infra" -TimeoutSecs 15 -StartAction {
                Start-LoggedProcess -Name "nats" -FilePath $natsExe `
                    -ArgumentList @("-js", "-m=8222") -WorkingDirectory $repoRoot
            }
        } else {
            Write-Host "[nats] nats-server.exe not found in tools/" -ForegroundColor Red
        }
    }

    # -- PostgreSQL + pgvector (exec-11 Memory Engine) --
    # Setup once: .\scripts\setup-postgres.ps1

    if (-not $SkipPostgres) {
        $pgCtl = Join-Path $repoRoot "tools\pgsql\bin\pg_ctl.exe"
        $pgDataDir = Join-Path $repoRoot "tools\pgsql-data"
        if (Test-Path $pgCtl) {
            Register-Service -Name "postgres" -Port 5433 -Tier "infra" -TimeoutSecs 20 -StartAction {
                Start-LoggedProcess -Name "postgres" -FilePath $pgCtl `
                    -ArgumentList @("start", "-D", $pgDataDir, "-l", (Join-Path $repoRoot "logs\dev-stack\postgres.log"), "-w") `
                    -WorkingDirectory $repoRoot
            }
        } else {
            Write-Host "[postgres] Not installed. Run: .\scripts\setup-postgres.ps1" -ForegroundColor Yellow
        }
    }

    # -- Tier: app --

    if (-not $SkipGoAppservice) {
        $goPrebuilt = Join-Path $goDir "tmp\appservice.exe"
        Register-Service -Name "go-appservice" -Port 8090 -Tier "app" -TimeoutSecs 60 `
            -HealthUrl "http://127.0.0.1:8090/health" -StartAction {
            if (Test-Path $goPrebuilt) {
                Start-LoggedProcess -Name "go-appservice" -FilePath $goPrebuilt `
                    -ArgumentList @() -WorkingDirectory $goDir
            } else {
                Start-LoggedProcess -Name "go-appservice" -FilePath "go" `
                    -ArgumentList @("run", "-tags", "goolm", "./cmd/appservice/...") -WorkingDirectory $goDir
            }
        }
    }

    # Resolve Python exe once for all Python services
    $pyVenv = Join-Path $pyDir ".venv\Scripts\python.exe"
    $pyExe = if (Test-Path $pyVenv) { $pyVenv } else { "python" }

    # -- Agent Service (Port 8094) — main Python runtime with /api/v1/control/* --
    # Slice 7: Real agent service is DEFAULT. Opt-in mock via -UseMock.
    # Go appservice ControlProxyHandler forwards /api/v1/control/* to :8094
    # which must be the REAL agent.app (mock-agent only has /api/v1/agent/chat).
    if ($UseMock) {
        Register-Service -Name "mock-agent" -Port 8094 -Tier "app" -TimeoutSecs 20 `
            -HealthUrl "http://127.0.0.1:8094/health" -StartAction {
            Start-LoggedProcess -Name "mock-agent" -FilePath "uv" `
                -ArgumentList @("run", "mock_agent.py") -WorkingDirectory $mockDir
        }
    } elseif (-not $SkipAgentService) {
        Register-Service -Name "agent-service" -Port 8094 -Tier "app" -TimeoutSecs 90 `
            -HealthUrl "http://127.0.0.1:8094/health" -StartAction {
            Start-LoggedProcess -Name "agent-service" -FilePath $pyExe `
                -ArgumentList @("-m", "uvicorn", "agent.app:app",
                    "--host", "127.0.0.1", "--port", "8094", "--reload") `
                -WorkingDirectory $pyDir
        }
    }

    # -- Python Bridge (Port 8097) — NATS consumer for Matrix events --
    if (-not $SkipPython) {
        Register-Service -Name "py-bridge" -Port 8097 -Tier "app" -TimeoutSecs 60 `
            -HealthUrl "http://127.0.0.1:8097/health" -StartAction {
            Start-LoggedProcess -Name "py-bridge" -FilePath $pyExe `
                -ArgumentList @("-m", "uvicorn", "bridge.app:app",
                    "--host", "127.0.0.1", "--port", "8097", "--reload") `
                -WorkingDirectory $pyDir
        }
    }

    if (-not $SkipFrontend) {
        Register-Service -Name "nextjs" -Port 3000 -Tier "app" -TimeoutSecs 120 -StartAction {
            Start-LoggedProcess -Name "nextjs" -FilePath "bun" `
                -ArgumentList @("run", "dev") -WorkingDirectory $nextDir
        }
    }

    # -- control-ui (Memory & Control UI, exec-15, Port 3001) --
    if (-not $SkipControlUi -and (Test-Path $controlUiDir)) {
        Register-Service -Name "control-ui" -Port 3001 -Tier "app" -TimeoutSecs 120 -StartAction {
            Start-LoggedProcess -Name "control-ui" -FilePath "bun" `
                -ArgumentList @("run", "dev") -WorkingDirectory $controlUiDir
        }
    }

    # -- SeaweedFS (S3-compatible object storage, exec-15 Slice 1, Port 8333/9333) --
    # On by default. Use -SkipStorage to disable.
    if (-not $SkipStorage -and (Test-Path $seaweedExe)) {
        if (-not (Test-Path $seaweedDataDir)) {
            New-Item -ItemType Directory -Path $seaweedDataDir -Force | Out-Null
        }
        Register-Service -Name "seaweedfs" -Port 8333 -Tier "infra" -TimeoutSecs 30 -StartAction {
            Start-LoggedProcess -Name "seaweedfs" -FilePath $seaweedExe `
                -ArgumentList @("server", "-dir=$seaweedDataDir", "-s3", "-s3.config=$($repoRoot)\tools\seaweedfs\s3.json") `
                -WorkingDirectory $repoRoot
        }
    } elseif (-not $SkipStorage -and -not (Test-Path $seaweedExe)) {
        Write-Host "[seaweedfs] weed.exe not found at $seaweedExe - download from https://github.com/seaweedfs/seaweedfs/releases" -ForegroundColor Yellow
    }

    # -- Ingestion Worker (exec-15 Slice 2, Venv 2 — Port 8098) --
    # Decoupled extraction pipeline. agent/control/ingestion.py is a thin
    # httpx proxy. See exec-15 §5.2 + D13-D17.
    if (-not $SkipIngestion -and (Test-Path $ingestionDir)) {
        Register-Service -Name "ingestion-worker" -Port 8098 -Tier "app" -TimeoutSecs 60 -StartAction {
            Start-LoggedProcess -Name "ingestion-worker" -FilePath "uv" `
                -ArgumentList @("run", "--project", $ingestionDir, "uvicorn", "ingestion.worker:app", "--host", "127.0.0.1", "--port", "8098") `
                -WorkingDirectory $ingestionDir
        }
    } elseif (-not $SkipIngestion -and -not (Test-Path $ingestionDir)) {
        Write-Host "[ingestion-worker] $ingestionDir not found - skipping" -ForegroundColor Yellow
    }

    # -- LiteLLM Gateway (exec-16, Venv 5 — Port 4000) --
    # Unified LLM proxy: model-name prefix routes to provider automatically.
    # All provider API keys read from python-backend/.env.
    $litellmDir = Join-Path $repoRoot "python-backend\litellm-gateway"
    if (-not $SkipLiteLLM -and (Test-Path $litellmDir)) {
        Register-Service -Name "litellm" -Port 4000 -Tier "app" -TimeoutSecs 60 `
            -HealthUrl "http://127.0.0.1:4000/health" -StartAction {
            Start-LoggedProcess -Name "litellm" -FilePath "uv" `
                -ArgumentList @("run", "--project", $litellmDir, "litellm", "--config", (Join-Path $litellmDir "config.yaml"), "--port", "4000") `
                -WorkingDirectory $litellmDir
        }
    } elseif (-not $SkipLiteLLM -and -not (Test-Path $litellmDir)) {
        Write-Host "[litellm] $litellmDir not found - run: cd python-backend/litellm-gateway && uv sync" -ForegroundColor Yellow
    }

    # -- Hindsight Memory Worker (exec-11, runs consolidation tasks) --
    if (-not $SkipPostgres) {
        $pgCtl2 = Join-Path $repoRoot "tools\pgsql\bin\pg_ctl.exe"
        if (Test-Path $pgCtl2) {
            Register-Service -Name "memory-worker" -Port 9999 -Tier "app" -TimeoutSecs 30 -StartAction {
                Start-LoggedProcess -Name "memory-worker" -FilePath $pyExe `
                    -ArgumentList @("-m", "hindsight_api.worker.main") -WorkingDirectory $pyDir
            }
        }
    }

    # -- Voice AI Worker (optional, -WithVoice Flag) --
    if ($WithVoice) {
        Register-Service -Name "voice-worker" -Port 0 -Tier "app" -TimeoutSecs 30 -StartAction {
            Start-LoggedProcess -Name "voice-worker" -FilePath "uv" `
                -ArgumentList @("run", "python", "-m", "voice.worker") -WorkingDirectory $pyDir
        }
    }

    # -- AI SDK DevTools (optional, -DevTools Flag) --
    if ($DevTools) {
        Register-Service -Name "ai-devtools" -Port 4983 -Tier "app" -TimeoutSecs 10 -StartAction {
            Start-LoggedProcess -Name "ai-devtools" -FilePath "npx" `
                -ArgumentList @("@ai-sdk/devtools") -WorkingDirectory $nextDir
        }
    }

    $registered = $script:services.Keys -join ", "
    Write-Host "Registered: $registered" -ForegroundColor DarkGray

    # -- Tunnel (optional) --
    if ($Tunnel) {
        $cloudflaredBin = Join-Path $repoRoot "tools\cloudflared.exe"
        $ngrokBin       = Join-Path $repoRoot "tools\ngrok.exe"
        if (Test-Path $cloudflaredBin) {
            Register-Service -Name "tunnel" -Port 0 -Tier "app" -TimeoutSecs 10 -StartAction {
                Start-LoggedProcess -Name "tunnel" -FilePath $cloudflaredBin `
                    -ArgumentList @("tunnel", "--url", "http://localhost:8448") -WorkingDirectory $repoRoot
            }
        } elseif (Test-Path $ngrokBin) {
            Register-Service -Name "tunnel" -Port 0 -Tier "app" -TimeoutSecs 10 -StartAction {
                Start-LoggedProcess -Name "tunnel" -FilePath $ngrokBin `
                    -ArgumentList @("http", "8448") -WorkingDirectory $repoRoot
            }
        }
    }

    # ==========================================================================
    #  PHASE C -- START
    # ==========================================================================
    Write-Phase "Phase C: Start"

    # Tier 1: Infrastructure
    $infraServices = $script:services.Values | Where-Object { $_.Tier -eq "infra" }
    if ($infraServices) {
        Write-Host "[tier-1] Starting infrastructure..." -ForegroundColor Cyan
        foreach ($svc in $infraServices) { Start-ServiceSafe -Name $svc.Name }
    }

    # Tier 2: Next.js first (longest compile), don't wait — launch rest in parallel
    $appServices = $script:services.Values | Where-Object { $_.Tier -eq "app" }
    if ($appServices) {
        Write-Host "[tier-2] Starting app services..." -ForegroundColor Cyan
        if ($script:services["nextjs"]) {
            # Start Next.js but don't block — it compiles in background
            $svc = $script:services["nextjs"]
            if (-not (Test-PortInUse $svc.Port)) {
                try {
                    Start-Service -Name "nextjs" | Out-Null
                    Write-Host "[nextjs] Compiling in background..." -ForegroundColor Green
                } catch {
                    Write-Host "[nextjs] Start failed: $($_.Exception.Message)" -ForegroundColor Yellow
                    $script:failedServices += "nextjs"
                }
            } else {
                Write-Host "[nextjs] Already running on :$($svc.Port) - skipping" -ForegroundColor Green
            }
        }
        # All other app services — start and wait for port
        $rest = $appServices | Where-Object { $_.Name -ne "nextjs" }
        foreach ($svc in $rest) { Start-ServiceSafe -Name $svc.Name }
        # Now wait for Next.js port
        if ($script:services["nextjs"] -and -not (Test-PortInUse 3000)) {
            $ready = Wait-ForPort -Port 3000 -Name "nextjs" -TimeoutSecs 120
            if ($ready) { Write-Host "[nextjs] Ready on :3000" -ForegroundColor Green }
            else { Write-Host "[nextjs] Port timeout after 120s" -ForegroundColor Yellow; $script:failedServices += "nextjs" }
        }
    }

    # -- Report ----------------------------------------------------------------
    if ($script:failedServices.Count -gt 0) {
        Write-Host "`n  WARNING: $($script:failedServices.Count) failed: $($script:failedServices -join ', ')" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  MATRIX STACK READY" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend" -ForegroundColor Cyan
    if ($script:services["nextjs"])        { Write-Host "    Next.js Chat:    http://localhost:3000/matrix" }
    if ($script:services["control-ui"])    { Write-Host "    Control UI:      http://localhost:3001" }
    Write-Host ""
    Write-Host "  Backend" -ForegroundColor Cyan
    if ($script:services["go-appservice"])    { Write-Host "    Go Appservice:       http://127.0.0.1:8090 (Matrix bridge + Control Proxy → :8094)" }
    if ($script:services["agent-service"])    { Write-Host "    Agent Service:       http://127.0.0.1:8094 (54 /api/v1/control/* routes)" }
    if ($script:services["mock-agent"])       { Write-Host "    LLM Mock Agent:      http://127.0.0.1:8094 (MOCK — only /chat + /health)" -ForegroundColor DarkYellow }
    if ($script:services["py-bridge"])        { Write-Host "    Python Bridge:       http://127.0.0.1:8097 (NATS consumer)" }
    if ($script:services["ingestion-worker"]) { Write-Host "    Ingestion Worker:    http://127.0.0.1:8098 (Venv 2, Slice 2)" }
    if ($script:services["litellm"])          { Write-Host "    LiteLLM Gateway:     http://127.0.0.1:4000 (Venv 5, exec-16)" }
    if ($script:services["memory-worker"])    { Write-Host "    Hindsight Worker:    (consolidation tasks)" }
    Write-Host ""
    Write-Host "  Infrastructure" -ForegroundColor Cyan
    if ($script:services["seaweedfs"]) {
        Write-Host "    SeaweedFS Master: http://127.0.0.1:9333"
        Write-Host "    SeaweedFS S3:     http://127.0.0.1:8333"
        Write-Host "    SeaweedFS Filer:  http://127.0.0.1:8888"
    }
    if ($script:services["tuwunel"] -or $script:services["zendrite"]) {
        Write-Host "    Homeserver:      http://127.0.0.1:8448"
    }
    if ($script:services["nats"])          { Write-Host "    NATS:            nats://127.0.0.1:4222 | Monitor: http://localhost:8222" }
    if ($script:services["postgres"])      { Write-Host "    PostgreSQL:      postgresql://postgres@localhost:5433/hindsight_dev (pgvector)" }
    if ($script:services["tunnel"])        { Write-Host "    Tunnel:          see logs/dev-stack/tunnel.stdout.log" -ForegroundColor DarkCyan }
    if ($script:services["voice-worker"])  { Write-Host "    Voice Worker:    LiveKit Agent (-WithVoice)" -ForegroundColor DarkYellow }
    if ($script:services["ai-devtools"])   { Write-Host "    AI DevTools:     http://127.0.0.1:4983  (-DevTools)" -ForegroundColor DarkYellow }
    Write-Host ""
    Write-Host "  Logs: logs\dev-stack\*.log" -ForegroundColor DarkGray
    Write-Host "============================================" -ForegroundColor Green

    # ==========================================================================
    #  PHASE D -- WATCH (restart crashed services)
    # ==========================================================================
    if ($Watch) {
        $label = if ($WaitSeconds -gt 0) { "for $WaitSeconds seconds" } else { "- Ctrl+C to stop" }
        Write-Host "`n[watch] Active $label" -ForegroundColor Cyan
        $startTs = Get-Date
        while ($true) {
            foreach ($entry in @($script:services.GetEnumerator())) {
                $svc = $entry.Value
                if ($null -eq $svc.Process -or $svc.CrashLoop) { continue }
                if (-not $svc.Process.HasExited) { continue }

                $svc.RestartCount++
                if ($svc.RestartCount -gt $MaxRestarts) {
                    if (-not $svc.CrashLoop) {
                        Write-Host "[$($svc.Name)] CRASH-LOOP - $MaxRestarts restarts exhausted" -ForegroundColor Red
                        $svc.CrashLoop = $true
                        $script:services[$svc.Name] = $svc
                    }
                    continue
                }

                $delay = [Math]::Min(30, [Math]::Pow(2, $svc.RestartCount))
                Write-Host "[$($svc.Name)] Exited (code $($svc.Process.ExitCode)). Restart $($svc.RestartCount)/$MaxRestarts in ${delay}s..." -ForegroundColor Yellow
                Start-Sleep -Seconds $delay

                try {
                    Start-Service -Name $svc.Name | Out-Null
                    $ready = Wait-ForPort -Port $svc.Port -Name $svc.Name -TimeoutSecs 30
                    if ($ready -and $svc.HealthUrl) { Wait-ForHealth -Url $svc.HealthUrl -Name $svc.Name | Out-Null }
                    if ($ready) { Write-Host "[$($svc.Name)] Restarted OK" -ForegroundColor Green }
                } catch {
                    Write-Host "[$($svc.Name)] Restart failed: $($_.Exception.Message)" -ForegroundColor Red
                }
            }

            if ($WaitSeconds -gt 0 -and ((Get-Date) - $startTs).TotalSeconds -ge $WaitSeconds) { break }
            Start-Sleep -Seconds 2
        }
    } elseif ($WaitSeconds -gt 0) {
        Start-Sleep -Seconds $WaitSeconds
    } else {
        Write-Host "`n[dev-stack] Press Enter to stop..." -ForegroundColor Cyan
        Read-Host
    }
}
finally {
    Write-Host "`n[shutdown] Stopping all processes..." -ForegroundColor Cyan
    $stopped = 0
    foreach ($proc in $script:processes) {
        if ($null -ne $proc -and -not $proc.HasExited) {
            try {
                Write-Host "  Stopping $($proc.ProcessName) (PID $($proc.Id))" -ForegroundColor DarkGray
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                $stopped++
            } catch { }
        }
    }
    if ($stopped -gt 0) { Write-Host "[shutdown] $stopped process(es) stopped." -ForegroundColor Green }
    else { Write-Host "[shutdown] Nothing to stop." -ForegroundColor DarkGray }
}
