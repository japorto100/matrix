# exec-notifications: Real-Time Notification & Alert System

**Datum:** 13.04.2026
**Status:** Draft → **Ready-to-implement 2026-04-24**. No open design decisions; 5-phase implementation plan (Go Alert Hub → Python Producer → LiteLLM Webhook → Frontend Bell → Preferences) is commit-ready. Libraries selected (nikoksr/notify v2, r3labs/sse v2 — both MIT), NATS subjects defined (§NATS), DB schema finalized (§DB Schema, Go auto-migrate in `storage.*`), 9 verify-gates enumerated. Implementation is a multi-day track separate from this spec.
**Abhaengig von:** exec-19 (NATS Bridge, LiteLLM Spend), exec-16 (Virtual Keys)
**Kontext:** Trading/Research Platform mit Matrix Chat + Agent System. Alerts sind Trading-relevant (Budget, Ingestion, Agent-Tasks, Markt-Events, Portfolio). Mobile Delivery via Element X (Matrix Chat Nachrichten).

---

## Referenzen

### Libraries (neu hinzuzufuegen)

| Package | Lizenz | Stars | Beschreibung |
|---|---|---|---|
| [nikoksr/notify v2](https://github.com/nikoksr/notify) | MIT | 12k+ | Multi-Channel Delivery (Matrix, Slack, Email, Telegram, 30+ Services) |
| [r3labs/sse v2](https://github.com/r3labs/sse) | MIT | 2k+ | Go SSE Server fuer Webapp Real-Time Delivery |

### Bereits vorhanden (kein Install)

| Package | Wo | Rolle |
|---|---|---|
| `nats.go` | go-appservice | Event Bus (alle Services → Go Alert Hub) |
| `nats-py` | python-backend | Alert Producer (Agent, Ingestion, Compute) |
| `mautrix-go` | go-appservice | Matrix Room Messages (Appservice kann in Rooms schreiben) |
| `pgx/v5` | go-appservice | Notification Persistenz |
| `sonner` | control-ui | Toast Notifications |
| shadcn alert/collapsible | control-ui | Banner + Bell UI Components |
| `matrix-js-sdk` PushProcessor | nextjs-chat | Matrix Push Rules + Unread Counts |
| `useNotifications` Hook | nextjs-chat | Mentions, Thread-Replies, Invites |

### Weitere Quellen

- [Go + NATS Notification Example](https://github.com/BaseMax/real-time-notifications-nats-go)
- [Go + NATS + WS Notification Microservice](https://github.com/nccapo/go-notification)
- [Event-Driven Systems with Go and NATS (2026)](https://dasroot.net/posts/2026/02/building-event-driven-systems-go-nats/)
- [FastAPI SSE Notifications](https://medium.com/@inandelibas/real-time-notifications-in-python-using-sse-with-fastapi-1c8c54746eb7)
- [LiteLLM Alerting/Webhooks](https://docs.litellm.ai/docs/proxy/alerting)
- [Matrix Push Rules Explained](https://patrick.cloke.us/posts/2023/05/08/matrix-push-rules-notifications/)
- [Tuwunel Push Suppression](https://github.com/matrix-construct/tuwunel/pull/150)
- [Element-X Android Notifications](https://github.com/element-hq/element-x-android/blob/develop/docs/notifications.md)
- [shadcn Notification Button Pattern](https://www.shadcn.io/patterns/button-group-badges-1)
- Lucide: [bell-dot](https://www.shadcn.io/icon/lucide-bell-dot) Icon

### Nicht verwendet (mit Begruendung)

| Tool | Warum nicht |
|---|---|
| Novu | Node.js Stack, eigener Server-Prozess, Overkill |
| Centrifugo | Eigener Server-Prozess, wir haben NATS + r3labs/sse |
| Gorush | Firebase/APNs Push — nicht noetig weil Matrix Mobile Push |
| Gotify | Eigener Server + eigene Android App — redundant mit Element X |
| MagicBell | SaaS, nicht self-hosted |

---

## Warum

Aktuell hat Matrix kein zentrales Notification System:
- Budget-Alerts → kein Trigger, kein Delivery
- Agent Task fertig → User muss manuell pruefen
- Ingestion abgeschlossen → keine Benachrichtigung
- Service Health → nur in Logs sichtbar
- Exchange Events (Hauptprojekt GCT) → kein Kanal
- Kein In-App Notification Center (Bell Icon, Unread Count)

---

## Architektur

```
Event Sources                Go Appservice (Alert Hub)              Delivery
────────────                ─────────────────────────              ────────
Python Agent ──┐                                              ┌──→ SSE → Webapp (Toast/Bell)
LiteLLM ───────┤            internal/alerts/                   │   (r3labs/sse)
Ingestion ─────┤── NATS ──→   router.go                       │
Exchanges (GCT)┤              - subscribe NATS alerts.*   ────┼──→ Matrix Room Message
Health Checks ─┘              - persist to PG                  │   (nikoksr/notify Matrix)
                              - fan-out per channel            │
                              - serve SSE stream               └──→ (spaeter: Email/Slack)
                              - serve history API                   (nikoksr/notify SMTP/Slack)
```

### Go Appservice = Alert Hub

Warum Go:
- Zentrales Gateway — alle HTTP Requests fliessen durch
- NATS Bridge existiert bereits (`natsbridge/bridge.go`)
- Matrix Appservice (mautrix-go) kann in Rooms schreiben
- Gleiche Architektur wie Hauptprojekt (GCT) → portierbar
- `nikoksr/notify` + `r3labs/sse` passen direkt rein

### Python = Alert Producer

Python entscheidet nicht wohin, nur was passiert ist:
- `agent/alerts.py` — `publish_alert(subject, payload)` via `nats-py`
- Aufrufe in: runner.py, worker.py, scheduler

---

## NATS Subjects

| Subject | Producer | Payload |
|---|---|---|
| `alerts.budget.threshold` | Go (LiteLLM Webhook) | `{user_id, spend, max_budget, threshold_pct, provider}` |
| `alerts.budget.exceeded` | Go (LiteLLM Webhook) | `{user_id, spend, max_budget, provider}` |
| `alerts.agent.completed` | Python | `{user_id, thread_id, summary, duration_ms, model, tokens}` |
| `alerts.agent.error` | Python | `{user_id, thread_id, error, model}` |
| `alerts.ingestion.done` | Python | `{user_id, file_id, filename, pipeline, duration_ms}` |
| `alerts.ingestion.failed` | Python | `{user_id, file_id, filename, error}` |
| `alerts.system.health` | Go | `{service, status, message}` |
| `alerts.exchange.*` | Go (GCT) | `{user_id, exchange, event_type, data}` |

---

## Delivery Channels

| Channel | Wann | Library | Wie |
|---|---|---|---|
| **Webapp Toast** | Immer (control-ui, agent-chat) | `r3labs/sse` | SSE → EventSource → `toast()` |
| **Bell Icon Badge** | Immer | `r3labs/sse` | SSE → unread count → Badge |
| **Notification Sheet** | Klick auf Bell | pgx query | Letzte N aus DB |
| **Matrix Room** | Immer (fuer Mobile via Element X) | `nikoksr/notify` Matrix Service | Message in `#alerts` Room → Element X Push |
| **Email** | Konfigurierbar (kritisch) | `nikoksr/notify` SMTP | Spaeter |
| **Slack/Teams** | Konfigurierbar | `nikoksr/notify` Slack/Teams Service | Spaeter |

### Mobile Push (via Matrix)

Kein eigener Push-Server noetig. Flow:
```
Go Appservice → nikoksr/notify → Matrix Message in #alerts Room
  → Tuwunel Homeserver → Element X App auf Phone
  → Normale Chat-Notification (Badge, Sound, Vibration)
```

Element X hat eigene Push-Infra (UnifiedPush, FCM, oder Polling). Wir muessen nur eine Matrix-Nachricht schreiben.

---

## DB Schema

```sql
CREATE TABLE storage.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,           -- budget_threshold, agent_completed, ingestion_done, ...
    severity TEXT NOT NULL DEFAULT 'info',  -- info, warning, critical
    title TEXT NOT NULL,
    body TEXT,
    metadata JSONB DEFAULT '{}',
    channels_delivered TEXT[] DEFAULT '{}',  -- ['sse', 'matrix', 'email']
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON storage.notifications (user_id, created_at DESC);
CREATE INDEX idx_notifications_unread ON storage.notifications (user_id) WHERE read_at IS NULL;
```

---

## API Endpoints (Go Appservice)

| Method | Path | Beschreibung |
|---|---|---|
| `GET` | `/api/v1/alerts/stream` | SSE Stream — Real-Time Alerts fuer verbundenen User |
| `GET` | `/api/v1/alerts?limit=50` | History — letzte N Notifications aus DB |
| `GET` | `/api/v1/alerts/unread-count` | Unread Count fuer Bell Badge |
| `POST` | `/api/v1/alerts/{id}/read` | Mark als gelesen |
| `POST` | `/api/v1/alerts/read-all` | Alle als gelesen markieren |
| `POST` | `/api/v1/alerts/webhook` | LiteLLM Budget Webhook Empfaenger |

---

## Implementation Plan

### Phase 1: Go Alert Hub (Core)

| Datei | Aenderung |
|---|---|
| `go.mod` | `go get github.com/nikoksr/notify/v2 github.com/r3labs/sse/v2` |
| `internal/alerts/router.go` | NEU: NATS subscribe, persist, fan-out |
| `internal/alerts/sse.go` | NEU: r3labs/sse Server, per-user channels |
| `internal/alerts/matrix_channel.go` | NEU: nikoksr/notify Matrix delivery |
| `internal/alerts/store.go` | NEU: pgx CRUD fuer notifications Tabelle |
| `internal/handlers/http/alerts_handler.go` | NEU: REST + SSE + Webhook endpoints |
| `internal/handler/server.go` | Route registration |

### Phase 2: Python Alert Producer

| Datei | Aenderung |
|---|---|
| `agent/alerts.py` | NEU: `publish_alert(subject, payload)` via nats-py |
| `agent/graph/runner.py` | Alert bei Task completion/error |
| `ingestion/worker.py` | Alert bei Ingestion done/failed |

### Phase 3: LiteLLM Webhook

| Datei | Aenderung |
|---|---|
| `litellm-gateway/config.yaml` | `alerting: ["webhook"]`, `alert_to_webhook_url` |

### Phase 4: Frontend Notification Center

| Datei | Aenderung |
|---|---|
| `control-ui/src/components/NotificationBell.tsx` | NEU: Bell + unread Badge |
| `control-ui/src/components/NotificationSheet.tsx` | NEU: Alert Feed (Sheet) |
| `control-ui/src/hooks/useAlertStream.ts` | NEU: EventSource auf SSE |
| `control-ui/.../ControlTopNav.tsx` | NotificationBell einbinden |
| `agent-chat/src/hooks/useAlertStream.ts` | NEU: Shared SSE hook |

### Phase 5: Notification Preferences (Optional)

- control-ui: Settings fuer welche Alerts, welche Channels
- DB: `storage.notification_preferences` Tabelle
- Channels: Matrix (an/aus), Email (an/aus), Severity-Filter

---

## Alembic Migration

```sql
-- Managed by Go (storage schema), not Alembic
-- Aber fuer Referenz:
-- storage.notifications (siehe DB Schema oben)
-- storage.notification_preferences (Phase 5)
```

Da `storage.*` Schema Go-owned ist, wird die Migration in Go `auto-migrate` gemacht, nicht via Python Alembic.

---

## Verify Gates

- [ ] `go get` fuer nikoksr/notify + r3labs/sse erfolgreich
- [ ] NATS subscribe auf `alerts.*` empfaengt Python-published Events
- [ ] `POST /api/v1/alerts/webhook` empfaengt LiteLLM Budget-Alert
- [ ] SSE `/api/v1/alerts/stream` liefert Events an Browser EventSource
- [ ] Matrix Message erscheint in `#alerts` Room nach Budget-Threshold
- [ ] Element X zeigt Push Notification fuer Matrix Alert Message
- [ ] NotificationBell in control-ui zeigt Unread Count
- [ ] NotificationSheet zeigt Alert-History aus DB
- [ ] Mark-as-Read reduziert Unread Count
- [ ] Python `publish_alert("alerts.agent.completed", ...)` → Toast in Webapp

---

## Relation zu anderen Execs

| Exec | Verbindung |
|---|---|
| **exec-19** | LiteLLM Spend Tracking + Virtual Keys → Budget-Alert Source |
| **exec-17** | OTel Tracing → Anomaly-Detection als Alert-Trigger (spaeter) |
| **exec-a2fm** | Routing-Entscheidungen → Alert bei Model-Failover |
| **exec-merge-chat** | Shared Alert-Stream zwischen control-ui + agent-chat |
| **GCT Hauptprojekt** | Exchange Events → `alerts.exchange.*` NATS Subject |
