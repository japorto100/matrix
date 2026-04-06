# RAG / GraphRAG Strategy 2026

> **Stand:** 13. Maerz 2026
> **Zweck:** Kompakte Arbeitsstrategie fuer produktive Retrieval- und
> Reasoning-Architektur (RAG, GraphRAG, Agentic RAG, UQ) als Ableitung aus
> `Important-RAG_GraphRAG SOTA & Best Practices.md`.
> **Abgrenzung:** Dieses Dokument ist entscheidungsorientiert; tiefe Herleitung,
> Studienbreite und Randfaelle bleiben im `Important-*`-Dokument.

---

## 1. Leitentscheidungen

1. **Dual Pipeline als Baseline**
   - Offline: ingestion/chunking/embedding/index lifecycle
   - Online: routing/retrieval/rerank/generation/caching
2. **Hybrid Retrieval statt Single-Path**
   - Vector fuer semantische Suche
   - KG/Graph fuer relationale Multi-Hop-Fragen
   - SQL/strukturierte Stores fuer exakte Fakten
3. **Contextual Retrieval + Rerank verpflichtend**
   - Kontext-angereicherte Chunks
   - Top-N retrieval, dann rerank, nur Top-K in Prompt
4. **GraphRAG differenziert einsetzen**
   - GraphRAG bei Hierarchie/Beziehungen/Kausalpfaden
   - Vector-RAG bei direkten Fakten-/Dokumentsuchen
   - LinearRAG/LogicRAG als SOTA-Evaluationspfad
5. **Unsicherheit explizit modellieren**
   - UQ/Bayesian-orientierte Confidence-Gates
   - Abstention statt ueberkonfidenter Halluzination
6. **Agentic RAG unter Policy-Boundaries**
   - MCP als Interop-Layer, nicht als Security-Ersatz
   - Retrieval Broker / Tool Proxy / Capability Envelope bleiben Pflicht

---

## 2. Runtime-Modi

### 2.1 Search Mode

- Ziel: schnelle Kandidatenfindung und grounded Antwort
- Pipeline: retrieve -> rerank -> synthesize

### 2.2 Compare/Audit Mode

- Ziel: Whole-doc Vergleich, Gap-/Widerspruchsanalyse
- Pipeline: section/full-doc context + strukturierte Vergleichsfragen

### 2.3 Verify Mode

- Ziel: belastbare Aussagen fuer sensible Entscheidungen
- Pipeline: claim decomposition -> evidence mapping -> contradiction check -> confidence gate

### 2.4 Global/Corpus Mode

- Ziel: corpus-level Aggregation statt nur local chunk lookup
- Pipeline: retrieval + symbolische Aggregation + erlaeuternde Generation

---

## 3. Produktions-Mindeststandards

- semantisches Caching fuer wiederkehrende Queries
- verpflichtende Provenance je Antwort
- verpflichtender Rerank vor finalem Context Build
- Logging von query class, retrieval path, evidence set, confidence/abstain
- language-drift guard fuer multilingual retrieval

---

## 4. Decision Matrix (Kurzform)

| Query-Typ | Primaerer Pfad | Optional |
|---|---|---|
| Direkte Fakten | SQL/structured + Vector | KG bei Beziehungsbedarf |
| Semantische Doku-Suche | Vector + Rerank | Contextual Retrieval |
| Multi-Hop/Hierarchie | KG/GraphRAG | LogicRAG-Pattern |
| Whole-doc Vergleich | Compare/Audit Mode | Long-context Assembly |
| Korpus-Aggregation | Global Mode + Symbolik | LLM fuer Erklaerung |
| High-risk Antwort | Verify Mode | UQ/Abstention Gate |

---

## 5. Priorisierte naechste Schritte

1. Query-Router-Klassen finalisieren (Search/Compare/Verify/Global)
2. Rerank-Pfad und Top-K-Policy als Standard fixieren
3. Evidence-Completeness Gate in Runtime integrieren
4. Language-drift guard fuer multilingual sources definieren
5. UQ-light Start (claim-level confidence + abstain rule) pilotieren

---

## 6. Nicht-Ziele

- kein blindes Framework-Adopt als Architekturersatz
- kein "alles nur Vector-RAG"
- kein unkontrolliertes Agent-Tooling ohne Policy-Boundaries
- kein Long Context als Speicherersatz

---

## 7. Kernquellen (wichtigste URLs)

- Anthropic Contextual Retrieval:
  <https://www.anthropic.com/news/contextual-retrieval>
- LinearRAG (ICLR 2026):
  <https://arxiv.org/abs/2510.10114>
- LogicRAG (AAAI 2026):
  <https://github.com/chensyCN/LogicRAG>
- Bayesian RAG (financial reliability):
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC12886353/>
- BayesRAG (multimodal):
  <https://arxiv.org/abs/2601.07329>
- UQLM:
  <https://github.com/cvs-health/uqlm>
- Agentic RAG (A-RAG):
  <https://arxiv.org/abs/2602.03442>
- Global RAG / GlobalQA:
  <https://arxiv.org/html/2510.26205v1>
- Language Drift (multilingual RAG):
  <https://arxiv.org/abs/2511.09984>
- MCP Spezifikation:
  <https://modelcontextprotocol.io/specification/2025-11-25>

---

## 8. Querverweise im Repo

- `AGENT_ARCHITECTURE.md`
- `AGENT_TOOLS.md`
- `AGENT_SECURITY.md`
- `MEMORY_ARCHITECTURE.md`
- `CONTEXT_ENGINEERING.md`
- `specs/execution/agent_memory_context_delta.md`
- `specs/execution/agent_security_runtime_delta.md`
- `Important-RAG_GraphRAG SOTA & Best Practices.md`
