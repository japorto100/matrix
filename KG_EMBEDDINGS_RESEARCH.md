# Knowledge Graph + Embeddings for Document Retrieval

> Research Findings (02.04.2026) — Ansaetze fuer KG-basiertes Retrieval auf Dokumente, Nachrichten, geopolitische Informationen.

## TL;DR

**Hybrid (KG + Vector Embeddings) gewinnt.** Aber nicht jeder Ansatz passt zu jedem Use-Case. Die Entscheidung haengt ab von: Daten-Dynamik, Query-Typ, Budget.

---

## 1. RAG-Architekturen mit Knowledge Graphs

### GraphRAG (Microsoft)
- **Was:** LLM-basierte Entity/Relationship-Extraction → Community Detection → hierarchische Zusammenfassungen
- **Wann nutzen:** Statischer Korpus, thematische Corpus-weite Queries ("Was sind die geopolitischen Dynamiken?")
- **Nachteil:** O(n) LLM-Kosten bei Indexierung, teuer bei dynamischen Daten
- **DRIFT Search** (2025): Staerkster Query-Modus, dynamische lokale+globale Suche
- GitHub: https://github.com/microsoft/graphrag
- DRIFT Docs: https://microsoft.github.io/graphrag/posts/drift_search/

### LightRAG
- **Was:** Leichtgewichtige Alternative zu GraphRAG, inkrementelle Updates
- **Wann nutzen:** Kontinuierliche Daten (News-Feeds, Message-Streams), Budget-bewusst
- **Vorteil:** 10-20x guenstiger als GraphRAG, vergleichbare Qualitaet bei den meisten Queries
- **Empfehlung:** Bester Startpunkt fuer dynamische Dokument-Pipelines
- Paper: https://arxiv.org/abs/2410.05779
- GitHub: https://github.com/HKUDS/LightRAG

### HippoRAG
- **Was:** Personalized PageRank (PPR) ueber KG fuer Multi-Hop Retrieval
- **Wann nutzen:** Multi-Hop Queries ("Wie haengen Russland, Energiepolitik und EU-Sanktionen zusammen?")
- **Vorteil:** Bestes Accuracy/Cost-Verhaeltnis fuer komplexe Queries
- Paper: https://arxiv.org/abs/2405.14831
- GitHub: https://github.com/OSU-NLP-Group/HippoRAG

### PathRAG
- **Was:** Pfad-basiertes Retrieval — findet Verbindungswege zwischen Entitaeten
- **Wann nutzen:** "Wie sind X und Y ueber Z verbunden?" Queries
- Paper: https://arxiv.org/abs/2502.14902

### SubgraphRAG
- **Was:** Subgraph-Retrieval, serialisiert Triples als Kontext fuer LLM
- **Vorteil:** Einfacher zu implementieren als HippoRAG, aehnliche Qualitaet
- Paper: https://arxiv.org/abs/2501.00332 (ID verifizieren)

---

## 2. Knowledge Graph Embeddings (KGE)

### NICHT verwenden: TransE / RotatE
- Designed fuer statische Ontologie-Graphen (Wikidata-Scale)
- Dokument-KGs sind sparse, noisy, dynamisch → schlechte Performance

### Stattdessen: Textuelle KGE
| Ansatz | Beschreibung | Link |
|--------|-------------|------|
| **SimKGC** | Kontrastive KG Completion mit Text-Encodern | https://arxiv.org/abs/2203.02167 |
| **KGT5** | Seq2Seq KG Completion mit T5 | https://arxiv.org/abs/2108.00800 |
| **Kontextuelle Entity Embeddings** | Mean-Pool der Mention-Embeddings (E5/Voyage) — einfachster Ansatz | Siehe Embedding-Modelle unten |

### Empfehlung
Fuer Dokument-KGs: kontextuelle Entity-Embeddings (mean-pool aller Mentions einer Entitaet) sind einfach, effektiv, und inkrementell aktualisierbar. Keine separate KGE-Pipeline noetig.

---

## 3. Temporale Knowledge Graphs

**Pflicht fuer geopolitische Daten.** Ohne Zeitstempel wird der Graph ein flacher Brei ohne kausale oder temporale Ordnung.

### Anforderungen
- Jede Entity-Extraction und Event-Extraction braucht `published_at` / `occurred_at`
- Relationen brauchen Zeitfenster (`valid_from`, `valid_until`)

### Temporale KG Completion
| Ansatz | Beschreibung | Link |
|--------|-------------|------|
| **TNTComplEx** | Tensor-Decomposition fuer temporale KGs | https://arxiv.org/abs/2004.04926 |
| **CEN** | Context-aware Entity Networks, event-basiert | https://arxiv.org/abs/2206.08471 |
| **TANGO** | ODE-basierte temporale KG Evolution | https://arxiv.org/abs/2105.08070 |

---

## 4. Foundation Model fuer KGs

### Ultra
- **Was:** Foundation Model das zero-shot auf neue KGs transferiert — keine Retraining noetig
- **Wann nutzen:** Entity-Vokabular aendert sich staendig (neue Akteure, Organisationen in News)
- **Vorteil:** Loest das Problem wechselnder Entity-Sets ohne Re-Training
- Paper: https://arxiv.org/abs/2310.04562

---

## 5. Empfohlener Stack

### Entity Extraction
| Tool | Zweck | Link |
|------|-------|------|
| **GLiNER** | Zero-Shot NER, keine domaenenspezifische Fine-Tuning noetig | https://github.com/urchade/GLiNER |

### Knowledge Graph Storage
| Tool | Zweck | Link |
|------|-------|------|
| **kuzu** | Embedded KG (Cypher), kein Server, Python-nativ | https://kuzudb.com / https://github.com/kuzudb/kuzu |

### Embedding-Modelle
| Modell | Zweck | Link |
|--------|-------|------|
| **voyage-3** | Multilinguale Embeddings (kommerziell, top quality) | https://docs.voyageai.com/docs/embeddings |
| **multilingual-E5-large** | Open-Source multilingual Embeddings | https://huggingface.co/intfloat/multilingual-e5-large |

### Vector Storage
| Tool | Zweck |
|------|-------|
| **pgvector** | Dense Chunk Index (bereits im Stack) |

---

## 6. Architektur-Entscheidungsbaum

```
Daten sind... 
├── statisch (Archiv, Reports) → GraphRAG + DRIFT Search
└── dynamisch (News, Messages) → LightRAG
    │
    Query-Typ ist...
    ├── Thematisch ("Ueberblick ueber X") → Community Summaries (GraphRAG/LightRAG)
    ├── Faktisch ("Wann hat X Y gemacht?") → KG Direct Lookup + Temporal Filter
    ├── Multi-Hop ("Verbindung X↔Y via Z") → HippoRAG oder PathRAG
    └── Semantisch ("aehnliche Events wie X") → Vector Search + KG Re-Ranking
```

---

## 7. Anti-Patterns

| Nicht tun | Warum | Stattdessen |
|-----------|-------|-------------|
| TransE/RotatE auf Dokument-KGs | Designed fuer statische Ontologien | Kontextuelle Entity Embeddings |
| KG ohne Zeitstempel | Geopolitik ohne Temporal = nutzlos | Temporal Tagging auf allen Entitaeten/Events |
| Vollstaendiges Re-Indexing bei Updates | Skaliert nicht bei News-Streams | LightRAG (inkrementell) |
| Nur Vector Search ohne KG | Verliert strukturelle Relationen | Hybrid: KG + Vector |
| Nur KG ohne Embeddings | Verliert semantische Aehnlichkeit | Hybrid: KG + Vector |

---

## Quellen

| Referenz | Link |
|----------|------|
| Microsoft GraphRAG | https://github.com/microsoft/graphrag |
| LightRAG | https://arxiv.org/abs/2410.05779 |
| HippoRAG | https://arxiv.org/abs/2405.14831 |
| PathRAG | https://arxiv.org/abs/2502.14902 |
| SubgraphRAG | https://arxiv.org/abs/2501.00332 |
| SimKGC | https://arxiv.org/abs/2203.02167 |
| KGT5 | https://arxiv.org/abs/2108.00800 |
| Ultra | https://arxiv.org/abs/2310.04562 |
| TNTComplEx | https://arxiv.org/abs/2004.04926 |
| CEN | https://arxiv.org/abs/2206.08471 |
| TANGO | https://arxiv.org/abs/2105.08070 |
| GLiNER | https://github.com/urchade/GLiNER |
| kuzu | https://github.com/kuzudb/kuzu |
| voyage-3 | https://docs.voyageai.com/docs/embeddings |
| multilingual-E5-large | https://huggingface.co/intfloat/multilingual-e5-large |
| DRIFT Search | https://microsoft.github.io/graphrag/posts/drift_search/ |
