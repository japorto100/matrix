#Requires -Version 5.1
<#
.SYNOPSIS
  Matrix Dev Stack -- startet alle Services lokal (kein Docker).

.DESCRIPTION
  Startet in dieser Reihenfolge:
    1. Tuwunel Homeserver      (Port 8448)
    2. NATS Server             (Port 4222)
    3. Go Appservice           (Port 8090)
    4. LLM Mock Agent          (Port 8094, nur mit -MockAgent)
    5. Python Agent Bridge     (Port 8097)
    6. Next.js Chat UI         (Port 3000)
    +  Tunnel                  (optional, mit -Tunnel)

.PARAMETER NoHomeserver
  Tuwunel nicht starten (z.B. wenn extern läuft).

.PARAMETER NoNATS
  NATS nicht starten (z.B. wenn extern läuft).

.PARAMETER SkipGoAppservice
  Go Appservice nicht starten.

.PARAMETER AgentOnly
  Nur Python Agent Bridge starten.

.PARAMETER FrontendOnly
  Nur Next.js starten.

.PARAMETER NoFrontend
  Next.js nicht starten (z.B. wenn bereits extern läuft).

.PARAMETER NoPython
  Python Agent Bridge nicht starten.

.PARAMETER Tunnel
  Startet einen Tunnel für Mobile-Tests (Reihenfolge: cloudflared -> ngrok -> bore).
  Tuwunel muss auf address = "0.0.0.0" konfiguriert sein.

.PARAMETER MockAgent
  Startet den LLM Mock Agent (Port 8094) statt des echten Agent-Service.
  Perfekt um den kompletten Stack zu testen ohne Anthropic/OpenAI Key.

.EXAMPLE
  .\scripts\devstack.ps1
  .\scripts\devstack.ps1 -MockAgent              # Stack + Mock statt echtem Agent
  .\scripts\devstack.ps1 -MockAgent -Tunnel      # Stack + Mock + Tunnel für Mobile
  .\scripts\devstack.ps1 -NoHomeserver -NoNATS
  .\scripts\devstack.ps1 -FrontendOnly
#>
param(
  [switch]$NoHomeserver,
  [switch]$NoNATS,
  [switch]$SkipGoAppservice,
  [switch]$AgentOnly,
  [switch]$FrontendOnly,
  [switch]$NoFrontend,
  [switch]$NoPython,
  [switch]$Tunnel,
  [switch]$MockAgent
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir

# Farben pro Service
function Write-Service($prefix, $color, $msg) {
  Write-Host "[$prefix] $msg" -ForegroundColor $color
}

function Write-HS($msg)     { Write-Service "homeserver " "Cyan"    $msg }
function Write-NATS($msg)   { Write-Service "nats       " "Magenta" $msg }
function Write-Go($msg)     { Write-Service "go-appsvc  " "Blue"    $msg }
function Write-Py($msg)     { Write-Service "py-bridge  " "Yellow"  $msg }
function Write-Next($msg)   { Write-Service "nextjs     " "Green"   $msg }
function Write-Main($msg)   { Write-Service "devstack   " "White"   $msg }

# Port-Übersicht
Write-Host ""
Write-Host "=== Matrix Dev Stack ===" -ForegroundColor White
Write-Host ""
Write-Host "  Port Map:" -ForegroundColor Gray
Write-Host "    8448  Tuwunel Homeserver  (_matrix/client/v3)" -ForegroundColor Gray
Write-Host "    4222  NATS               (matrix.message.*)" -ForegroundColor Gray
Write-Host "    8090  Go Appservice      (/_matrix/app/v1)" -ForegroundColor Gray
Write-Host "    8094  LLM Mock Agent     (/api/v1/agent/chat)  [-MockAgent]" -ForegroundColor Gray
Write-Host "    8097  Python Bot Bridge  (/health)" -ForegroundColor Gray
Write-Host "    3000  Next.js Chat UI    (/matrix)" -ForegroundColor Gray
Write-Host ""

$jobs = @()

# --- 1. Tuwunel Homeserver ---------------------------------------------------
if (-not $NoHomeserver -and -not $AgentOnly -and -not $FrontendOnly) {
  # Tuwunel (Linux via WSL) oder Dendrite (Windows native) -- automatische Erkennung
  $tuwunelBin  = Join-Path $RootDir "tools\tuwunel"
  $dendriteBin = Join-Path $RootDir "tools\dendrite.exe"
  $tuwunelCfg  = Join-Path $RootDir "homeserver\tuwunel.toml"
  $dendriteCfg = Join-Path $RootDir "homeserver\dendrite.yaml"

  # Tuwunel bevorzugen (Linux via WSL1), Dendrite als Windows-Fallback
  if (Test-Path $tuwunelBin) {
    Write-HS "Nutze Tuwunel (via WSL1) auf :8448..."
    $jobs += Start-Job -Name "homeserver" -ScriptBlock {
      param($rootDir)
      # -d Ubuntu -u root: OOBE-Bypass, WSL1-kompatibel
      # relative Pfade in tuwunel.toml funktionieren weil cd /mnt/d/matrix
      wsl -d Ubuntu -u root bash -c "cd /mnt/d/matrix && ./tools/tuwunel --config ./homeserver/tuwunel.toml" 2>&1
    } -ArgumentList $RootDir
    Start-Sleep -Seconds 7   # Tuwunel braucht ~5-7s bis HTTP bereit
    Write-HS "Tuwunel gestartet (Job-ID: $($jobs[-1].Id))"
  } elseif (Test-Path $dendriteBin) {
    Write-HS "Nutze Dendrite (Windows native) auf :8448..."
    # data/ Verzeichnis sicherstellen
    New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "homeserver\data") | Out-Null
    $jobs += Start-Job -Name "homeserver" -ScriptBlock {
      param($bin, $cfg)
      & $bin --config $cfg -really-enable-open-registration 2>&1
    } -ArgumentList $dendriteBin, $dendriteCfg
    Start-Sleep -Seconds 3
    Write-HS "Dendrite gestartet (Job-ID: $($jobs[-1].Id))"
  } else {
    Write-Host "[homeserver] WARNUNG: Kein Homeserver-Binary gefunden." -ForegroundColor Red
    Write-Host "  Dendrite:  tools\dendrite.exe  (Go build aus dendrite-src/)" -ForegroundColor Yellow
    Write-Host "  Tuwunel:   tools\tuwunel       (Linux, via WSL1)" -ForegroundColor Yellow
  }
}

# --- 2. NATS Server ----------------------------------------------------------
if (-not $NoNATS -and -not $AgentOnly -and -not $FrontendOnly) {
  # tools/nats-server.exe zuerst, dann PATH
  $natsLocal = Join-Path $RootDir "tools\nats-server.exe"
  if (Test-Path $natsLocal) { $natsBin = $natsLocal } else {
    $cmd = Get-Command "nats-server" -ErrorAction SilentlyContinue
    $natsBin = if ($cmd) { $cmd.Source } else { $null }
  }
  if (-not $natsBin) {
    Write-Host "[nats] WARNUNG: nats-server nicht gefunden -- NATS wird übersprungen." -ForegroundColor Red
    Write-Host "[nats]  Download: tools/nats-server.exe (siehe scripts/devstack.ps1)" -ForegroundColor Yellow
  } else {
    Write-NATS "Starte NATS auf :4222..."
    $jobs += Start-Job -Name "nats" -ScriptBlock {
      param($bin) & $bin 2>&1
    } -ArgumentList $natsBin
    Start-Sleep -Seconds 1
    Write-NATS "gestartet (Job-ID: $($jobs[-1].Id))"
  }
}

# --- 3. Go Appservice --------------------------------------------------------
if (-not $SkipGoAppservice -and -not $AgentOnly -and -not $FrontendOnly) {
  $goDir = Join-Path $RootDir "go-appservice"
  $goEnv = Join-Path $goDir ".env.development"

  if (-not (Test-Path $goEnv)) {
    Write-Go "WARNUNG: $goDir\.env.development nicht gefunden -- bitte .env.example kopieren und befüllen."
  } else {
    Write-Go "Starte Go Appservice auf :8090..."
    $jobs += Start-Job -Name "go-appservice" -ScriptBlock {
      param($dir)
      Set-Location $dir
      go run -tags goolm ./cmd/appservice/... 2>&1
    } -ArgumentList $goDir
    Start-Sleep -Seconds 2
    Write-Go "gestartet (Job-ID: $($jobs[-1].Id))"
  }
}

# --- 4. LLM Mock Agent (optional, -MockAgent Flag) ---------------------------
if ($MockAgent) {
  $mockDir = Join-Path $RootDir "llm-mock"
  Write-Host "[mock-agent] Starte LLM Mock Agent auf :8094..." -ForegroundColor DarkGreen
  $jobs += Start-Job -Name "mock-agent" -ScriptBlock {
    param($dir)
    Set-Location $dir
    uv run mock_agent.py 2>&1
  } -ArgumentList $mockDir
  Start-Sleep -Seconds 2
  Write-Host "[mock-agent] gestartet -- POST http://127.0.0.1:8094/api/v1/agent/chat" -ForegroundColor DarkGreen
}

# --- 5. Python Agent Bridge --------------------------------------------------
if (-not $FrontendOnly -and -not $NoPython) {
  $pyDir = Join-Path $RootDir "python-agent-bridge"
  $pyEnv = Join-Path $pyDir ".env"

  if (-not (Test-Path $pyEnv)) {
    Write-Py "WARNUNG: $pyDir\.env nicht gefunden -- bitte .env.example kopieren und befüllen."
  } else {
    Write-Py "Starte Python Bot Bridge auf :8097..."
    $jobs += Start-Job -Name "py-bridge" -ScriptBlock {
      param($dir)
      Set-Location $dir
      uv run uvicorn agent_bridge.app:app --host 127.0.0.1 --port 8097 --reload 2>&1
    } -ArgumentList $pyDir
    Start-Sleep -Seconds 2
    Write-Py "gestartet (Job-ID: $($jobs[-1].Id))"
  }
}

# --- 6. Next.js --------------------------------------------------------------
if (-not $AgentOnly -and -not $NoFrontend) {
  $nextDir = Join-Path $RootDir "nextjs-chat"
  $nextEnv = Join-Path $nextDir ".env.local"

  if (-not (Test-Path $nextEnv)) {
    Write-Next "WARNUNG: $nextDir\.env.local nicht gefunden -- bitte .env.local.example kopieren."
  }

  Write-Next "Starte Next.js auf :3000..."
  $jobs += Start-Job -Name "nextjs" -ScriptBlock {
    param($dir)
    Set-Location $dir
    bun run dev 2>&1
  } -ArgumentList $nextDir
  Write-Next "gestartet (Job-ID: $($jobs[-1].Id))"
}

if ($jobs.Count -eq 0) {
  Write-Main "Kein Service gestartet."
  exit 0
}

Write-Host ""
Write-Main "Alle Services gestartet. Ctrl+C zum Beenden."
Write-Host ""

# --- Log-Output aller Jobs ---------------------------------------------------
# --- 6. Tunnel (optional, -Tunnel Flag) --------------------------------------
if ($Tunnel) {
  $tunnelStarted = $false

  # Reihenfolge: cloudflared -> ngrok -> bore
  $cloudflaredBin = Join-Path $RootDir "tools\cloudflared.exe"
  $ngrokBin       = Join-Path $RootDir "tools\ngrok.exe"
  $boreBin        = Join-Path $RootDir "tools\bore.exe"

  if (Test-Path $cloudflaredBin) {
    Write-Host "[tunnel    ] Starte Cloudflare Tunnel (kein Account nötig)..." -ForegroundColor DarkCyan
    $jobs += Start-Job -Name "tunnel" -ScriptBlock {
      param($bin) & $bin tunnel --url http://localhost:8448 2>&1
    } -ArgumentList $cloudflaredBin
    Start-Sleep -Seconds 3
    Write-Host "[tunnel    ] cloudflared gestartet -- URL erscheint im Log oben" -ForegroundColor DarkCyan
    $tunnelStarted = $true

  } elseif (Test-Path $ngrokBin) {
    Write-Host "[tunnel    ] cloudflared nicht gefunden -- versuche ngrok..." -ForegroundColor DarkYellow
    Write-Host "[tunnel    ] HINWEIS: ngrok braucht authtoken (ngrok config add-authtoken TOKEN)" -ForegroundColor Yellow
    $jobs += Start-Job -Name "tunnel" -ScriptBlock {
      param($bin) & $bin http 8448 2>&1
    } -ArgumentList $ngrokBin
    Start-Sleep -Seconds 2
    Write-Host "[tunnel    ] ngrok gestartet -- URL: http://localhost:4040" -ForegroundColor DarkCyan
    $tunnelStarted = $true

  } elseif (Test-Path $boreBin) {
    Write-Host "[tunnel    ] ngrok nicht gefunden -- versuche bore (kein HTTPS!)..." -ForegroundColor DarkYellow
    $jobs += Start-Job -Name "tunnel" -ScriptBlock {
      param($bin) & $bin local 8448 --to bore.pub 2>&1
    } -ArgumentList $boreBin
    Start-Sleep -Seconds 2
    Write-Host "[tunnel    ] bore gestartet -- URL erscheint im Log (bore.pub:PORT)" -ForegroundColor DarkCyan
    Write-Host "[tunnel    ] WARNUNG: kein HTTPS -- Element X zeigt Sicherheitswarnung" -ForegroundColor Yellow
    $tunnelStarted = $true
  }

  if (-not $tunnelStarted) {
    Write-Host "[tunnel    ] WARNUNG: Kein Tunnel-Binary gefunden (cloudflared/ngrok/bore in tools/)" -ForegroundColor Red
  }

  Write-Host "[tunnel    ] tuwunel.toml muss address = '0.0.0.0' haben für Mobile-Zugriff" -ForegroundColor Gray
}

$colorMap = @{
  "homeserver"    = "Cyan"
  "nats"          = "Magenta"
  "go-appservice" = "Blue"
  "mock-agent"    = "DarkGreen"
  "py-bridge"     = "Yellow"
  "nextjs"        = "Green"
  "tunnel"        = "DarkCyan"
}

try {
  while ($true) {
    foreach ($job in $jobs) {
      $output = Receive-Job -Job $job -ErrorAction SilentlyContinue
      if ($output) {
        $color = if ($colorMap[$job.Name]) { $colorMap[$job.Name] } else { "White" }
        foreach ($line in $output) {
          Write-Host "[$($job.Name)] $line" -ForegroundColor $color
        }
      }
    }

    # Abgestürzte Jobs melden
    foreach ($job in $jobs) {
      if ($job.State -eq "Failed") {
        Write-Host "[$($job.Name)] FEHLER -- Job abgestürzt!" -ForegroundColor Red
      }
    }

    Start-Sleep -Milliseconds 500
  }
}
finally {
  Write-Host ""
  Write-Main "Beende alle Services..."
  foreach ($job in $jobs) {
    Stop-Job  -Job $job -ErrorAction SilentlyContinue
    Remove-Job -Job $job -ErrorAction SilentlyContinue
    Write-Host "  Gestoppt: $($job.Name)" -ForegroundColor Gray
  }
  Write-Main "Fertig."
}
