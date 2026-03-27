# dev-stack2.ps1 -- Matrix Dev Stack (v2)
# Usage: .\scripts\dev-stack2.ps1 [-SkipMock] [-Tunnel] [-SkipHomeserver] [-SkipNats] ...
# By default opens its own PowerShell window. Use -Inline to run in current terminal.
# Design: 3 phases (Prepare -> Register+Start -> Watch)

param(
    [switch]$SkipHomeserver,
    [switch]$SkipNats,
    [switch]$SkipGoAppservice,
    [switch]$SkipPython,
    [switch]$SkipFrontend,
    [switch]$SkipMock,
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
$pyDir       = Join-Path $repoRoot "python-agent-bridge"
$nextDir     = Join-Path $repoRoot "nextjs-chat"
$mockDir     = Join-Path $repoRoot "llm-mock"
$logsRoot    = Join-Path $repoRoot "logs\dev-stack"

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
        $dendriteBin = Join-Path $repoRoot "tools\dendrite.exe"
        $dendriteCfg = Join-Path $repoRoot "homeserver\dendrite.yaml"

        if (Test-Path $tuwunelBin) {
            Register-Service -Name "tuwunel" -Port 8448 -Tier "infra" -TimeoutSecs 30 `
                -HealthUrl "http://127.0.0.1:8448/_matrix/client/versions" -StartAction {
                # Tuwunel = Linux binary, needs WSL
                Start-LoggedProcess -Name "tuwunel" -FilePath "wsl" `
                    -ArgumentList @("-d", "Ubuntu", "-u", "root", "bash", "-c",
                        "cd /mnt/d/matrix && ./tools/tuwunel --config ./homeserver/tuwunel.toml") `
                    -WorkingDirectory $repoRoot
            }
        } elseif (Test-Path $dendriteBin) {
            Register-Service -Name "dendrite" -Port 8448 -Tier "infra" -TimeoutSecs 20 -StartAction {
                New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "homeserver\data") | Out-Null
                Start-LoggedProcess -Name "dendrite" -FilePath $dendriteBin `
                    -ArgumentList @("--config", $dendriteCfg, "-really-enable-open-registration") `
                    -WorkingDirectory $repoRoot
            }
        } else {
            Write-Host "[homeserver] No binary found (tools/tuwunel or tools/dendrite.exe)" -ForegroundColor Red
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

    if (-not $SkipMock) {
        Register-Service -Name "mock-agent" -Port 8094 -Tier "app" -TimeoutSecs 20 `
            -HealthUrl "http://127.0.0.1:8094/health" -StartAction {
            Start-LoggedProcess -Name "mock-agent" -FilePath "uv" `
                -ArgumentList @("run", "mock_agent.py") -WorkingDirectory $mockDir
        }
    }

    if (-not $SkipPython) {
        $pyVenv = Join-Path $pyDir ".venv\Scripts\python.exe"
        $pyExe = if (Test-Path $pyVenv) { $pyVenv } else { "python" }
        Register-Service -Name "py-bridge" -Port 8097 -Tier "app" -TimeoutSecs 60 `
            -HealthUrl "http://127.0.0.1:8097/health" -StartAction {
            Start-LoggedProcess -Name "py-bridge" -FilePath $pyExe `
                -ArgumentList @("-m", "uvicorn", "agent_bridge.app:app",
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
    if ($script:services["nextjs"])        { Write-Host "    Next.js Chat:  http://localhost:3000/matrix" }
    Write-Host ""
    Write-Host "  Backend" -ForegroundColor Cyan
    if ($script:services["go-appservice"]) { Write-Host "    Go Appservice:   http://127.0.0.1:8090" }
    if ($script:services["py-bridge"])     { Write-Host "    Python Bridge:   http://127.0.0.1:8097" }
    if ($script:services["mock-agent"])    { Write-Host "    LLM Mock Agent:  http://127.0.0.1:8094" }
    Write-Host ""
    Write-Host "  Infrastructure" -ForegroundColor Cyan
    if ($script:services["tuwunel"] -or $script:services["dendrite"]) {
        Write-Host "    Homeserver:      http://127.0.0.1:8448"
    }
    if ($script:services["nats"])          { Write-Host "    NATS:            nats://127.0.0.1:4222 | Monitor: http://localhost:8222" }
    if ($script:services["tunnel"])        { Write-Host "    Tunnel:          see logs/dev-stack/tunnel.stdout.log" -ForegroundColor DarkCyan }
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
