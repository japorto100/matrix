$HS = "http://localhost:8448"
$REG_TOKEN = "matrix-dev-token-2026"

function Reg-User($user, $pass, $device) {
    $body = ConvertTo-Json @{
        auth     = @{ type = "m.login.registration_token"; token = $REG_TOKEN }
        username = $user; password = $pass; device_id = $device
    }
    try {
        Invoke-RestMethod "$HS/_matrix/client/v3/register" -Method POST -ContentType "application/json" -Body $body | Out-Null
        Write-Host "  Registriert: @$user" -ForegroundColor Green
    } catch {
        if ($_ -match "M_USER_IN_USE") { Write-Host "  @$user existiert bereits" -ForegroundColor Yellow }
        else { Write-Host "  Reg-Fehler @${user}: $_" -ForegroundColor Red }
    }
    return Invoke-RestMethod "$HS/_matrix/client/v3/login" -Method POST -ContentType "application/json" -Body (ConvertTo-Json @{
        type = "m.login.password"; user = $user; password = $pass; device_id = $device
    })
}

# Tuwunel erreichbar?
try {
    $v = Invoke-RestMethod "$HS/_matrix/client/versions" -TimeoutSec 5
    Write-Host "Tuwunel: Matrix $($v.versions[-1])" -ForegroundColor Cyan
} catch { Write-Host "FEHLER: Tuwunel nicht erreichbar" -ForegroundColor Red; exit 1 }

# Alice
Write-Host "`nAlice..." -ForegroundColor Cyan
$alice = Reg-User "alice" "Alice1234!" "ALICE01"
$aliceToken  = $alice.access_token
$aliceDevice = $alice.device_id

# Bot
Write-Host "`nBot..." -ForegroundColor Cyan
$botPass = -join ((65..90)+(97..122)+(48..57) | Get-Random -Count 20 | ForEach-Object { [char]$_ })
try {
    $bot = Reg-User "trading-agent" $botPass "AGENT01"
    $botToken = $bot.access_token
    Write-Host "  Bot PW: $botPass" -ForegroundColor Gray
} catch {
    Write-Host "  Bot-Login fehlgeschlagen: $_" -ForegroundColor Red
    $botToken = $null
}

# Raum
Write-Host "`n#general Raum..." -ForegroundColor Cyan
try {
    $room = Invoke-RestMethod "$HS/_matrix/client/v3/createRoom" `
        -Method POST -ContentType "application/json" `
        -Headers @{ Authorization = "Bearer $aliceToken" } `
        -Body (ConvertTo-Json @{ name="General"; topic="Matrix Test"; preset="public_chat"; room_alias_name="general" })
    Write-Host "  Raum: $($room.room_id)" -ForegroundColor Green
} catch { Write-Host "  Raum: $($_ -replace '\n',' ')" -ForegroundColor Yellow }

# .env schreiben
$nextEnv = Get-Content "D:/matrix/nextjs-chat/.env.local" -Raw
$nextEnv = $nextEnv -replace "MATRIX_ACCESS_TOKEN=.*", "MATRIX_ACCESS_TOKEN=$aliceToken"
$nextEnv = $nextEnv -replace "MATRIX_DEVICE_ID=.*",    "MATRIX_DEVICE_ID=$aliceDevice"
Set-Content "D:/matrix/nextjs-chat/.env.local" $nextEnv
Write-Host "`nnextjs-chat/.env.local OK" -ForegroundColor Green

if ($botToken) {
    $pyEnv = Get-Content "D:/matrix/python-backend/.env" -Raw
    $pyEnv = $pyEnv -replace "MATRIX_BOT_ACCESS_TOKEN=.*", "MATRIX_BOT_ACCESS_TOKEN=$botToken"
    $pyEnv = $pyEnv -replace "MATRIX_BOT_PASSWORD=.*",     "MATRIX_BOT_PASSWORD=$botPass"
    Set-Content "D:/matrix/python-backend/.env" $pyEnv
    Write-Host "python-backend/.env OK" -ForegroundColor Green
}

Write-Host "`n=== SETUP FERTIG ===" -ForegroundColor Green
Write-Host "  @alice:matrix.local          PW: Alice1234!"
if ($botToken) { Write-Host "  @trading-agent:matrix.local  PW: $botPass" }
