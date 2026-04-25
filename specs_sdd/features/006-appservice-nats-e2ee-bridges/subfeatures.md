---
title: Appservice NATS E2EE Bridges Subfeatures
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 006
---

# Subfeatures

## 006.1 Go Appservice Matrix/E2EE Gateway

Owns registration, namespace, membership handling, message filters, E2EE
decrypt/encrypt and agent intent sending.

## 006.2 Python NATS Bridge

Owns NATS subscription, agent HTTP/SSE call, reply publishing, health status and
removal of legacy `matrix-nio` behavior.

## 006.3 Subject Routing and Thread Support

Owns global vs per-room/per-agent subjects, `target_agent`, thread metadata and
reply identity. Subject routing is default-disabled until live verified.

## 006.4 E2EE Trust, Backup and Deletion

Owns the E2BE trust model, Cross-Signing, key backup, key deletion flags and
history-retention compromise for agent usefulness.

## 006.5 Agent Sender Identities

Owns `@agent-*` namespace behavior, dynamic reply sender selection and future
per-user agent identity mapping.

## 006.6 Future Messaging Bridges

Owns the roadmap for mautrix WhatsApp/Signal/Telegram/Meta/Discord and bridge
E2BE separation. None of these are closure blockers for current core Matrix
gateway until explicitly pulled into active scope.

## 006.7 Hybrid / Native Agent E2EE

Owns evaluation of per-agent native E2EE with vodozemac-python or successor
bindings. Current accepted behavior remains gateway decrypt.

## 006.8 Production Hardening

Owns NATS TLS, JetStream persistence, NATS authorization and production-level
transport isolation.
