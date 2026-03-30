$HS = "http://localhost:8448"
$REG_TOKEN = "matrix-dev-token-2026"

# Tuwunel im Hintergrund starten
Write-Host "Starte Tuwunel..." -ForegroundColor Cyan
$tuwunel = Start-Process -FilePath "wsl.exe" `
    -ArgumentList "-d", "Ubuntu", "-u", "root", "bash", "-c", "cd /mnt/d/matrix && ./tools/tuwunel --config ./homeserver/tuwunel.toml" `
    -PassThru -WindowStyle Hidden

# Warten bis API antwortet
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep 2
    try {
        $v = Invoke-RestMethod "$HS/_matrix/client/versions" -TimeoutSec 2
        Write-Host "  Tuwunel OK: Matrix $($v.versions[-1])" -ForegroundColor Green
        $ready = $true; break
    } catch {}
    Write-Host "  Warte... ($($i*2+2)s)"
}
if (-not $ready) { Write-Host "FEHLER: Tuwunel nicht gestartet" -ForegroundColor Red; exit 1 }

function Reg-User($user, $pass, $device) {
    try {
        Invoke-RestMethod "$HS/_matrix/client/v3/register" -Method POST -ContentType "application/json" `
            -Body (ConvertTo-Json @{
                auth     = @{ type = "m.login.registration_token"; token = $REG_TOKEN }
                username = $user; password = $pass; device_id = $device
            }) | Out-Null
        Write-Host "  Registriert: @$user" -ForegroundColor Green
    } catch {
        if ($_ -match "M_USER_IN_USE") { Write-Host "  @$user existiert bereits" -ForegroundColor Yellow }
        else { Write-Host "  Reg-Fehler @${user}: $_" -ForegroundColor Red }
    }
    return Invoke-RestMethod "$HS/_matrix/client/v3/login" -Method POST -ContentType "application/json" `
        -Body (ConvertTo-Json @{ type = "m.login.password"; user = $user; password = $pass; device_id = $device })
}

Write-Host "`nAlice..." -ForegroundColor Cyan
$alice       = Reg-User "alice" "Alice1234!" "ALICE01"
$aliceToken  = $alice.access_token
$aliceDevice = $alice.device_id

Write-Host "`nBot..." -ForegroundColor Cyan
$botPass = -join ((65..90)+(97..122)+(48..57) | Get-Random -Count 20 | ForEach-Object { [char]$_ })
$bot     = Reg-User "trading-agent" $botPass "AGENT01"
$botToken = $bot.access_token
Write-Host "  Bot PW: $botPass" -ForegroundColor Gray

Write-Host "`n#general Raum..." -ForegroundColor Cyan
try {
    $room = Invoke-RestMethod "$HS/_matrix/client/v3/createRoom" `
        -Method POST -ContentType "application/json" `
        -Headers @{ Authorization = "Bearer $aliceToken" } `
        -Body (ConvertTo-Json @{ name="General"; topic="Matrix Test"; preset="public_chat"; room_alias_name="general" })
    Write-Host "  $($room.room_id)" -ForegroundColor Green
} catch { Write-Host "  $($_ -replace '\n',' ')" -ForegroundColor Yellow }

# .env schreiben
$nextEnv = (Get-Content "D:/matrix/nextjs-chat/.env.local" -Raw) `
    -replace "MATRIX_ACCESS_TOKEN=.*", "MATRIX_ACCESS_TOKEN=$aliceToken" `
    -replace "MATRIX_DEVICE_ID=.*",    "MATRIX_DEVICE_ID=$aliceDevice"
Set-Content "D:/matrix/nextjs-chat/.env.local" $nextEnv
Write-Host "nextjs-chat/.env.local OK" -ForegroundColor Green

$pyEnv = (Get-Content "D:/matrix/python-backend/.env" -Raw) `
    -replace "MATRIX_BOT_ACCESS_TOKEN=.*", "MATRIX_BOT_ACCESS_TOKEN=$botToken" `
    -replace "MATRIX_BOT_PASSWORD=.*",     "MATRIX_BOT_PASSWORD=$botPass"
Set-Content "D:/matrix/python-backend/.env" $pyEnv
Write-Host "python-backend/.env OK" -ForegroundColor Green

Write-Host "`n=== FERTIG ===" -ForegroundColor Green
Write-Host "  @alice:matrix.local          PW: Alice1234!"
Write-Host "  @trading-agent:matrix.local  PW: $botPass"

Stop-Process -Id $tuwunel.Id -ErrorAction SilentlyContinue
