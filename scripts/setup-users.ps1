#Requires -Version 5.1
<#
.SYNOPSIS
  Erstellt Test-User und Bot-Account auf dem lokalen Homeserver.
  Homeserver (Tuwunel oder Dendrite) muss laufen bevor dieses Script ausgeführt wird.

.DESCRIPTION
  Erstellt:
    - @alice:matrix.local        (Test-User für Browser/Element X)
    - @trading-agent:matrix.local (Bot-Account für Python Bridge)
  Schreibt Access-Tokens direkt in die jeweiligen .env Dateien.

  Tuwunel:  registration_token = "matrix-dev-token-2026" (aus tuwunel.toml)
  Dendrite: registration_requires_token = true (Token via Admin-API oder manuell)
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
$HS        = "http://localhost:8448"

# Tuwunel Registration-Token (aus homeserver/tuwunel.toml)
$REG_TOKEN = "matrix-dev-token-2026"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Err($msg)  { Write-Host "    FEHLER: $msg" -ForegroundColor Red }

# ─── Homeserver erreichbar? ──────────────────────────────────────────────────
Write-Step "Prüfe Homeserver ($HS)..."
try {
  $versions = Invoke-RestMethod "$HS/_matrix/client/versions" -TimeoutSec 5
  Write-OK "Homeserver antwortet (Matrix $($versions.versions[-1]))"
} catch {
  Write-Err "Homeserver nicht erreichbar. Starte zuerst:"
  Write-Host "    Tuwunel:  wsl -d Ubuntu -u root bash -c 'cd /mnt/d/matrix && ./tools/tuwunel --config ./homeserver/tuwunel.toml'" -ForegroundColor Yellow
  Write-Host "    Dendrite: D:\matrix\tools\dendrite.exe --config D:\matrix\homeserver\dendrite.yaml -really-enable-open-registration" -ForegroundColor Yellow
  exit 1
}

# ─── Homeserver-Typ erkennen ─────────────────────────────────────────────────
$serverSoftware = "unknown"
try {
  $serverHeader = Invoke-WebRequest "$HS/_matrix/client/versions" -UseBasicParsing
  $serverHeader = $serverHeader.Headers["Server"]
  if ($serverHeader -match "Dendrite") { $serverSoftware = "dendrite" }
  elseif ($serverHeader -match "[Tt]uwunel|[Cc]onduit") { $serverSoftware = "tuwunel" }
} catch {}
Write-OK "Homeserver-Software: $serverSoftware"

# Bei Dendrite: Registration-Token via Admin-API erstellen
if ($serverSoftware -eq "dendrite") {
  Write-Step "Dendrite: Admin-Login für Registration-Token..."
  $adminUser = Read-Host "  Admin-Username (default: admin)"
  if (-not $adminUser) { $adminUser = "admin" }
  $adminPassPlain = Read-Host "  Admin-Passwort"
  try {
    $loginResp = Invoke-RestMethod "$HS/_matrix/client/v3/login" -Method POST -ContentType "application/json" -Body (@{
      type = "m.login.password"; user = $adminUser; password = $adminPassPlain
    } | ConvertTo-Json)
    $adminToken = $loginResp.access_token
    Write-OK "Admin eingeloggt"
    # Dendrite Registration Token via Admin API
    $REG_TOKEN = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    Invoke-RestMethod "$HS/_synapse/admin/v1/registration_tokens/new" `
      -Method POST -ContentType "application/json" `
      -Headers @{ Authorization = "Bearer $adminToken" } `
      -Body (@{ token = $REG_TOKEN; uses_allowed = 5 } | ConvertTo-Json) | Out-Null
    Write-OK "Token erstellt: $REG_TOKEN"
  } catch {
    Write-Host "    Admin-API nicht verfügbar — Token manuell eingeben:" -ForegroundColor Yellow
    $REG_TOKEN = Read-Host "  Registration-Token"
  }
} else {
  Write-OK "Tuwunel: Nutze Token aus tuwunel.toml: $REG_TOKEN"
}

# ─── Hilfsfunktion: User registrieren + einloggen ────────────────────────────
function Register-MatrixUser($localpart, $password, $displayName) {
  $userId = "@${localpart}:matrix.local"
  $deviceId = ($localpart.ToUpper().Substring(0, [Math]::Min(6, $localpart.Length)) + "01")

  # Registrieren
  try {
    $body = @{
      auth     = @{ type = "m.login.registration_token"; token = $REG_TOKEN }
      username = $localpart
      password = $password
      device_id = $deviceId
      initial_device_display_name = $displayName
    } | ConvertTo-Json
    Invoke-RestMethod "$HS/_matrix/client/v3/register" -Method POST -ContentType "application/json" -Body $body | Out-Null
    Write-OK "$userId registriert"
  } catch {
    $errMsg = $_.ToString()
    if ($errMsg -match "M_USER_IN_USE") {
      Write-Host "    $userId existiert bereits — logge ein." -ForegroundColor Yellow
    } else {
      Write-Err "Registrierung fehlgeschlagen: $errMsg"
      return $null
    }
  }

  # Login
  try {
    return Invoke-RestMethod "$HS/_matrix/client/v3/login" -Method POST -ContentType "application/json" -Body (@{
      type      = "m.login.password"
      user      = $localpart
      password  = $password
      device_id = $deviceId
      initial_device_display_name = $displayName
    } | ConvertTo-Json)
  } catch {
    Write-Err "Login fehlgeschlagen: $_"
    return $null
  }
}

# ─── Alice (Test-User) ────────────────────────────────────────────────────────
Write-Step "Erstelle @alice:matrix.local..."
$alicePass  = "Alice1234!"
$aliceLogin = Register-MatrixUser "alice" $alicePass "Alice (Test)"

if ($aliceLogin) {
  $aliceToken  = $aliceLogin.access_token
  $aliceDevice = $aliceLogin.device_id
  Write-OK "Token: $aliceToken"

  $envPath    = Join-Path $RootDir "nextjs-chat\.env.local"
  $envContent = Get-Content $envPath -Raw
  $envContent = $envContent -replace "MATRIX_ACCESS_TOKEN=.*",  "MATRIX_ACCESS_TOKEN=$aliceToken"
  $envContent = $envContent -replace "MATRIX_DEVICE_ID=.*",     "MATRIX_DEVICE_ID=$aliceDevice"
  $envContent = $envContent -replace "MATRIX_USER_ID=.*",       "MATRIX_USER_ID=@alice:matrix.local"
  Set-Content $envPath $envContent
  Write-OK "nextjs-chat/.env.local aktualisiert"
}

# ─── Trading Agent (Bot) ──────────────────────────────────────────────────────
Write-Step "Erstelle @trading-agent:matrix.local..."
$botPass  = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 20 | ForEach-Object { [char]$_ })
$botLogin = Register-MatrixUser "trading-agent" $botPass "Trading Agent"

if ($botLogin) {
  $botToken = $botLogin.access_token
  Write-OK "Bot Token: $botToken"
  Write-OK "Bot Passwort (speichern!): $botPass"

  $pyEnvPath = Join-Path $RootDir "python-backend\.env"
  $pyContent = Get-Content $pyEnvPath -Raw
  $pyContent = $pyContent -replace "MATRIX_BOT_ACCESS_TOKEN=.*", "MATRIX_BOT_ACCESS_TOKEN=$botToken"
  $pyContent = $pyContent -replace "MATRIX_BOT_PASSWORD=.*",     "MATRIX_BOT_PASSWORD=$botPass"
  Set-Content $pyEnvPath $pyContent
  Write-OK "python-backend/.env aktualisiert"
}

# ─── Test-Raum erstellen ──────────────────────────────────────────────────────
Write-Step "Erstelle Test-Raum #general:matrix.local..."
if ($aliceLogin) {
  try {
    $roomResp = Invoke-RestMethod "$HS/_matrix/client/v3/createRoom" `
      -Method POST -ContentType "application/json" `
      -Headers @{ Authorization = "Bearer $aliceToken" } `
      -Body (@{ name = "General"; topic = "Matrix Test"; preset = "public_chat"; room_alias_name = "general" } | ConvertTo-Json)
    Write-OK "Raum: $($roomResp.room_id)"
  } catch {
    Write-Host "    Raum existiert ggf. bereits: $_" -ForegroundColor Yellow
  }
}

# ─── Zusammenfassung ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Setup abgeschlossen ===" -ForegroundColor Green
Write-Host "  @alice:matrix.local          PW: $alicePass" -ForegroundColor White
if ($botLogin) {
  Write-Host "  @trading-agent:matrix.local  PW: $botPass" -ForegroundColor White
}
Write-Host "  .env Dateien automatisch aktualisiert." -ForegroundColor Gray
Write-Host "  Naechster Schritt: .\scripts\devstack.ps1" -ForegroundColor Cyan
