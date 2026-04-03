# Graph Database Vergleich — kuzu vs Neo4j vs FalkorDB vs TuringDB

> Analysiert am 02.04.2026 | Fokus: KG fuer Dokumente, Nachrichten, geopolitische Informationen

## TL;DR

| Rang | Datenbank | Empfehlung |
|---|---|---|
| 1 | **FalkorDB** | Operativer KG (Graphiti, Real-Time, Traversals) |
| 2 | **kuzu** | Embedded Analytics KG (LightRAG, Batch, kein Server) |
| 3 | Neo4j | Nur wenn Enterprise-Infrastruktur bereits vorhanden |
| 4 | TuringDB | Beobachten — beeindruckende Benchmarks (115-298x Neo4j), BSL Lizenz, noch frueh |

---

## Detailvergleich

| Feature | kuzu | Neo4j | FalkorDB | TuringDB |
|---|---|---|---|---|
| **Deployment** | Embedded (in-process) | Server (JVM, Cluster) | Docker One-Liner | Server (vermutlich) |
| **Lizenz** | MIT | GPL + Commercial | MIT | Unbekannt |
| **Query-Sprache** | Cypher (voll) + SQL | Cypher (voll) | Cypher (Subset) | Unbekannt/Partial |
| **Architektur** | Column-Store, Factorized | B-Tree, OLTP | GraphBLAS Sparse Matrix | Unbekannt |
| **Stars** | ~3.000 | ~13.000 | ~1.500 | 112 (4.089 Commits) |
| **Alter** | 3+ Jahre | 15+ Jahre | 5+ Jahre (Redis-Lineage) | Aktiv, fruehe Adoption |
| **Sprache** | C++ | Java (JVM) | C (GraphBLAS) | C++ |
| **LDBC Benchmarks** | Ja (top performer) | Ja (Referenz) | Ja (top performer) | Eigene (115-298x Neo4j) |
| **Vector Search** | HNSW, unified mit Cypher | HNSW (ab 5.11) | Flat/Brute-Force | Faiss Integration |
| **Traversal Speed vs Neo4j** | 5-20x schneller | Baseline | 10-50x schneller | 115-298x (eigene Benchmarks) |
| **Bulk Ingestion** | Exzellent (CSV) | Langsam (Tx-Log) | Schnell | Unbekannt |
| **RAM-Verbrauch** | Niedrig (disk-backed, mmap) | Hoch (JVM Heap 2-8 GB) | Mittel (in-memory) | In-Memory Column-Store |
| **Python SDK** | Ja (pip install kuzu) | Ja (neo4j-driver) | Ja (falkordb-py) | Ja (pip install turingdb) |
| **Node.js SDK** | Ja | Ja | Ja | Nein |
| **Graphiti Driver** | Nein (muesste man selbst bauen) | Ja (primaer) | Ja (nativ) | Nein |
| **LightRAG Backend** | Ja (Default) | Ja | Nein | Nein |
| **LangChain** | Limitiert | Ja (voll) | Wachsend | Nein |
| **Git-like Versioning** | Nein | Nein | Nein | Ja (Branch/Commit/Merge) |
| **Lizenz** | MIT | GPL + Commercial | SSPL v1 | BSL |

---

## Performance-Benchmarks

### LDBC Social Network Benchmark (SNB)

```
Traversal-Queries (Multi-Hop, Aggregation):

FalkorDB  ████████████████████████████████████████████████████  10-50x
kuzu      █████████████████████████████████████                  5-20x
Neo4j     ██████████                                             1x (Baseline)
TuringDB  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░             Keine Daten
```

### Warum FalkorDB so schnell ist:
GraphBLAS — Graph-Operationen werden als Sparse-Matrix-Multiplikationen ausgefuehrt. Multi-Hop Pattern Matching profitiert enorm davon. Ein 3-Hop Query der in Neo4j 100ms dauert, laeuft in FalkorDB in 2-10ms.

### Warum kuzu schnell ist:
Factorized Column-Store — analytische Queries (Aggregation, Scans) profitieren von spaltenorientierter Speicherung und Worst-Case-Optimal Joins. Besonders stark bei OLAP-Patterns.

---

## Staerken je Use-Case

### kuzu — Embedded Analytics
```
✅ Kein Server noetig (direkt in Python/Node eingebettet)
✅ LightRAG Default-Backend
✅ Beste Bulk-Ingestion Performance
✅ MIT Lizenz, komplett kostenlos
✅ Niedrigster RAM-Verbrauch
✅ Hybrid: Cypher + SQL in einer Query
✅ HNSW Vector Index unified mit Cypher Queries
❌ Kein Graphiti-Driver
❌ Single-Process (kein Multi-Node Cluster)
❌ Kleineres Ecosystem als Neo4j
```

### FalkorDB — Operativer Graph
```
✅ Schnellste Traversals (GraphBLAS)
✅ Nativer Graphiti-Driver (sofort einsatzbereit)
✅ Einfachstes Deployment: docker run -p 6379:6379 falkordb/falkordb
✅ SSPL Lizenz (Self-Hosting frei, nur DB-as-a-Service verboten)
✅ Redis-Protokoll kompatibel
✅ Kann bestehenden Redis-Container dual nutzen
❌ Cypher nur Subset (kein volles openCypher)
❌ Vector Search weniger ausgereift als kuzu/Neo4j
❌ In-Memory = RAM-limitiert
```

### Neo4j — Enterprise Standard
```
✅ Groesstes Ecosystem (LangChain, LlamaIndex, Graphiti, APOC, GDS)
✅ 15+ Jahre Production-Track-Record
✅ AuraDB Cloud (Managed Service)
✅ Graph Data Science Library (PageRank, Community Detection, etc.)
✅ Vollstaendigstes Cypher
❌ Langsamste Traversals der drei produktiven DBs
❌ JVM = hoher RAM-Verbrauch (2-8 GB Baseline)
❌ GPL + Commercial Lizenz
❌ Bulk Ingestion langsam
❌ Teuer im Enterprise-Tier
```

### TuringDB — High-Performance Analytical Graph DB (C++)
Repo: https://github.com/turing-db/turingdb | Lizenz: BSL | 112 Stars, 4.089 Commits
```
✅ C++ von Grund auf, Column-Oriented Storage
✅ MASSIVE Performance: 115-298x schneller als Neo4j (eigene Benchmarks!)
     - 1-hop: 12ms vs 1.390ms (115x)
     - 2-hop: 11ms vs 1.420ms (129x)
     - 7-hop: 172ms vs 51.264ms (298x)
     - 8-hop: 476ms vs 98.183ms (206x)
✅ Git-like Versioning (Commit/Branch/Merge auf Graph-Ebene)
✅ Zero-Lock Concurrency (Snapshot Isolation, DataParts)
✅ Faiss Vector Search Integration
✅ OpenCypher Query Language
✅ Python SDK (pip install turingdb)
✅ REST API (localhost:6666) + WebGL Visualisierung
✅ Immutable Snapshots (GDPR/Audit/Compliance)
✅ pip install turingdb / uv add turingdb / Docker / NixOS
❌ BSL Lizenz (nicht MIT/Apache — kommerziell eingeschraenkt)
❌ Kein Graphiti-Driver
❌ Kein LangChain/LlamaIndex Integration
❌ 112 Stars — noch frueh in Adoption
❌ Eigene Benchmarks, keine unabhaengige LDBC-Teilnahme
❌ Docker hat Performance-Einbussen (lt. README)
```

---

## TuringDB — Deep Dive

Repo: https://github.com/turing-db/turingdb | C++ | BSL | 112 Stars, 4.089 Commits

### Architektur

TuringDB ist eine **in-memory column-oriented Graph-Datenbank** in C++, optimiert fuer analytische und read-intensive Workloads.

**Kern-Innovationen:**

1. **Column-Oriented Storage:** Nodes/Edges in Spalten statt Zeilen → effizientes Streaming fuer analytische Queries
2. **DataParts:** Immutable Daten-Partitionen → Git-like Versioning + Zero-Lock Concurrency
3. **Snapshot Isolation:** Jede Query sieht konsistenten Snapshot, keine Locks zwischen Reads/Writes
4. **Faiss Integration:** Vector Similarity Search ueber Facebook's Faiss Library

### Performance (eigene Benchmarks vs Neo4j, 10M+ Nodes)

| Query | TuringDB | Neo4j | Faktor |
|---|---|---|---|
| 1-hop | 12ms | 1.390ms | **115x** |
| 2-hop | 11ms | 1.420ms | **129x** |
| 4-hop | 14ms | 1.568ms | **112x** |
| 7-hop | 172ms | 51.264ms | **298x** |
| 8-hop | 476ms | 98.183ms | **206x** |

**Caveat:** Das sind Eigenmessungen, keine unabhaengigen LDBC-Benchmarks. Aber die Groessenordnung (100x+) ist plausibel fuer Column-Store + In-Memory vs. JVM + B-Tree.

### Git-like Versioning (Alleinstellungsmerkmal)

```
turingdb commit "Added Q3 geopolitical events"
turingdb branch "sanctions-analysis"
turingdb merge "sanctions-analysis" → main
turingdb time-travel --to "2026-03-15"
```

Kein anderer Graph-DB bietet das. Fuer geopolitische Analyse extrem relevant:
- Snapshot eines KG zu einem bestimmten Zeitpunkt
- Branching fuer "What-if" Szenarien
- Audit Trail durch immutable Commits

### Deployment

```bash
pip install turingdb        # Python SDK
turingdb                    # Interactive CLI
turingdb -demon             # Daemon Mode
# REST API auf localhost:6666
```

Dependencies: Boost, OpenBLAS, Faiss, AWS SDK, Bison/Flex

### Vergleich: TuringDB vs kuzu (fuer unseren Use-Case)

| Dimension | TuringDB | kuzu |
|---|---|---|
| Traversal Speed | 115-298x Neo4j (eigene) | 5-20x Neo4j (LDBC) |
| Vector Search | Faiss (extern) | HNSW (nativ, unified Cypher) |
| Versioning | Git-like (Branch/Commit/Merge) | Nein |
| Lizenz | **BSL** (kommerziell eingeschraenkt) | **MIT** (frei) |
| LightRAG | Nein | Ja (Default) |
| Graphiti | Nein | Nein |
| Deployment | Server/Daemon | Embedded (in-process) |
| Benchmarks | Eigene | LDBC (unabhaengig) |

### Bewertung:

TuringDB ist **deutlich interessanter als zunaechst angenommen:**
- Die Column-Store + Snapshot-Architektur ist solide
- Git-like Versioning auf Graph-Ebene ist ein echtes Alleinstellungsmerkmal
- Die Performance-Zahlen (wenn verifizierbar) waeren beeindruckend
- Faiss-Integration fuer Vector Search ist pragmatisch

**Aber:**
- BSL-Lizenz ist ein Blocker fuer viele Open-Source-Projekte
- 112 Stars vs 3.000 (kuzu) — Ecosystem-Gap ist real
- Eigene Benchmarks ohne LDBC-Validierung
- Kein Graphiti/LightRAG/LangChain Driver

### Empfehlung:
**Beobachten, nicht adoptieren.** Das Git-like Versioning und die Performance sind compelling. Wenn ein Graphiti-Driver und LDBC-Benchmarks kommen, koennte TuringDB fuer den temporalen KG (Geopolitik) die bessere Wahl als FalkorDB werden. Re-evaluieren Q3/Q4 2026.

---

## Empfohlene Architektur fuer unser Projekt

### Zwei-Datenbank-Architektur:

```
┌─────────────────────────────────────────────────────────┐
│              ANALYTISCHER KG (kuzu, embedded)            │
│                                                         │
│  Dokumente/News → LightRAG → kuzu                       │
│  - Bulk-Ingestion von Dokumenten                         │
│  - Agent Working Memory                                  │
│  - OLAP Queries (Aggregation, Statistiken)               │
│  - Hybrid Vector + Cypher Queries                        │
│  - Kein Server, direkt in Python-Prozess                 │
│  - MIT Lizenz                                            │
└─────────────────────────────────────────────────────────┘
                        +
┌─────────────────────────────────────────────────────────┐
│              OPERATIVER KG (FalkorDB, Docker)            │
│                                                         │
│  Graphiti Temporal KG                                    │
│  - Nativer FalkorDBDriver                                │
│  - Multi-Hop Traversals (10-50x schneller als Neo4j)     │
│  - Real-Time Entity/Event Queries                        │
│  - Temporal Relationships (valid_from/valid_until)        │
│  - docker run -p 6379:6379 falkordb/falkordb             │
│  - SSPL Lizenz (Self-Hosting frei)                       │
└─────────────────────────────────────────────────────────┘
```

### Warum zwei DBs statt einer:

| Anforderung | Beste DB | Grund |
|---|---|---|
| Batch-Ingestion (1000 Docs) | kuzu | Column-Store, CSV-Import |
| Real-Time Multi-Hop Query | FalkorDB | GraphBLAS, 10-50x |
| Embedded (kein Server) | kuzu | In-Process |
| Graphiti Integration | FalkorDB | Nativer Driver |
| LightRAG Integration | kuzu | Default Backend |
| Vector + Graph Hybrid | kuzu | HNSW unified mit Cypher |

Beide sprechen Cypher. kuzu ist MIT, FalkorDB ist SSPL (kein Problem fuer Self-Hosting, nur DB-as-a-Service verboten). Sie ergaenzen sich perfekt.

---

## Migration Path

Falls spaeter **eine einzige DB** gewuenscht:
- **kuzu** ist der wahrscheinlichste Kandidat — das Team arbeitet aktiv an Server-Mode und Multi-Node Support. Wenn Graphiti einen kuzu-Driver bekommt (oder wir ihn bauen), koennte kuzu allein ausreichen.
- **FalkorDB** koennte ausreichen wenn Vector Search dort reifer wird.
- **Neo4j** bleibt Fallback fuer Enterprise-Anforderungen.

---

## Links

| Datenbank | Website | GitHub |
|---|---|---|
| kuzu | https://kuzudb.com | https://github.com/kuzudb/kuzu |
| Neo4j | https://neo4j.com | https://github.com/neo4j/neo4j |
| FalkorDB | https://falkordb.com | https://github.com/FalkorDB/FalkorDB |
| TuringDB | — | https://github.com/turing-db/turingdb |
