# 013 Sandbox Security/HITL - Offene Punkte & Hinweise (2026-04-27)

## Laufzeitstatus (aktuell)
- OpenSandbox API Gateway läuft (`http://127.0.0.1:8080/health: OK`).
- `SandboxManager.execute_code(...)` ist noch nicht stabil im Live-Betrieb.
  - Symptome: `Sandbox health check timed out after 90.0s ... use_server_proxy=True`
  - Ursache im Versuch: Sandbox wird mit `POST /v1/sandboxes` angelegt, aber Health/Proxy erreicht die Sandbox nicht.
- Für neue Sandboxen wurde ein Endpoint zurückgeliefert, der auf nicht erreichbare Host-IP (`10.89.0.8`) verweist.
  - `GET /v1/sandboxes/<id>/endpoints/<port>` liefert `10.89.0.8:...`/`proxy/...`
  - Host versucht diese IP nicht erreichen zu können.
  - Mit der aktuellen Konfiguration muss diese Aussage nach erfolgreichem `sandbox create` erneut validiert werden; aktuell endet der Create vor der Endpoint-Rückgabe noch mit `broken pipe`.

## Offene Punkte / Risiken
- **Proxy/Netzwerk-Konfiguration (`use_server_proxy`)**
  - aktuell `OPENSANDBOX_USE_SERVER_PROXY` Standard `true`.
  - Ursache nach Stack-Reload war primär ein bereits genutzter Host-Port 8080 durch
    einen rootful Alt-Container; dieser wurde bereinigt.
  - Danach lief Gateway gesund, das Runtime-Create scheitert aber noch am
    Container-Archiv-Error (`broken pipe`), nicht an der Proxy-Route.
- **`broken pipe` beim OpenSandbox-Archive-Write (`/opt/opensandbox`)**
  - reproduzierbar bei `POST /v1/sandboxes` trotz korrekter Health/Config.
  - wahrscheinlich Ressourcenlimit im Host-Storage/Podman-Archivpfad; lokale `df`-Prüfung
    zeigte `97%` auf `/` (~4.0 GB frei).
  - Lösungspfad: kontrollierte Bereinigung (`podman container/image/volume prune`) + erneute
    Create-Validierung, danach ggf. `execd-cache`-Container-Temp prüfen.
- **`eip`/host erreichbar für Proxyrouten**
  - In `python-backend/agent/sandbox/sandbox-config.toml` wurden `server.eip` und
    `[docker].host_ip` ergänzt (`127.0.0.1`), passend zu den OpenSandbox-Doku.
  - Nach der Runtime-Erstellung (noch blockiert durch `broken pipe`) prüfen wir die
    zurückgelieferten Endpoint-Hosts auf Host-Reachability (`127.0.0.1` statt
    private Bridge-IP).
- **Port-Mapping/Proxy-Logs**
  - Für echte Ursachenanalyse sollten API-Logs der `opensandbox-api-gateway`-Routen (`.../health`, `.../diagnostics`) vollständig in die zentrale Log-Sammlung gehen.
  - Aktuell ist nur Podman-Container-Log sichtbar; für Trace-kopplung fehlen
    weiterhin serverseitige Ereigniskorrelationen.

## Was bereits umgesetzt ist
- `SandboxManager` schreibt jetzt Audit-/Diagnose-Felder (`sandbox_id`, `trace_id`, `diagnostics`) in das Sandbox-Ergebnis.
- `test_manager_file.py` für neue Felder im Resultat angehoben.
- Feature-Dokumentation 013 wurde entsprechend auf die neue Audit-Observability geschoben.
- `trace_id` in `agent/sandbox/manager.py` nutzt jetzt OTel-Span-Context, wenn vorhanden,
  statt immer nur `uuid4()` zu erzeugen. Dadurch können `X-Request-ID`-Header,
  Audit-Trail und Gateway-Diagnostik auf denselben Trace korrelieren.
- Neue CLI für OpenSandbox-Diagnose hinzugefügt:
  `python-backend/scripts/opensandbox_cli.py`.
  Unterstützt aktuell:
  `health`, `openapi`, `list`, `get`, `endpoint`, `diagnostics`, `create`, `delete`, `smoke`.
  Mit CLI lassen sich `POST /v1/sandboxes`, Proxy-Endpointauflösung,
  Diagnoseabfrage und sauberes Cleanup reproduzierbar testen – ohne Browser-Frontend.

## Nächste sinnvolle Schritte (ohne Browser-FE-Live-Verify)
1. Runtime-Create-Fehler (broken pipe) im Stack bereinigen:
   - Platz-/Storage-Bedingungen prüfen und ggf. `podman`-Images/Container-Prune
     kontrolliert anwenden, dann Stack neu starten.
2. Nach Bereinigung erneut `print(2+3)`-Live-Run prüfen.
3. Erfolgreiche Sandbox-Erstellung prüfen und Endpoints auf Host-Reachability
   (`127.0.0.1`) validieren.
4. Wenn stabil:
   - Open points in `closeout.md` aufheben
   - `live-verify.md` um den non-browser Backend-Path ergänzen (SDK-Run + Health/Diagnostic-Check).
