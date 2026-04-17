# Agent Model and Token Tuning

> **Stand:** 16. April 2026
> **Zweck:** Root-Leitfaden fuer Token-, Cache- und Modellpfade im Agent-Runtime-
> Stack. Fokus auf reproduzierbare Optimierung mit Security- und Policy-Gates.
> **Herkunft:** Matrix-adaptierte Fassung aus
> `trading-project/docs/AGENT_MODEL_TOKEN_TUNING.md`.

---

## 1. Leitlinie

Kontextprobleme werden nicht primaer mit groesseren Fenstern geloest, sondern in
dieser Reihenfolge:

1. bessere Context-Assembly und Retrieval-Policy
2. Token-/Prefix-/KV-Optimierung
3. Security- und Tenant-Isolation
4. erst dann Modell- oder Backendwechsel

---

## 2. Ziele

- hoehere Effizienz pro Antwort
- stabilere Qualitaet bei langem Kontext
- keine Security-Regression durch Cache- oder Quantisierungspfade
- klare Go/No-Go-Gates fuer neue Runtime-Techniken

---

## 3. Sofortprofil

Empfohlen fuer produktionsnahe Agent-Tests:

- Kontextbudget pro Task-Typ statt global maximal
- Prefix caching nur mit nachvollziehbarer Invalidation
- Flash Attention dort, wo stabil und verifiziert
- konservative KV-Quantisierung
- Cache- und Policy-Telemetrie aktiv

---

## 4. Sicherheitsregeln

- kein Cache-Reuse ueber unterschiedliche Security-Kontexte
- keine sensitiven Segmente als sharebarer Prefix
- kein Bypass vom Cache-Pfad am Policy-Pfad vorbei
- bei Genauigkeitsabfall in kritischen Flows automatisch konservativeres Profil

---

## 5. Verify-Gates

Neue Tuning-Pfade gehen nur weiter, wenn sie:

- Qualitaets-Evals bestehen
- keine Security-Regression zeigen
- Drift und Miss-Rates sichtbar machen
- zu den Context-/Memory-Policies passen

---

## 6. Relevanz fuer Memory und Context

Fuer Matrix sind vor allem diese Punkte relevant:

- `cached_tokens` und Prefix-Stabilitaet muessen in Runtime/Inspector surfacen
- Compaction-Trigger und Pre-Save-Hooks bleiben in `CONTEXT_ENGINEERING.md`
- aggressive Langkontextpfade ersetzen nicht die Trennung von
  `personal_raw`, `personal_derived`, `personal_kb` und `world`

---

## 7. Querverweise

- `AGENT_TOOLS.md`
- `AGENT_HARNESS.md`
- `AGENT_SECURITY.md`
- `CONTEXT_ENGINEERING.md`
- `MEMORY_ARCHITECTURE.md`
