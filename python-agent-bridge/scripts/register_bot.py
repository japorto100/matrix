"""Bot-Account registrieren — einmalig ausführen.

Workflow:
1. Admin-Login (mit bestehendem Admin-Account)
2. Registration-Token erstellen (einmalig nutzbar)
3. Bot-Account mit diesem Token registrieren
4. Access Token ausgeben → in .env eintragen

Ausführen:
    uv run python scripts/register_bot.py
"""

from __future__ import annotations

import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv(".env", override=False)

HOMESERVER = os.getenv("MATRIX_HOMESERVER_URL", "http://localhost:8448")
BOT_USER_ID = os.getenv("MATRIX_BOT_USER_ID", "@trading-agent:matrix.local")
BOT_PASSWORD = os.getenv("MATRIX_BOT_PASSWORD", "")

# Bot-Localpart aus User-ID extrahieren
BOT_LOCALPART = BOT_USER_ID.split(":")[0].lstrip("@")


def prompt(text: str, default: str = "") -> str:
    result = input(f"{text} [{default}]: ").strip()
    return result or default


def main() -> None:
    print("\n━━━ Matrix Bot Registration ━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Homeserver: {HOMESERVER}")
    print(f"  Bot User:   {BOT_USER_ID}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    client = httpx.Client(base_url=HOMESERVER, timeout=30)

    # ── Schritt 1: Admin-Login ─────────────────────────────────────────────
    print("Schritt 1: Admin-Login")
    admin_user = prompt("Admin Username", "admin")
    admin_pw = prompt("Admin Passwort")

    resp = client.post(
        "/_matrix/client/v3/login",
        json={
            "type": "m.login.password",
            "user": admin_user,
            "password": admin_pw,
        },
    )

    if resp.status_code != 200:
        print(f"❌ Admin-Login fehlgeschlagen: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)

    admin_token = resp.json()["access_token"]
    print("✅ Admin-Login erfolgreich\n")

    # ── Schritt 2: Registration-Token erstellen ────────────────────────────
    print("Schritt 2: Registration-Token erstellen")

    resp = client.post(
        "/_synapse/admin/v1/registration_tokens/new",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"uses_allowed": 1},  # Einmalig nutzbar
    )

    if resp.status_code not in (200, 201):
        # Tuwunel-spezifischer Endpunkt (falls Synapse-Compat-Endpoint fehlt)
        print(f"⚠️  Synapse-Admin-Endpoint fehlgeschlagen ({resp.status_code})")
        print("   Versuche direkten Tuwunel-Endpunkt...")

        # Alternativ: offenes Registration (falls Server es erlaubt)
        reg_token = prompt(
            "Registration-Token manuell eingeben (oder leer für m.login.dummy)"
        )
        use_dummy = not reg_token
    else:
        reg_token = resp.json()["token"]
        use_dummy = False
        print(f"✅ Registration-Token erstellt: {reg_token}\n")

    # ── Schritt 3: Bot-Account registrieren ───────────────────────────────
    print(f"Schritt 3: Bot-Account '{BOT_LOCALPART}' registrieren")

    if not BOT_PASSWORD:
        print("❌ MATRIX_BOT_PASSWORD nicht gesetzt in .env")
        sys.exit(1)

    if use_dummy:
        auth = {"type": "m.login.dummy"}
    else:
        auth = {
            "type": "m.login.registration_token",
            "token": reg_token,
        }

    resp = client.post(
        "/_matrix/client/v3/register",
        json={
            "username": BOT_LOCALPART,
            "password": BOT_PASSWORD,
            "auth": auth,
        },
    )

    if resp.status_code == 200:
        data = resp.json()
        access_token = data.get("access_token", "")
        print("\n✅ Bot-Account erstellt!")
        print("\n━━━ In .env eintragen ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"MATRIX_BOT_ACCESS_TOKEN={access_token}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    elif resp.status_code == 400 and "M_USER_IN_USE" in resp.text:
        print(f"\n⚠️  User '{BOT_LOCALPART}' existiert bereits.")
        print("   Bot kann sich trotzdem einloggen — Access Token via Login holen:")

        resp2 = client.post(
            "/_matrix/client/v3/login",
            json={
                "type": "m.login.password",
                "user": BOT_LOCALPART,
                "password": BOT_PASSWORD,
            },
        )
        if resp2.status_code == 200:
            access_token = resp2.json()["access_token"]
            print("\n━━━ In .env eintragen ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"MATRIX_BOT_ACCESS_TOKEN={access_token}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        else:
            print(f"❌ Login fehlgeschlagen: {resp2.text[:200]}")
    else:
        print(f"❌ Registrierung fehlgeschlagen: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
