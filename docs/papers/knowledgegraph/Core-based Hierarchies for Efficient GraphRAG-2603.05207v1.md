

Core-based Hierarchies for Efficient GraphRAG
## Jakir Hossain
University at Buffalo
Buffalo, NY, USA
mh267@buffalo.edu
## Ahmet Erdem Sarıyüce
University at Buffalo
Buffalo, NY, USA
erdem@buffalo.edu
## Abstract
Retrieval-Augmented Generation (RAG) enhances large language
models by incorporating external knowledge. However, existing
vector-based methods often fail on global sensemaking tasks that
require reasoning across many documents. GraphRAG addresses
this by organizing documents into a knowledge graph with hierar-
chical communities that can be recursively summarized. Current
GraphRAG approaches rely on Leiden clustering for community de-
tection, but we prove that on sparse knowledge graphs, where aver-
age degree is constant and most nodes have low degree, modularity
optimization admits exponentially many near-optimal partitions,
making Leiden-based communities inherently non-reproducible. To
address this, we propose replacing Leiden with 푘 -core decomposi-
tion, which yields a deterministic, density-aware hierarchy in linear
time. We introduce a set of lightweight heuristics that leverage the푘-
core hierarchy to construct size-bounded, connectivity-preserving
communities for retrieval and summarization, along with a token-
budget–aware sampling strategy that reduces LLM costs. We evalu-
ate our methods on real-world datasets including financial earnings
transcripts, news articles, and podcasts, using three LLMs for an-
swer generation and five independent LLM judges for head-to-head
evaluation. Across datasets and models, our approach consistently
improves answer comprehensiveness and diversity while reduc-
ing token usage, demonstrating that푘-core-based GraphRAG is an
effective and efficient framework for global sensemaking.
## Keywords
GraphRAG, k-core, Leiden, RAG
## 1  Introduction
Retrieval-Augmented Generation (RAG) enhances large language
models (LLMs) with external knowledge, enabling more grounded
and accurate responses to complex queries [2,7,16,17,33]. It is
particularly useful when the corpus is too large to fit within an
LLM’s context window [15,18]. In a typical RAG setup, a small set
of relevant records is retrieved and fed, along with the query, to
the LLM for response generation. RAG has been widely adopted in
domains such as healthcare, law, finance, and education, improving
faithfulness, reducing hallucinations, mitigating privacy risks, and
enhancing robustness [19, 30, 31, 34, 35].
Most RAG systems rely on lexical/semantic retrieval over text
and are effective only for queries answerable from a few documents.
These approaches struggle with multi-hop reasoning or queries re-
quiring synthesis across semantically diverse documents or global
corpus understanding [15,18]. For instance, answering “How have
patient outcomes in cancer treatment evolved in response to multi-
center clinical trials over the last 15 years?” demands aggregating
evidence across many sources, which conventional RAG methods
cannot easily support. Similarly, a financial analyst asking “What
common strategies have semiconductor companies adopted in re-
sponse to supply chain disruptions over the past decade?” must
synthesize themes across hundreds of earnings call transcripts, a
task that no single retrieved passage can answer. We refer to such
queries as global sensemaking tasks: they require the system to
identify recurring themes, reconcile conflicting perspectives, and
synthesize evidence distributed across the entire corpus, capabilities
that go beyond standard RAG.
Graph-based Retrieval-Augmented Generation (GraphRAG) has
recently emerged as a promising approach for global sensemaking
tasks by representing the corpus as a knowledge graph and organiz-
ing it into a hierarchy of communities that can be recursively sum-
marized [6]. The GraphRAG framework introduced by Edge et al.
relies on modularity-based community detection, such as Leiden
[28]. However, Leiden often produces hierarchies that are shallow,
overly fragmented, and/or dominated by a few large communities.
Building on an observation by Good, de Montjoye, and Clauset[9],
we prove that when the average degree is constant and most nodes
have low degree—the regime of typical knowledge graphs—the
number of near-optimal modularity partitions is exponential in the
graph size (Theorem 1). This implies that Leiden-based communi-
ties are inherently non-reproducible on such graphs, compounding
known issues with resolution limits and sensitivity to initialization.
In practice, this instability causes communities to unpredictably
merge or fragment semantically meaningful structures.
Motivated by these limitations, we explore푘-core–based alterna-
tives for hierarchical graph construction in GraphRAG. The푘-core
decomposition organizes a network into nested layers of increasing
minimum degree [23]. Each node is assigned a core number: the
largest푘for which it belongs to a subgraph where every node has
at least푘neighbors. This creates a deterministic, density-aware
hierarchy that can be computed in a single푂(|퐸|)pass. Unlike
modularity-driven methods, the푘-core hierarchy naturally captures
progressively denser and more cohesive substructures, making it
well suited for global sensemaking tasks that require integrating
evidence across multiple interconnected regions of the corpus. In
knowledge graphs specifically, higher푘-cores correspond to enti-
ties connected through multiple distinct relational paths, providing
a natural proxy for topical centrality that modularity’s comparison
to a degree-preserving null model cannot capture.
We operationalize this hierarchy through a set of lightweight, in-
terpretable community construction heuristics that operate over dif-
ferent levels of the푘-core decomposition. Our approach constructs
balanced hierarchical communities while explicitly controlling clus-
ter sizes to respect LLM context constraints. These heuristics enable
comprehensive and diverse summaries without excessive token us-
age. Additionally, we introduce a token-budget–aware sampling
strategy that further reduces LLM costs while preserving retrieval
quality. We make the following key contributions:
arXiv:2603.05207v1  [cs.IR]  5 Mar 2026

Jakir Hossain and Ahmet Erdem Sarıyüce
•We introduce푘-core decomposition as a drop-in replace-
ment for Leiden in GraphRAG, yielding deterministic, density-
aware hierarchies in linear time.
•We prove that modularity optimization on sparse graphs
admits exponentially many near-optimal partitions (Theo-
rem 1), formally explaining why Leiden-based community
detection is unreliable on knowledge graphs.
•We propose multiple hierarchical heuristic strategies that
exploit different regions of the induced푘-core hierarchy to
balance coverage, granularity, and efficiency.
## •
We conduct extensive evaluations on three real-world datasets,
using three LLMs for answer generation and five indepen-
dent LLM judges for head-to-head evaluation.
2  Related Work and Background
In this section, we review the literature on Graph-based RAG and
remind key concepts of GraphRAG workflows and푘-core decom-
position.
Graph-based RAG. Traditional vector-based RAG retrieves rel-
evant passages to augment LLM responses, but is largely limited
to single-hop, fact-based queries where the answer resides within
one or a few contiguous passages. When reasoning must span mul-
tiple documents or synthesize information across a corpus, these
approaches fall short [10, 20].
To address this, several methods incorporate graph structures
into the retrieval process. One line of work constructs query-focused
subgraphs from knowledge graphs and performs reasoning over
them. Systems such as KG-GPT [14], G-Retriever [11], GRAG [12],
and HLG [8] follow this paradigm, extracting relevant subgraphs
and using LLMs to reason over the retrieved structure, thereby
improving multi-hop answer quality. A complementary line of
work enhances the retrieval step itself with graph signals, using
graph  topology  to  guide  which  documents  or  passages  are  se-
lected [20,25,29]. However, both subgraph-reasoning and graph-
enhanced retrieval methods are primarily designed for queries that
require a bounded number of reasoning hops. They do not address
global sensemaking, tasks where the answer requires understanding
themes, patterns, or relationships that emerge only when consider-
ing an entire corpus.
GraphRAG [6] addresses this gap by applying Leiden-based hi-
erarchical community detection on a knowledge graph and using
the resulting communities for global sensemaking (see Section 2.1
for details). A key limitation, however, is that modularity-based
clustering methods like Leiden can produce highly uneven hier-
archies, where community sizes vary widely across levels. This
imbalance can lead to inconsistent summary quality and makes it
difficult to control the granularity of retrieved context. Our work
addresses this limitation by replacing community detection with
푘-core decomposition, which yields a naturally nested and more
balanced hierarchy of dense subgraphs.
2.1  Community-based GraphRAG Overview
Edge et al.[6] introduced a graph-based approach for global sense-
making question answering by a community-driven GraphRAG
workflow. Here, we briefly describe the two main stages of the
GraphRAG workflow: indexing and query-time answer generation,
followed by their evaluation conditions.
Indexing. Large text corpora are first split into manageable chunks,
from which entities, relationships, and claims are extracted using
LLMs. These elements are aggregated into a knowledge graph,
where nodes represent entities or claims and edges represent rela-
tionships, weighted by frequency. The graph is hierarchically parti-
tioned into communities using Leiden community detection [28],
recursively identifying sub-communities until reaching leaf-level
communities that cannot be further split. Leaf-level communities
are summarized first by prioritizing elements according to edge
prominence, adding source and target node descriptions, edges,
and related claims into the LLM context until the token limit is
reached. For higher-level communities, if all element summaries fit
within the context window, they are summarized directly; other-
wise, sub-community summaries iteratively replace longer element-
level descriptions until they fit. This process, from knowledge graph
construction to hierarchical community summaries, is referred to
as indexing.
Query-Time Answer Generation. Given a user query, indexed
community summaries are used to generate a final answer through
a multi-stage Map-Reduce process. First, summaries are randomly
shuffled and divided into chunks of a pre-specified token size to
ensure relevant information is distributed across multiple contexts
rather than concentrated in a single window. Next, intermediate
answers are generated for each chunk in parallel, with the LLM also
assigning a helpfulness score between 0 and 100. These intermediate
answers are then sorted by helpfulness and iteratively added into
a new context window until the token limit is reached. The LLM
uses this aggregated context to produce the final global answer.
By leveraging the hierarchical structure of the communities, this
approach allows answers to be generated from different levels and
enables robust aggregation of information from all relevant sub-
communities.
Evaluation for GraphRAG. Evaluating RAG systems for multi-
document reasoning presents distinct challenges beyond standard
QA benchmarks. Recent work assesses output quality along dimen-
sions such as comprehensiveness, diversity, empowerment, and
directness [6]. Edge et al.tested six conditions, including four hi-
erarchical community levels (C0–C3), source-text summarization,
and a vector-based RAG approach. The hierarchical configurations
differ in granularity. C0 uses only top-level communities, yielding
the smallest set of summaries, C1 uses communities one level below
the root for a slightly finer decomposition and so on. Results on two
datasets show that all community-level approaches (C0–C3) out-
perform both source-text summarization and vector RAG for global
sensemaking. Among these, C2 and C3 consistently achieve the
best performance, hence we consider those two for our evaluation.
## 2.2  Hierarchical 푘-core Decomposition
In this work, we consider the knowledge graph as an unweighted
graph퐺= (푉,퐸), where푉denotes the set of nodes and퐸de-
notes the set of edges. The degree of a node푢within a subgraph
푆 ⊆ 퐺is denoted푑푒푔(푢,푆). A푘-core is the maximal connected
subgraph푆 ⊆ 퐺in which every vertex has at least푘neighbors,
i.e.,푑푒푔(푢,푆) ≥ 푘 ∀푢 ∈ 푆. Each node is assigned a core number,

Core-based Hierarchies for Efficient GraphRAG
the largest푘for which it belongs to a푘-core. The푘-shell is the
set of nodes with core number푘[4]. The푘-cores for all푘can be
computed by recursively removing nodes with degree less than푘
and their edges, which runs in푂(|퐸|)time [1]. This process of iden-
tifying all푘-cores and assigning core numbers is referred to as core
decomposition. Since nodes can belong to multiple푘-cores with
different푘values, the decomposition naturally forms a hierarchy
of nested dense subgraphs. This hierarchy can be represented as a
tree, with nodes denoting subgraphs and edges encoding contain-
ment relationships. The root represents the entire graph (1-core),
while child nodes correspond to subgraphs with increasing core
numbers. Internal nodes may contain denser subgraphs with higher
core values, forming a multi-level structure that captures the nested
organization of densely connected regions within the graph.
3  Why Modularity Optimization is Unreliable
on Sparse Knowledge Graphs?
Modularity-based community detection methods such as Leiden [28]
compare observed within-community edge density to the expec-
tation under a degree-preserving null model (the configuration
model), an approach that works well in dense networks but de-
grades in sparse ones. Good, de Montjoye, and Clauset [9] provided
a systematic characterization of this degradation. They showed that
the modularity function푄typically admits an exponentially large
number of distinct high-scoring partitions while lacking a clear
global maximum: a phenomenon they termed the degeneracy of mod-
ularity. Using real-world metabolic networks, they demonstrated
that these near-optimal partitions can fundamentally disagree on
key properties such as the composition of the largest modules and
the distribution of module sizes, meaning that any optimizer (in-
cluding Louvain and Leiden) is effectively selecting one solution
from a vast equivalence class, guided more by random seeds and
tie-breaking rules than by genuine structure. They further showed
that푄
## 푚푎푥
depends strongly on both network size and the num-
ber of modules, and that degeneracy is most severe in sparse and
hierarchically structured networks.
Modularity Degeneracy. We give a key structural observation:
the low-degree nodes (degree at most a fixed constant푑) have
vanishing modularity sensitivity in sparse graphs, because their
few edges contribute negligibly to the objective. Denote by푛
## ≤d
## =
## |{푖 ∈ 푉
## :푘
## 푖
≤ 푑}|the number of such nodes. For small푑, these
nodes can be reassigned across communities with negligible impact
on modularity, creating an exponentially large degenerate set.
Recall that the modularity of a partition휎of a graph퐺=(푉,퐸)
with푛nodes and푚edges is푄(휎)=
## 1
## 2푚
## Í
## 푖,푗
## [퐴
## 푖푗
## −푘
## 푖
## 푘
## 푗
## /
## 2푚] 훿(휎
## 푖
## ,휎
## 푗
## ),
where푘
## 푖
is the degree of node푖. Let푄
## ∗
= max
## 휎
푄(휎)denote the op-
timal modularity. For휀>0, we define the휀-degeneracy of퐺as the
number of structurally distinct partitions achieving near-optimal
modularity:D(휀)=|{휎 ∈ P(퐺) : 푄
## ∗
## −푄(휎)< 휀}|.
Theorem 1 (Modularity Degeneracy in Sparse Graphs). Let
퐺be a graph with푛nodes,푚edges, average degree
## ̄
## 푘=2푚/푛=푂(1),
and 푛
## ≤d
=Θ(푛). Then for any 휀> 푑(2+
## ̄
## 푘)/(2푚),
## D(휀) ≥  2
## 푛
## ≤d
## /(푑+1)
## .
In particular, the number of near-optimal partitions is exponential
in푛, and the tolerance threshold휀required to trigger this blowup is
## 푂(1/푛).
Proof sketch and the full proof are given in Appendix A.
Knowledge graphs (KG) are particularly well-suited to푘-core
decomposition over modularity-based methods for two structural
reasons. First, their heavy-tailed but low-mean degree distributions
mean that푛
## ≤푑
=Θ(푛), placing them squarely in the regime where
Theorem 1 bites hardest. Second, KG edges are semantically mean-
ingful rather than stochastic, so the푘-core criterion, requiring each
node to have at least푘neighbors, directly captures genuine rela-
tional richness in a way that comparison to a degree-preserving
null model does not.
## 4  A Robust Alternative: 푘-core Decomposition
Theorem 1 exposes a fundamental instability: for a graph with low
average degree; any modularity optimizer, Leiden included, selects
one partition from an exponentially large near-optimal plateau.
Different seeds, tie-breaking rules, or minor edge perturbations
yield structurally different communities.
The푘-core decomposition sidesteps this problem entirely. It
is unique: for every graph퐺and integer푘, the푘-core퐻
## 푘
is the
unique maximal subgraph with minimum degree≥ 푘, computed by
the deterministic peeling process; no optimization landscape, no
stochasticity. It is robust: adding or removing a few edges changes
the shells by at most a proportional number of nodes, whereas
Theorem 1 implies that even a single edge can shift the optimal par-
tition across the entire degenerate set. And푘-core decomposition
provides a natural hierarchy: the nested shells퐻
## 1
## ⊇ 퐻
## 2
## ⊇ ···re-
flect structural connectivity rather than comparison to a null model.
In the sparse regime where푘
## 푖
## ·푘
## 푗
/2푚 ≈0 for most pairs, the null
model is nearly vacuous yet푘-core structure remains informative.
The 2-core captures the backbone of multiply-connected nodes
while degree-1 nodes form the periphery. In knowledge graphs, this
distinction is semantically meaningful: multiple relational paths
between entities signal genuine topical relatedness. Last, but not
least, computing푘-core is much cheaper than Leiden; a single pass
over the graph suffices to compute all and a hierarchy [21].
In GraphRAG, community assignments determine which entities
are summarized together and which retrieval units are constructed.
Exponential degeneracy means Leiden-based pipelines produce
non-reproducible summaries: the same knowledge graph under
different random seeds yields different communities and different
retrieval behavior, with communities that are either too fragmented
(splitting apart a natural topic) or too arbitrary (grouping unrelated
peripheral nodes together because the optimization found a mar-
ginal modularity gain). The푘-core decomposition eliminates this
variance. Its nested shells provide a small number of progressively
tighter subgraphs where the innermost cores represent the most
interconnected, and therefore most semantically central — concepts,
while the outer shells supply context. This maps naturally onto a
summarization hierarchy: summarize the dense core first, then ex-
pand outward, producing stable, deterministic retrieval units from
which summaries and indices can be reliably built.
Remark. A natural refinement of푘-core is the푘-truss [5], which
requires every edge to participate in at least푘−2 triangles, yielding

Jakir Hossain and Ahmet Erdem Sarıyüce
e
m
o
p
n
k
l
g
f
## 1-core
a-p
## 2-core
f-p
b
a
## 1-core
## 2-core
## 3-core
m-p
## Res
f-h
i
j
c
d
## 3-core
## Res
a, b
## Res
i, j
h
## 2-hop
c, d
## Res
k, l
## SGLN
e
Figure 1:푘-core decomposition (left) and corresponding hier-
archy tree produced by RkH (right).
tighter subgraphs. However, knowledge graphs are triangle-poor:
edges typically connect entities through distinct relation types
(e.g., born_in, capital_of ), producing bipartite-like local structure
with global clustering coefficients well below 0.05. Even the 3-truss
discards the vast majority of the graph, making the degree-based
푘 -core criterion the right granularity for sparse relational graphs.
Motivated by these advantages, we propose a set of heuristics
for efficient global sensemaking in GraphRAG. These heuristics
leverage the푘-core hierarchy to generate size-constrained clusters,
merge small two-hop clusters, and handle residual components.
4.1  Handling Residuals in 푘-core Hierarchy
Our first heuristic builds on the푘-core hierarchy while address-
ing practical issues such as singleton nodes and oversized clusters
by separating dense cores from sparse residuals. At each level,
dense components are recursively partitioned into size-bounded,
connectivity-preserving clusters, while low-core residuals are han-
dled separately to avoid distorting core structure. The result is
a deterministic hierarchy that captures both central regions and
peripheral context, enabling reliable hierarchical summarization.
Algorithm 1 presents the resulting Residual-aware푘-core Hi-
erarchy heuristic,RkHin short. It takes two parameters: the input
graph (퐺), and the maximum cluster size (푀).RkHbegins by ex-
tracting the largest connected component and removing self-loops
(line 1), as done in GraphRAG [6]. It then computes the core number
for each node (line 2). The hierarchy construction is initialized by
settingℓ=1, enqueuing full node set푉intoQ, and initializing an
empty cluster setC and global singleton setG
## 푠
## (lines 3–4).
The graph is then processed iteratively over increasing core
levelsℓuntil the maximum core is reached (line 5), splitting each
cluster푆into core (푐(푣) ≥ ℓ) and residual (푐(푣)< ℓ) nodes (line 8).
Core components smaller than or equal to푀are added directly toC
and the queue; larger components are split into size-bounded clus-
ters via Split before adding (lines 9–11). The maximum cluster size
(푀) is set by dividing the input token limit by the average tokens per
node, providing a practical estimate that keeps most clusters within
the allowed input size. Residual nodes are handled similarly, either
added directly or Split as needed (lines 13–14); since these residual
subgraphs correspond to leaf clusters, they are not pushed to the
next-level queue. The Split procedure breaks each oversized cluster
into smaller, size-bounded clusters by greedily growing each cluster
from a high-degree seed node, prioritizing neighbors that maximize
internal connectivity. This ensures that dense regions remain intact
Algorithm 1:RkH: Residual-aware푘-core Hierarchy (퐺,푀)
Require:  Graph퐺= (푉,퐸) , max cluster size 푀
Ensure:  Hierarchical clusters C
1: 퐺 ← LCC(퐺) ; remove self-loops
2:  Compute core number 푐(푣) for all 푣 ∈ 푉
3:  Initialize queue Q ← {(푉)} and level ℓ ← 1
4:  Initialize cluster set C ← ∅, Global singleton G
## 푠
## ← ∅
5: while ℓ ≤ max푐(푣) do
## 6:  Q
## ′
## ← ∅
7:   for each cluster 푆 ∈ Q do
## 8:푆
## 푐
## ← {푣 ∈ 푆 | 푐(푣) ≥ ℓ}, 푆
## 푟
## ← 푆\푆
## 푐
9:for each connected component 푅 of퐺[푆
## 푐
] do
## 10:푅
## ′
## ←
## (
## {푅},|푅| ≤ 푀
## Split(퐺,푅,푀)otherwise
## 11:    C ← C∪푅
## ′
## , Q
## ′
## ← Q
## ′
## ∪푅
## ′
12:end for
13:for each connected component 푅 of퐺[푆
## 푟
] do
## 14:    C ← C∪
## (
## {푅},|푅| ≤ 푀
## Split(퐺,푅,푀)otherwise
15:end for
## 16:푆
single
## ← {푅 ∈ C | |푅|= 1}
## 17:   H ← {푅 ⊆ 푆
single
| 푅 is 2-hop connected in퐺}
## 18:   G
## 푠
## ← 푆
single
## \
## Ð
## 푅∈H
## 푅
19:for each 2-hop component 푅 of H do
## 20:    C ← C∪
## (
## {푅},|푅| ≤ 푀
## Split-2hop(퐺,푅,푀)otherwise
21:end for
22:   end for
## 23:  Q ← Q
## ′
## , ℓ ← ℓ+ 1
24: end while
25:  Attach each of G
## 푠
to neighboring clusters in C
26: return C
while respecting the maximum cluster size; full algorithmic details
are provided in Algorithm 3 in Appendix B.1.
Now, we extract singleton clusters from the existing setC(line 16)
into푆
single
and form new clustersHconsisting of nodes that are
2-hop connected in퐺(line 17). A set푅is 2-hop connected if each
node푢 ∈ 푅has a path of length≤2 in퐺to some other node푣 ∈ 푅.
Any remaining singleton nodes not included inHare added to
global setG
## 푠
(line 18). Now, each 2-hop component fromHis either
added directly toCor split into smaller clusters via SPLIT-2HOP if
it exceeds size 푀 (lines 19–20).
The SPLIT-2HOP procedure greedily splits a 2-hop connected
component,  ensuring  that  nodes  sharing  common  anchors  are
grouped together. Starting from a seed node with the largest anchor
set, the algorithm greedily grows a cluster by adding nodes that
share anchors with the current cluster, continuing until the cluster
reaches the maximum size or no eligible nodes remain. Anchor
nodes connected to multiple cluster members are then included to
maintain structural coherence. The process produces size-bounded
clusters that respect both 2-hop connectivity and anchor relation-
ships. Full details are provided in Algorithm 4 in Appendix B.2.
After all clusters at the current level are processed, the queue
is updated with the newly formed clusters, and the level counter
is incremented (line 23). Once all core levels have been processed,
a final attachment step assigns each node inG
## 푠
to a neighboring
cluster inC, ensuring that no isolated nodes remain in the hierarchy

Core-based Hierarchies for Efficient GraphRAG
(line 25). Finally, the algorithm returns the hierarchical cluster
setC(line 26). This approach ensures size-bounded, connectivity-
preserving clusters while capturing both dense core structures and
sparse residual nodes.
Figure 1 shows an example hierarchy produced byRkH. The
1-core contains all nodes (a–p). At the next level, the 2-core consists
of nodes (f–p), while the remaining nodes (a–e) form different
clusters, including a connected component (a–b), a 2-hop connected
group (c–d), and a singleton (e). At the 3-core level, only nodes
(m–p) remain, and the residual nodes (f–l) are partitioned into
three connected components (f–h), (i–j), and (k–l). Note that the
singleton (e) is attached to its neighboring cluster (f–h) at the end.
This recursive decomposition yields a hierarchy where higher푘-
cores capture denser subgraphs and residuals are organized into
progressively finer-grained structures, as formalized in Algorithm 1.
## 4.2  Handling Small Clusters
Due to the sparse nature of knowledge graphs, many tiny clusters
(often containing only two nodes) can arise from previous heuris-
tic. As a result, when GraphRAG evaluates community relevance
during query answering, these small clusters usually receive low
scores. Consequently, they are often excluded from the final answer
generation, which can affect overall sensemaking performance. We
propose to explicitly merge such small clusters.
Merging 2-hop Small Clusters. InRkH, some 2-hop clusters gen-
erated in lines 19–20 may contain only two nodes. These very
small clusters can fragment the hierarchy and reduce connectivity
if left unprocessed. To address this, we apply a post-processing step
after Algorithm 1 that merges small 2-hop clusters into larger clus-
ters whenever possible, or creates new clusters when no suitable
neighbors exist. The merging procedure is detailed in Algorithm 2,
referred to asM2hC. First, all 2-hop clusters of size two are sepa-
rated from the remaining clusters (lines 1–2). While small clusters
remain (line 3), the algorithm selects the small cluster with the
most connections to existing clusters (line 4) and counts its neigh-
bors in each cluster (line 5). If neighbors exist, the small cluster
is merged in-place into the cluster with which it shares the most
edges (lines 6–8). Otherwise, a new cluster is created for the small
cluster (line 9). After each iteration, the processed small cluster is
removed from the pool (line 12). Finally, the algorithm returns the
updated cluster set with all small clusters integrated (line 14).
Merging Residual Clusters. In addition to the previous heuristics,
we observe that many residual connected components produced
duringRkH(lines 13–14) have size two. To address this, we introduce
an extended heuristic, referred to asMRC.MRCis conceptually similar
toM2hC, but instead of focusing solely on 2-hop clusters, it handles
all small residual clusters of size two. The only modification occurs
in line 1 of Algorithm 2, where both residual clusters and 2-hop
clusters of size two are collected into the setSfor processing. The
rest of the procedure remains unchanged: each small cluster is
merged into a neighboring parent cluster when possible; otherwise,
a new cluster is created only if no suitable neighbors exist.
Algorithm 2: M2hC : Merge 2-hop Clusters (퐺 ,C)
Require:  Graph 퐺=(푉,퐸), existing cluster setC
Ensure:  Updated cluster setC with small clusters merged
1: S ← All 2-hop clusters of size 2 inC
## 2: L ←C\S
3: whileS≠∅ do
4:Pick small cluster퐶
## 푠
∈S with the most neighbors inL
5:Count neighbors of퐶
## 푠
in each cluster of 퐿 ∈ L
6:   if any neighbors exist then
7:Find 퐿
## 푏푒푠푡
∈ L with most neighbors of퐶
## 푠
## 8:    퐿
## 푏푒푠푡
## ← 퐿
## 푏푒푠푡
## ∪퐶
## 푠
9:   else
## 10:  L ←L∪퐶
## 푠
11:   end if
12:Remove퐶
## 푠
fromS
13: end while
14: return L
Note that, forM2hCandMRC, we focus specifically on clusters
of size two, as they account for the majority of small clusters ob-
served in practice. Clusters of size three or larger occur infrequently,
and trying to merge would not yield measurable improvements;
moreover, merging them would unnecessarily inflate neighboring
clusters and weaken size constraints.
4.3  Token Efficiency via Sampling
In large hierarchical graph decompositions, leaf-level communi-
ties can be densely connected, and many nodes/edges within the
same community frequently carry overlapping information. Pass-
ing all of this content to an LLM for retrieval or summarization can
therefore be costly in terms of tokens, leading to inefficiency and
redundancy. To address this challenge, we propose the Round-Robin
Token-Constrained Selection (RRTC) heuristic, which efficiently re-
duces token usage while preserving the most informative edges
from each community. RRTC operates on leaf-level communities
produced by any hierarchy heuristic (e.g.,RkH,M2hC, orMRC) and
selects a representative subset of edges under a fixed token budget.
Within each community, edges are ranked by the combined degree
of their endpoints to reflect overall prominence. Selection then
proceeds in a round-robin fashion across leaf-level communities,
traversing from higher to lower푘-shells, until the token budget
is exhausted. By sampling a representative subset of edges from
each community, RRTC captures the essential information without
including all nodes/edges.
## 5  Experimental Setup
In this section, we describe the experimental setup, including the
datasets and evaluation approach. Since our study targets the global
sensemaking task, we selected three datasets requiring reasoning
over multiple documents. The first two align with the original
Edge et al.’s study, while the third also requires multi-document
reasoning. Dataset sizes range from approximately 1M to 6M tokens,
all processed using the same knowledge graph construction pipeline
used by [6]. Details of these datasets are reported in Table 1.
Podcast transcripts (podcast). Public transcripts of Behind the
Tech with Kevin Scott, a podcast featuring conversations between

Jakir Hossain and Ahmet Erdem Sarıyüce
Table 1: Summary statistics of datasets used in our experi-
ments, showing model, dataset, number of documents, and
graph information (|푉|: nodes,|퐸|: edges,퐾
## 푚
: maximum core
number). Post-cutoff data is used forGPT-3.5-turbo(cutoff:
Sep 1, 2021) andGPT-4o-mini(cutoff: Oct 1, 2023), while full
data is used for GPT-5-mini .
ModelDataset# Docs    |V||E|K
## 푚
GPT-3.5-turbo
## (post-cutoff )
podcast36179126516
news60910655153686
semiconductor1834324954613
GPT-4o-mini
## (post-cutoff )
podcast136288825
news331531273166
semiconductor63202942499
GPT-5-mini
## (full)
podcast72332377617
news609449979418
microsoft4579017027
Microsoft CTO Kevin Scott and various thought leaders in science
and technology [22]. The corpus contains 72 documents with ap-
proximately 1 million tokens in total.
News articles (news). A benchmark dataset of news articles span-
ning multiple categories, including entertainment, business, sports,
technology, health, and science [26]. It is a multi-document QA
dataset containing 609 documents and nearly 1.4 million tokens.
S&P 500 earnings transcripts. This dataset consists of earnings
call transcripts from publicly listed S&P 500 companies spanning
2013–2025 [3], with over 20,000 documents totaling 232M tokens.
ForGPT-3.5-turboandGPT-4o-mini, to focus on multi-document
synthesis and keep the dataset manageable, we use only post-cutoff
transcripts from the Semiconductor industry (semiconductor),
yielding 183 and 63 documents, respectively. ForGPT-5-mini, since
the fullsemiconductordataset is large (nearly 6M tokens), we
use Microsoft earnings calls from 2013–2024 (microsoft) to limit
corpus size.
## 5.1  Evaluation Criteria
Following the methodology of [6], we generated 125 sensemaking
questions usingGPT-5-mini(details are in Appendix C.0.1). Con-
sistent with prior work [6,13,27], we evaluate answers using two
primary criteria: Comprehensiveness, which measures how thor-
oughly an answer addresses all relevant aspects of a question, and
Diversity, which measures the extent to which an answer captures
varied perspectives and insights. Edge et al.[6] also report Em-
powerment (ability to support informed judgment) and Directness
(degree to which an answer directly addresses the question); results
for these metrics are provided in the Appendix (Table 12).
Retrieval approaches and evaluation. We focus on C2 and
C3 from Section 2, which perform best overall, and evaluate all푘-
core heuristics—RkH,M2hC, andMRC—against them. Higher푘-core
levels typically yield finer-grained communities, improving answer
quality via more detailed summaries (see Appendix, Table 8). Hence,
for all heuristics, we consider the Leaf and immediate parent levels,
labeled LF and L1 (e.g.,RkHLF). For evaluation, we use a head-to-
head framework where LLMs compare answers to select a winner,
loser, or tie. To improve reliability, we use multiple evaluators and
perform repeated assessments, with majority voting determining
the final outcome—suitable for global sensemaking tasks without
gold-standard references (see Appendix C.0.2 for details).
Configuration. For fair comparison with [6], we performed
indexing using a 600-token chunking window with 100-token over-
lap and an 8k-token context window for community summaries,
following their approach. We utilized the public Azure OpenAI end-
point and the OpenAI API forGPT-3.5-turbo,GPT-4o-mini, and
GPT-5-mini. For the multiple-judge evaluation,GPT-5-miniwas
accessed via Azure OpenAI, while the other four LLMs (Gemini
3 Pro Preview, Gemini 2.5 Pro, Qwen3 Next 80B, and DeepSeek
v3.2) were accessed via GCP. All LLM-based evaluations were per-
formed on a GCP virtual machine equipped with 32 GB memory
and 16 vCPUs (Intel Haswell architecture). Detailed prompts for
graph construction, community summaries, and global answer gen-
eration (following [6]), along with our code, are available here:
https://github.com/jakir-sust/Kcore-GraphRAG.
6  Results and Analysis
Knowledge cutoff is a key consideration in RAG evaluation [24,32],
as models may have already seen the corpus if it predates their
training data. To minimize such contamination, we prioritize post-
cutoff data when selecting both datasets and evaluation models.
Our primary evaluation (Section 6.1) usesGPT-3.5-turboand
GPT-4o-miniacross three post-cutoff datasets:podcast,news, and
semiconductor. This setup ensures a fair comparison of GraphRAG
configurations under realistic retrieval and sensemaking conditions,
while minimizing the influence of memorized knowledge. To fur-
ther verify that our heuristics generalize to more recent, stronger
models, we conduct a secondary evaluation usingGPT-5-minion
the full datasets, compensating for the limited post-cutoff content
(Section 6.2). We then report the statistical significance of our푘-
core–based heuristics (Section 6.3). Finally, we analyze token effi-
ciency compared to Edge et al. [6] and evaluate our Round-Robin
Token-Constrained Selection (RRTC) heuristic that aims to reduce to-
ken usage while maintaining competitive performance (Section 6.4).
6.1  Results on Post–Cutoff Data
In this section, we evaluate the performance of our heuristics vs.
Leiden-based GraphRAG [6] on three datasets under a post–knowledge-
cutoff setting, usingGPT-3.5-turboandGPT-4o-mini, according
to the two metrics defined earlier: comprehensiveness and diversity.
Table 2 summarizes theGPT-3.5-turboresults. We report head-
to-head comparisons of our푘-core based heuristics (in rows) vs.
Leiden-based GraphRAG [6] (columns) on post-knowledge-cutoff
content (September 2021), covering 183 documents forsemiconductor,
609 fornews, and 36 forpodcast. For each of our heuristics, we
consider the leaf (LF) and parent-of-leaf (L1) levels, and for Leiden-
based GraphRAG, we consider C2 (third from top) and C3 (fourth
from top) levels, which consistently perform well (see Section 2 for
details). Results on C0 and C1 are given in the Appendix (Table 10).
Across all datasets and configurations, our푘-core–based heuris-
tics achieve higher win rates than the C2 and C3 configurations
of Edge et al.in approximately 70–75% of comparisons. Ties are
generally infrequent (typically below 10%) and nearly absent for
semiconductor, indicating decisive preferences.M2hCLF is the
most consistently strong configuration in the evaluation. It
never records a negative net win rate across any dataset, condition,

Core-based Hierarchies for Efficient GraphRAG
Table 2:GPT-3.5-turbopost-cutoff: Head-to-head win rates (%), for comprehensiveness and diversity metrics. C2 and C3 are
Leiden community levels from Edge et al. [6]. LF is leaf-level communities, and L1 is the level immediately above the leaf.
GPT-3.5-turbopodcastnewssemiconductor
results forC2C3C2C3C2C3
ComprehensivenessWinLossTieWinLossTieWinLossTieWinLossTieWinLossTieWinLossTie
RkH L156368504284444125238104848456422
RkH LF584204452452426494745050050482
M2hC L1583665242656341050361458420484210
M2hC LF584025244454388563865444254424
## MRC L15044648484504284246125440650464
## MRC LF5050053434424810484846040067294
DiversityWinLossTieWinLossTieWinLossTieWinLossTieWinLossTieWinLossTie
RkH L1465045244446522365865248048520
RkH LF564224452448448564404652244506
M2hC L1643245642244524445065446050500
M2hC LF6634055441564226137252480543610
## MRC L1505004654062380484485640454442
## MRC LF524804951052480564406238069283
or metric. On comprehensiveness, it maintains steady positive mar-
gins (+8 to +18 net) across all three datasets against both C2 and C3,
with no sharp degradation between conditions. Performance is even
stronger for diversity: it achieves the highestpodcastwin rate in
the table (66% against C2), delivers strongnewsresults that actu-
ally improve from C2 to C3 (reaching 61/37 in C3), and posts solid
semiconductorgains especially in C3 (+18 net). Dataset-wise, gains
are largest onsemiconductor, whereMRCLF averages∼64% wins
and peaks at 67–69% against C3. Forpodcastandnews,M2hCLF
performs best, averaging∼57% and∼56%, respectively. Across
datasets, our heuristics outperform C3 more strongly than C2 by
roughly 3–6% on average.
Averaged across datasets and community levels, leaf-level (LF)
variants consistently outperform their L1 counterparts by 5–10 per-
centage points, confirming that finer-grained communities lead to
more informative and diverse summaries. This effect is particularly
pronounced onpodcastandsemiconductor, where LF configura-
tions frequently exceed 55–60% win rates across both metrics. Over-
all,M2hCLF andMRCLF emerge as the strongest heuristics:M2hCLF
shows the most consistent gains for diversity onpodcastandnews,
while MRC LF dominates comprehensiveness on semiconductor .
We conduct the same evaluation usingGPT-4o-mini, restricting
all datasets to content published after its knowledge cutoff (October
2023). This results in 63 documents forsemiconductor, 331 docu-
ments fornews, and 13 documents forpodcast. Overall, the trends
remain consistent withGPT-3.5-turbo, though performance mar-
gins are narrower and ties more frequent, as expected given that
GPT-4o-miniis a stronger model and the post-cutoff subsets are
smaller. The detailed results are given in the Appendix (Table 11).
6.2  Evaluation on Full Data by GPT-5-mini
In  our  secondary  experiments,  we  useGPT-5-minito  examine
whether the trends observed with earlier models persist with a
stronger, more recent evaluator. Due toGPT-5-mini’s later train-
ing window, none of the datasets have sufficient post-cutoff content.
Hence, we evaluate on the fullnews,podcast, andmicrosoft(since
semiconductor would create an excessively large corpus).
Table 3 reports head-to-head results between Leiden C2 and
our푘-core heuristics; C3 results are given in Appendix (Table 9).
While our heuristics continue to show improvements, the high
proportion of ties suggests that prior knowledge reduces the dis-
criminative power of head-to-head evaluation. Across datasets and
Table 3:GPT-5-minifull: Head-to-head win rates (%), for com-
prehensiveness and diversity metrics against Leiden C2 level
from Edge et al. [6]. LF indicates leaf-level communities, and
L1 indicates the level immediately above the leaf.
GPT-5-minipodcastnewsmicrosoft
Comprehen.WinLossTieWinLossTieWinLossTie
RkH L141471256422434314
RkH LF5048250455454015
M2hC L140528403426404515
M2hC LF5242640402048502
## MRC L14850242382045487
## MRC LF54442423622453520
DiversityWinLossTieWinLossTieWinLossTie
RkH L14044165044648502
RkH LF50482454312384517
M2hC L1375112403822453817
M2hC LF5636840372352462
## MRC L14850236402455423
## MRC LF54442373726404317
metrics, leaf-level variants generally outperform L1 by 2–6 per-
centage points, withM2hCLF showing the strongest gains for di-
versity onpodcastandMRCLF performing best for comprehensive-
ness onmicrosoft. WhileM2hCLF still achieves the strongest
overall performance,MRCLF edges outM2hCLF onpodcastand
microsoft. Overall win rates remain around 45–55%, reflecting
narrower margins than withGPT-3.5-turboand slightly wider
than withGPT-4o-mini. Several L1 configurations fall below 50%,
indicating that gains are concentrated in leaf-level variants. Never-
theless, the directional consistency with earlier evaluators suggests
that푘-core-based heuristics retain an advantage, albeit a modest
one, even under a stronger model whose prior knowledge reduces
the discriminative power of head-to-head evaluation.
## 6.3  Statistical Analysis
To assess statistical significance, we follow the procedure of [6]
and report p-values for pairwise comparisons of each heuristic
against C2/C3 baselines on the comprehensiveness metric using
GPT-3.5-turbopost-cutoff data in Table 4 (details and diversity
results are in Appendix D). Values with푝<0.005 are highlighted
in bold. Overall,RkHandM2hCare significant onpodcastandnews,
whileM2hCandMRCperform best onsemiconductor. Notably,M2hCLF
is the only heuristic significant (푝<0.005) against both C2 and C3
across all datasets.
Summary. The results above show that the performance gap be-
tween our heuristics and Leiden-based C2/C3 is systematic rather

Jakir Hossain and Ahmet Erdem Sarıyüce
than incidental. Knowledge graphs exhibit extremely sparse graph
structures; e.g., average degrees in our datasets range from 2.88
to 4.42 and 55-60% of nodes have a degree of just 1. This high
prevalence of degree-1 nodes means that the majority of nodes
have only a single connection, providing insufficient local structure
for Leiden’s modularity optimization to form meaningful commu-
nities, as the algorithm relies on dense local neighborhoods to
effectively aggregate nodes into clusters. As Theorem 1 shows,
Leiden’s degeneracy on such sparse graphs makes it unlikely to
find the “right” partition, as there are exponentially many near-
equivalent solutions, most of which group peripheral nodes incoher-
ently. In contrast,푘-core–based heuristics produce a deterministic
hierarchy that is structurally grounded, explaining the consistent
advantage of our methods acrossGPT-3.5-turbo,GPT-4o-mini,
andGPT-5-minievaluations. Note that nearly 45% of clusters from
RkHhave size 2, soM2hCandMRChelp improve performance by merg-
ing these, reducing fragmentation. Clusters of size 3 or 4 account for
only 10–12%, and merging them offers little benefit while inflating
neighboring clusters, so they were excluded from our small-cluster
definition. UnderGPT-3.5-turbo, these differences are statisti-
cally significant across all three datasets (푝<0.005 forM2hCLF),
and directionally consistent underGPT-4o-miniandGPT-5-mini,
where stronger prior knowledge narrows the margins but does not
eliminate the advantage.
6.4  Token Utilization and Impact of RRTC
Finally, we analyze how the evaluated methods consume tokens,
and how our round-robin token-constrained selection (RRTC) mech-
anism (see Section 4.3) performs. We first analyze the number of
communities produced by each heuristic, along with the percent-
age of source tokens contained in those communities. These are
the communities and tokens that are used to answer queries via
LLM calls: fewer communities reduce the number of LLM calls, and
lower token counts reduce overall LLM token usage. Results on
GPT-3.5-turbopost-cutoff data are shown in Table 5 for leaf-level,
which typically contain more communities and use more tokens
than L1. Notably,MRCreduces both the number of communities and
the tokens used: it consistently produces the fewest communities
and lowest coverage (55–60%), meaning it aggressively consolidates
information. These reductions indicate that our heuristics use fewer
tokens and require fewer LLM calls, while achieving comparable
or improved performance on global sensemaking, as shown in the
previous section.
Impact of Round-Robin Token-Constrained Selection (RRTC).
Table 6 reports results forM2hCLF with RRTC across three datasets,
Table 4: Wilcoxon signed-rank test p-values for comprehen-
siveness (GPT-3.5-turbo) across datasets and baselines. Val-
ues with 푝< 0.005 are highlighted in bold.
## Cond.podcastnewssemiconductor
## C2C3C2C3C2C3
RkHL1<0.001  <0.0011.000   <0.0011.000   <0.001
RkHLF<0.001  <0.001<0.0010.3700.9820.363
M2hC
## L1<0.001  <0.001<0.001  <0.001<0.0010.006
M2hCLF<0.001  <0.001<0.001  <0.001<0.001  <0.001
## MRC
## L10.0071.000<0.0010.069<0.0010.073
## MRCLF0.982   <0.0010.0071.000<0.001  <0.001
Table 5: Community statistics across datasets, showing the
number of communities and the percentage of source text
used at different hierarchy levels and methods.
Dataset# TokensMetricC2C3  RkH LF  M2hC LF  MRC LF
podcast180,267# Comm.291301351311194
## Coverage (%)68.9370.8783.7075.4758.08
news1,340,078# Comm.2,0192,0212,2051,8631,357
## Coverage (%)65.9071.2676.4665.7455.08
semic.438,819# Comm.627696847705468
## Coverage (%)66.8172.6790.1876.4559.94
compared against Leiden C2/C3 under three edge budgets: 80%,
70%, and 60% of the original graph. The table reports token us-
age relative to C2/C3 and head-to-head win rates against them for
comprehensiveness and diversity, where win rates are computed
against losses only (ties excluded); thus, a 55% win rate implies a
45% loss rate.
Across datasets, RRTC maintains competitive performance even
when selecting only 60% of graph edges. Comprehensiveness win
rates  remain  in  the  50–56%  range,  with  the  highest  values  on
semiconductorat the 80% budget, reaching 56% and 58% against C2
and C3, respectively. Diversity is similarly preserved, often exceed-
ing 55% onpodcastandsemiconductordespite substantial edge
reduction. As the edge budget decreases from 80% to 60%, win rates
gradually decline, with comprehensiveness onpodcastdropping
below 50%, indicating that a 60% budget may be too aggressive for
some dataset–metric combinations. Overall, RRTC reduces token
usage by up to∼40% relative to Leiden C2/C3 while maintaining
competitive comprehensiveness and diversity, providing a practical,
token-efficient alternative under moderate budget constraints.
Table 6: RRTC (M2hCLeaf) vs. Leiden C2/C3: Head-to-head
win rates (%) on comprehensiveness and diversity
DatasetEdge   Relative tokenComp.Div.
budgetusage (%)
win rate (%)win rate (%)
## (%)C2C3C2C3C2C3
podcast
## 80908857556455
## 70797754525652
## 60686647465149
news
## 80817554545558
## 70716549545256
## 60605652504650
semic.
## 80928556585560
## 70817453535057
## 60696455505254
## 7  Conclusion
We proved that modularity optimization is inherently unreliable
on the sparse graphs typical of GraphRAG knowledge graphs, and
proposed푘-core–based heuristics that yield deterministic, size-
bounded hierarchies in linear time. Across three datasets, three
generator LLMs, and five LLM judges, our approach consistently
improves comprehensiveness and diversity while reducing token
usage compared to Leiden-based GraphRAG. Future work includes
extending the framework to dynamic knowledge graphs and ex-
ploring its applicability beyond global sensemaking tasks.

Core-based Hierarchies for Efficient GraphRAG
## References
[1]Vladimir Batagelj and Matjaž Zaversnik. 2011. Fast algorithms for determining
(generalized) core groups in social networks. Advances in Data Analysis and
## Classification 5, 2 (2011), 129–145.
[2]Tal Baumel, Matan Eyal, and Michael Elhadad. 2018. Query focused abstractive
summarization: Incorporating query relevance, multi-document coverage, and
summary length constraints into seq2seq models. arXiv preprint arXiv:1801.07704
## (2018).
[3]Michele Ca’ Zorzi, Gianluigi Lopardo, and Ana-Simona Manu. 2025. Verba Volant,
Transcripta Manent: What Corporate Earnings Calls Reveal About the AI Stock
Rally. 3093 (2025).  https://glopardo.com/corporatetalks/
## [4]
Shai Carmi, Shlomo Havlin, Scott Kirkpatrick, Yuval Shavitt, and Eran Shir. 2007.
A model of Internet topology using k-shell decomposition. Proceedings of the
National Academy of Sciences 104, 27 (2007), 11150–11154.
[5]J. Cohen. 2008. Trusses: Cohesive subgraphs for social network analysis. National
## Security Agency Technical Report (2008).
## [6]
## Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva
Mody, Steven Truitt, Dasha Metropolitansky, Robert Osazuwa Ness, and Jonathan
Larson. 2024.   From local to global: A graph rag approach to query-focused
summarization. arXiv preprint arXiv:2404.16130 (2024).
[7]Yunfan  Gao,  Yun  Xiong,  Xinyu  Gao,  Kangxiang  Jia,  Jinliu  Pan,  Yuxi  Bi,  Yi
Dai, Jiawei Sun, Meng Wang, and Haofen Wang. 2024.  Retrieval-Augmented
Generation for Large Language Models: A Survey.  arXiv:2312.10997 [cs.CL]
https://arxiv.org/abs/2312.10997
## [8]
## Abdellah Ghassel, Ian Robinson, Gabriel Tanase, Hal Cooper, Bryan Thompson,
Zhen Han, Vassilis Ioannidis, Soji Adeshina, and Huzefa Rangwala. 2025.  Hi-
erarchical Lexical Graph for Enhanced Multi-Hop Retrieval. In Proceedings of
the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining V.2
(Toronto ON, Canada) (KDD ’25). Association for Computing Machinery, New
York, NY, USA, 4457–4466.   https://doi.org/10.1145/3711896.3737233
[9]Benjamin H Good, Yves-Alexandre De Montjoye, and Aaron Clauset. 2010. Per-
formance of modularity maximization in practical contexts. Physical Review
E—Statistical, Nonlinear, and Soft Matter Physics 81, 4 (2010), 046106.
## [10]
## Haoyu Han, Yu Wang, Harry Shomer, Kai Guo, Jiayuan Ding, Yongjia Lei, Ma-
hantesh Halappanavar, Ryan A. Rossi, Subhabrata Mukherjee, Xianfeng Tang, Qi
He, Zhigang Hua, Bo Long, Tong Zhao, Neil Shah, Amin Javari, Yinglong Xia, and
Jiliang Tang. 2025. Retrieval-Augmented Generation with Graphs (GraphRAG).
arXiv:2501.00309 [cs.IR]  https://arxiv.org/abs/2501.00309
## [11]
Xiaoxin He, Yijun Tian, Yifei Sun, Nitesh Chawla, Thomas Laurent, Yann LeCun,
Xavier Bresson, and Bryan Hooi. 2024. G-retriever: Retrieval-augmented gen-
eration for textual graph understanding and question answering. Advances in
## Neural Information Processing Systems 37 (2024), 132876–132907.
## [12]
Yuntong Hu, Zhihan Lei, Zheng Zhang, Bo Pan, Chen Ling, and Liang Zhao.
- GRAG: Graph Retrieval-Augmented Generation. arXiv:2405.16506 [cs.LG]
https://arxiv.org/abs/2405.16506
[13]Boyoung Kim, Dosung Lee, Sumin An, Jinseong Jeong, and Paul Hongsuck
Seo. 2025. ReTAG: Retrieval-Enhanced, Topic-Augmented Graph-Based Global
Sensemaking. In Findings of the Association for Computational Linguistics: EMNLP
## 2025. 22249–22277.
## [14]
Jiho Kim, Yeonsu Kwon, Yohan Jo, and Edward Choi. 2023.  Kg-gpt: A general
framework for reasoning on knowledge graphs using large language models.
arXiv preprint arXiv:2310.11220 (2023).
[15]Yuri Kuratov, Aydar Bulatov, Petr Anokhin, Dmitry Sorokin, Artyom Sorokin,
and Mikhail Burtsev. 2024.  In search of needles in a 11m haystack: Recurrent
memory finds what llms miss. arXiv preprint arXiv:2402.10790 (2024).
[16]Md Tahmid Rahman Laskar, Enamul Hoque, and Jimmy Huang. 2020. Query fo-
cused abstractive summarization via incorporating query relevance and transfer
learning with transformer models. In Canadian conference on artificial intelligence.
## Springer, 342–348.
[17]Patrick  Lewis,  Ethan  Perez,  Aleksandra  Piktus,  Fabio  Petroni,  Vladimir
## Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rock-
täschel, et al.2020. Retrieval-augmented generation for knowledge-intensive nlp
tasks. Advances in neural information processing systems 33 (2020), 9459–9474.
[18]Nelson F Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua,
Fabio Petroni, and Percy Liang. 2024. Lost in the middle: How language models
use long contexts. Transactions of the association for computational linguistics 12
## (2024), 157–173.
[19]Fatma Miladi, Valéry Psyché, and Daniel Lemire. 2024. Leveraging gpt-4 for ac-
curacy in education: A comparative study on retrieval-augmented generation in
moocs. In International Conference on Artificial Intelligence in Education. Springer,
## 427–434.
[20]Boci Peng, Yun Zhu, Yongchao Liu, Xiaohe Bo, Haizhou Shi, Chuntao Hong, Yan
Zhang, and Siliang Tang. 2025. Graph retrieval-augmented generation: A survey.
ACM Transactions on Information Systems 44, 2 (2025), 1–52.
## [21]
Ahmet Erdem Sariyüce and Ali Pinar. 2016. Fast hierarchy construction for dense
subgraphs. 10, 3 (Nov. 2016), 97–108.
[22]Kevin Scott. 2024. Behind the Tech. https://www.microsoft.com/en-us/behind-
the-tech.  Accessed: 2026-01-01.
[23]Stephen B Seidman. 1983.   Network structure and minimum degree.  Social
networks 5, 3 (1983), 269–287.
[24]Minjae Seo, Wonwoo Choi, Myoungsung You, and Seungwon Shin. 2025.  Au-
toPatch: Multi-Agent Framework for Patching Real-World CVE Vulnerabilities.
arXiv preprint arXiv:2505.04195 (2025).
[25]Jiashuo Sun, Chengjin Xu, Lumingyuan Tang, Saizhuo Wang, Chen Lin, Yeyun
Gong, Lionel M Ni, Heung-Yeung Shum, and Jian Guo. 2023. Think-on-graph:
Deep and responsible reasoning of large language model on knowledge graph.
arXiv preprint arXiv:2307.07697 (2023).
[26]Yixuan  Tang  and  Yi  Yang.  2024.Multihop-rag:  Benchmarking  retrieval-
augmented generation for multi-hop queries. arXiv preprint arXiv:2401.15391
## (2024).
[27]Yash Tiwari, Owais Ahmad Lone, and Mayukha Pal. 2025. OntoRAG: Enhancing
Question-Answering through Automated Ontology Derivation from Unstruc-
tured Knowledge Bases. arXiv preprint arXiv:2506.00664 (2025).
## [28]
Vincent A Traag, Ludo Waltman, and Nees Jan Van Eck. 2019. From Louvain to
Leiden: guaranteeing well-connected communities. Scientific reports 9, 1 (2019),
## 1–12.
[29]Yu Wang, Nedim Lipka, Ryan A Rossi, Alexa Siu, Ruiyi Zhang, and Tyler Derr.
- Knowledge graph prompting for multi-document question answering. In
Proceedings of the AAAI conference on artificial intelligence, Vol. 38. 19206–19214.
[30]Nirmalie Wiratunga, Ramitha Abeyratne, Lasal Jayawardena, Kyle Martin, Stew-
art Massie, Ikechukwu Nkisi-Orji, Ruvan Weerasinghe, Anne Liret, and Bruno
Fleisch. 2024.  CBR-RAG: case-based reasoning for retrieval augmented gen-
eration in LLMs for legal question answering. In International Conference on
Case-Based Reasoning. Springer, 445–460.
[31]Ran Xu, Wenqi Shi, Yue Yu, Yuchen Zhuang, Bowen Jin, May Dongmei Wang,
Joyce Ho, and Carl Yang. 2024.  Ram-ehr: Retrieval augmentation meets clini-
cal predictions on electronic health records. In Proceedings of the 62nd Annual
Meeting of the Association for Computational Linguistics (Volume 2: Short Papers).
## 754–765.
[32]Zhuoyi Yang, Yurun Song, Iftekhar Ahmed, and Ian Harris. 2026. Fine-Tuning vs.
RAG for Multi-Hop Question Answering with Novel Knowledge. arXiv preprint
arXiv:2601.07054 (2026).
## [33]
Jin-ge Yao, Xiaojun Wan, and Jianguo Xiao. 2017. Recent advances in document
summarization. Knowledge and Information Systems 53, 2 (2017), 297–336.
## [34]
Boyu Zhang, Hongyang Yang, Tianyu Zhou, Muhammad Ali Babar, and Xiao-
Yang Liu. 2023. Enhancing financial sentiment analysis via retrieval augmented
large language models. In Proceedings of the fourth ACM international conference
on AI in finance. 349–356.
[35]Wayne Xin Zhao, Kun Zhou, Junyi Li, Tianyi Tang, Xiaolei Wang, Yupeng Hou,
Yingqian Min, Beichen Zhang, Junjie Zhang, Zican Dong, et al.2023. A survey
of large language models. arXiv preprint arXiv:2303.18223 1, 2 (2023).

Jakir Hossain and Ahmet Erdem Sarıyüce
A  Proof of Theorem 1
Proof sketch.
Step 1: Low-degree nodes are weakly coupled. A node with
degree푘
## 푖
≤ 푑participates in at most푑edges. Moving it between
communities changes modularity by at most푂(푑/푚): the adjacency
term shifts by at most푑/푚, and the null-model penalty shifts by
## 푂(푘
## 푖
## · 퐾
## 푟
## /(2푚)
## 2
## )where퐾
## 푟
is the total degree of the destination
community. In the sparse regime where푚=Θ(푛), this is푂(1/푛),
so the node’s community assignment barely affects the objective.
Step 2: Weakly coupled nodes can be independently reas-
signed. Reassigning one low-degree node perturbs another’s sensi-
tivity by only푂(1/푛
## 2
). By selecting a large independent set among
the low-degree nodes, which is straightforward since these nodes
have bounded degree, we obtainΘ(푛)nodes whose reassignments
are approximately independent. Each can be placed in at least two
communities without meaningful modularity loss, yielding 2
## Θ(푛)
distinct near-optimal partitions.
Step 3: Sparsity makes this severe. When
## ̄
푘<3, standard re-
sults on Poisson and power-law degree distributions guarantee that
## 푛
## ≤d
=Θ(푛). This is the regime of knowledge graphs in GraphRAG.
In contrast, for dense graphs with large
## ̄
## 푘,푛
## ≤d
/푛 →0 and most
nodes are strongly coupled to their communities, collapsing the
degeneracy.
Full proof.
Proof.We first remind modularity in its standard community-
sum form:
## 푄(휎)=
## ∑︁
## 푐
## "
## 푒
## 푐
## 푚
## −
## 
## 퐾
## 푐
## 2푚
## 
## 2
## #
## ,
where푒
## 푐
counts edges internal to community푐and퐾
## 푐
## =
## Í
## 푗∈푐
## 푘
## 푗
is its total degree. Moving node푖from community푠to community
푟produces a new partition휎
## 푖→푟
. We write푑
## (푐)
## 푖
for the number
of neighbors of푖in community푐. We also define the modularity
sensitivity of node푖under partition휎isΔ
## 푖
(휎)= max
## 푟≠휎
## 푖
## |푄(휎)−
## 푄(휎
## 푖→푟
## )|
, where휎
## 푖→푟
moves푖to community푟with all other as-
signments fixed. Node 푖 is 휀-weakly coupled ifΔ
## 푖
## (휎)< 휀.
Next, we give two lemmas that will help with the proof
Lemma 2 (Moving a low-degree node). For any partition휎
and any node푖with degree푘
## 푖
≤ 푑, moving푖to any other community
changes modularity by at most
## Δ
## 푖
## (휎) ≤
## 2푘
## 푖
## 푚
## +
## 푘
## 2
## 푖
## 2푚
## 2
## = 푂
## 
## 1
## 푛
## 
## .
Proof.Moving푖from community푠to푟affects only those two
terms in the sum. There are two contributions:
Edge term. Community푠loses푑
## (푠)
## 푖
internal edges;푟gains푑
## (푟)
## 푖
## . Both
are at most 푘
## 푖
, so
## |Δ
edge
## |=
## |푑
## (푟)
## 푖
## −푑
## (푠)
## 푖
## |
## 푚
## ≤
## 푘
## 푖
## 푚
## .
Degree-penalty term. The total degree of푠drops by푘
## 푖
and that of푟
rises by 푘
## 푖
. Expanding the squares and simplifying:
## |Δ
penalty
## |=
## |푘
## 푖
## [2(퐾
## 푟
## − 퐾
## 푠
## )+ 2푘
## 푖
## ]|
## (2푚)
## 2
## ≤
## 푘
## 푖
## 푚
## +
## 푘
## 2
## 푖
## 2푚
## 2
## ,
using|퐾
## 푟
## − 퐾
## 푠
## | ≤ 2푚.
Adding the two and substituting푘
## 푖
## ≤ 푑and푚= 푛
## ̄
푘/2=Θ(푛)gives
## Δ
## 푖
## ≤ 2푑/푚+푑
## 2
## /(2푚
## 2
). Both terms are 푂(1/푛).□
Lemma 3 (Non-adjacent low-degree nodes). Let푖, 푗be non-
adjacent nodes with degrees≤ 푑. Reassigning푗changes node푖’s
sensitivity by at most
## |Δ
## 푖
## (휎)−Δ
## 푖
## (휎
## ′
## )| ≤
## 2푑
## 2
## (2푚)
## 2
## = 푂
## 
## 1
## 푛
## 2
## 
## .
Proof.Since푖and푗share  no  edge,  reassigning푗does  not
change푖’s neighbor counts푑
## (푐)
## 푖
in any community, so the edge
term for푖is unaffected. The only effect is that푗’s move shifts the
total degrees퐾
## 푟
## ,퐾
## 푠
by±푘
## 푗
≤ 푑, which perturbs푖’s penalty term by
at most 푘
## 푖
## · 2푑/(2푚)
## 2
## ≤ 2푑
## 2
## /(2푚)
## 2
## =푂(1/푛
## 2
## ).□
Now, we give the proof of Theorem 1. The argument has three
parts.
- Find a large independent set of weakly coupled nodes. By
Lemma 2, every node with푘
## 푖
≤ 푑has sensitivity푂(1/푛), so for
## 휀> 푑(2+
## ̄
푘)/(2푚)it is휀-weakly coupled. Let푛
## ≤푑
denote the number
of such nodes. The subgraph they induce has maximum degree푑,
so a greedy algorithm yields an independent set 푆 of size
## |푆| ≥
## 푛
## ≤푑
## 푑+ 1
## .
- Every combination of reassignments stays near-optimal.
Start from an optimal partition휎
## ∗
. Each node푖 ∈ 푆can stay or
move to an alternative community: two choices per node. For any
subset푇 ⊆ 푆of nodes that are reassigned, the total modularity loss
is bounded by summing the individual sensitivities plus pairwise
cross-terms (using Lemma 3):
## |푄
## ∗
## −푄(휎
## 푇
## )| ≤
## ∑︁
## 푖∈푇
## Δ
## 푖
## (휎
## ∗
## )
## |      {z      }
individual
## +
## ∑︁
## {푖,푗}⊆푇
## 2푑
## 2
## (2푚)
## 2
## |          {z          }
cross-terms
## .
Bounding each sum with|푇| ≤ |푆| ≤ 푛
## ≤푑
/(푑+ 1) and푚= 푛
## ̄
## 푘/2:
Individual sum≤
## 푛
## ≤푑
## 푑+ 1
## ·
## 푑(2+
## ̄
## 푘)
## 푛
## ̄
## 푘
## ≤
## 푑(2+
## ̄
## 푘)
## (푑+ 1)
## ̄
## 푘
## =
## :
## 퐶
## 1
## ,
Cross-term sum≤
## 1
## 2
## 
## 푛
## ≤푑
## 푑+ 1
## 
## 2
## ·
## 2푑
## 2
## 푛
## 2
## ̄
## 푘
## 2
## ≤
## 푑
## 2
## (푑+ 1)
## 2
## ̄
## 푘
## 2
## =
## :
## 퐶
## 2
## .
## Both퐶
## 1
and퐶
## 2
are constants (independent of푛), so setting휀
## ′
## =
## 퐶
## 1
## +퐶
## 2
keeps every such partition within 휀
## ′
of 푄
## ∗
## .
- Count and conclude. Each of the|푆|nodes has two valid as-
signments, giving 2
## |푆|
structurally distinct near-optimal partitions:
## D(휀
## ′
## ) ≥  2
## |푆|
## ≥  2
## 푛
## ≤푑
## /(푑+1)
## .
In the sparse regime (
## ̄
푘<3), standard degree distributions guar-
antee푛
## ≤푑
=Θ(푛). For example, under a Poisson distribution with
## ̄
푘=2 and푑=2, the fraction of low-degree nodes is 5푒
## −2
## ≈0.68;
under a power law with exponent훾=2.5, degree-1 nodes alone
comprise∼74% of the graph. ThereforeD(휀
## ′
## ) ≥ 2
## Θ(푛)
## .□

Core-based Hierarchies for Efficient GraphRAG
## B  Splitting Oversized Components
B.1  SPLIT: Splitting Large Connected
## Components
When a connected component푅exceeds the maximum cluster size
푀, it is split into smaller clusters using the Split procedure. The
algorithm (Algorithm 3) grows each cluster greedily from a seed
node with the highest degree (line 3), adding neighboring nodes
that maximize internal connectivity (line 6) until the cluster reaches
size푀. Each completed cluster is added to the cluster set (line 10)
and removed from the remaining node set (line 11). The output is a
set of size-constrained clusters that preserve internal connectivity
within퐶.
Algorithm 3: Split (G, R, M)
Require:  Graph 퐺=(푉,퐸), connected comp. 푅, max size 푀
Ensure:  List of split clustersC
1:  Initialize cluster setC ←∅
2: while 푅≠∅ do
3:Pick seed node 푠 ∈ 푅 with highest degree
## 4:  푆 ←{푠}, 푓푟표푛푡푖푒푟 ← 푁(푠)∩ 푅
5:   while|푆|< 푀 and 푓푟표푛푡푖푒푟≠∅ do
6:Pick 푣 ∈ 푓푟표푛푡푖푒푟 maximizing 푁(푣)∩ 푆
## 7:    푆 ← 푆∪ 푣
## 8:푓푟표푛푡푖푒푟 ← 푁(푣)∩(푅\ 푆)
9:   end while
## 10: C ←C∪ 푆
11:Remove 푆 from 푅
12: end while
13: return C
B.2  SPLIT-2HOP: Splitting Large 2-Hop
## Connected Components
When a 2-hop connected component퐻exceeds the maximum
cluster size푀, it is partitioned into smaller clusters using the Split-
2HOP procedure (Algorithm 4). The algorithm first computes the
anchor set as the union of neighbors of all 2-hop nodes and precom-
putes anchor neighborhoods for each node (lines 2–3). Clusters are
grown greedily by selecting a seed node with the largest anchor set
(line 5) and initializing a cluster with this seed (line 6). Candidate
nodes that share at least one anchor with the seed are added to the
frontier (line 7). The cluster is expanded by repeatedly selecting
the frontier node with the highest overlap in anchor connectivity
with the current cluster (lines 8–10), until the cluster reaches size
푀or no eligible nodes remain. After cluster growth, anchor nodes
connected to at least two nodes in the cluster are selected and in-
cluded (line 12), and the resulting cluster is added to the output set
(line 13). The assigned nodes are then removed from the remaining
2-hop groups set (line 14). This process repeats until all nodes in
the 2-hop groups are assigned.
## C  Evaluation Criteria Details
C.0.1    Question Generation.  Following methodology described in
[6], we generated 125 sensemaking questions usingGPT-5-mini.
Consistent with their approach, we first promptedGPT-5-minito
Algorithm 4: Split-2hop (G, H, M)
Require:  Graph 퐺=(푉,퐸), 2-hop groups 퐻 , max size 푀
Ensure:  List of split clustersC
1:  Initialize cluster setC ←∅
2:  Compute anchors 퐴←
## Ð
## 푢∈퐻
## 푁(푢)
## 3:  Precompute 퐴
## 푢
← 푁(푢)∩ 퐴 for푢 ∈ 퐻
4: while 퐻≠∅ do
5:Pick 푠푒푒푑 ∈ 퐻 with max|퐴
## 푠푒푒푑
## |
## 6:  푆 ←{푠푒푒푑}
## 7:  푓푟표푛푡푖푒푟 ←{푣 ∈ 퐻 \{푠푒푒푑} | 퐴
## 푣
## ∩ 퐴
## 푠푒푒푑
## ≠∅}
8:   while|푆|< 푀 and 푓푟표푛푡푖푒푟≠∅ do
9:Pick 푣 ∈ 푓푟표푛푡푖푒푟 maximizing
## Í
## 푢∈푆
## |퐴
## 푣
## ∩ 퐴
## 푢
## |
## 10:    푆 ← 푆∪{푣};
## 푓푟표푛푡푖푒푟 ← (푓푟표푛푡푖푒푟 ∪{푢 ∈ 퐻 | 퐴
## 푢
## ∩ 퐴
## 푣
## ≠∅})\ 푆
11:   end while
// Select anchors linked to ≥ 2 nodes in 푆
## 12:  퐴
## ′
## ←{푣 ∈ 퐴푠.푡.푁(푣)∩ 푆 ≥ 2}
## 13: C ←C∪{푆∪ 퐴
## ′
## }
## 14:  퐻 ← 퐻 \ 푆
15: end while
16: return C
create personas of hypothetical users for each corpus and then gen-
erated 5 tasks per user. For each user-task pair, we useGPT-5-minito
generate high-level questions that require understanding of the en-
tire corpus without relying on low-level fact retrieval. This process
ensures that the resulting questions assess comprehensive, corpus-
wide reasoning, aligned with prior work.
C.0.2    Evaluation Approach.  We evaluate models using a head-to-
head framework, where LLMs compare pairs of answers to identify
a winner, loser, or tie. To enhance reliability, multiple evaluators are
used, and repeated assessments are performed. The final outcome is
determined via majority voting, making this approach suitable for
global sensemaking tasks without gold-standard references. Each
comparison proceeds as follows:
(1)Generate answers to the same query using two approaches.
(2)Randomize answer order and present the pair to the evalu-
ator.
(3)Each of five independent LLM evaluators (GPT-5-mini,
Gemini 3 Pro Preview, Gemini 2.5 Pro, Qwen3 Next 80B,
and DeepSeek v3.2) assesses the same answer pair three
times.
(4)Apply majority voting within each evaluator to determine
their decision.
## (5)
Apply a second majority vote across evaluators to deter-
mine the final judgment.
This procedure ensures robust, repeatable head-to-head compar-
isons across methods.
## D  Statistical Analysis (p-values)
To assess the significance of observed differences, we follow a pro-
cedure similar to Edge et al. [6]. For each dataset, evaluator, and
metric, we assign scores for each head-to-head comparison: the
winning method receives a score of 100, the losing method receives
0, and in the event of a tie, both methods receive 50. These scores

Jakir Hossain and Ahmet Erdem Sarıyüce
are then averaged over all evaluators, repeated runs, and questions,
as detailed in Section 5.1. Following [6], we use non-parametric
Wilcoxon signed-rank tests to evaluate pairwise performance dif-
ferences between methods. Holm-Bonferroni adjustment is applied
to correct for multiple comparisons.
Table 7: Wilcoxon signed-rank test p-values for comparisons
across datasets and baselines on Diversity (GPT-3.5-turbo).
Significant values are highlighted in bold for 푝< 0.005.
Condition     podcastnewssemiconductor
## C2C3C2C3C2C3
RkH L10.073   <0.0010.008   <0.0010.0830.083
RkH LF<0.001  <0.001
## 0.071   <0.0010.0080.007
M2hC L1<0.001  <0.001<0.0010.007<0.0010.982
M2hC LF<0.001  <0.001
## <0.001  <0.0010.083   <0.001
## MRC L10.982   <0.001<0.0010.071<0.001  <0.001
## MRC LF0.0830.393
## 0.083   <0.001<0.001  <0.001
## C3<0.001  <0.001<0.001  <0.001<0.001  <0.001
D.1  Head-to-Head Comparison on Leiden C2
and Different M2hC Levels
Table 8 shows the head-to-head win rates (%) forGPT-3.5-turboon
microsoftdata, comparing the Leiden C2 baseline against various
M2hClevel variants. The two subtables report metrics for (a) Com-
prehensiveness and (b) Diversity.
Here, theM2hCvariants correspond to different k-core levels
within the graph hierarchy: LF represents the leaf-level communi-
ties, LF-2 corresponds to two levels above the leaf, LF-4 to four levels
above the leaf, and LF-6 to six levels above the leaf. We observe that
higher k-core levels consistently achieve better win rates against
C2, particularly in Comprehensiveness, indicating that the more
central nodes capture global context more effectively. This justifies
focusing on leaf-level (LF) and the level immediately above leaf (L1)
for all of our evaluations, as they provide better performance.
Table 8:GPT-3.5-turboHead-to-Head Win Rates (%) using
Leiden C2 and M2hC Level Variants on microsoft data
## (a) Comprehensiveness
Leiden C2M2hC LF-6M2hC LF-4M2hC LF-2M2hC LF
## Leiden C25056514839
M2hC LF-64450454333
M2hC LF-44955504640
M2hC LF-25257545047
M2hC LF6167605350
## (b) Diversity
Leiden C2M2hC LF-6M2hC LF-4M2hC LF-2M2hC LF
## Leiden C25062544639
M2hC LF-63850423836
M2hC LF-44658504941
M2hC LF-25462515051
M2hC LF6164594950
## E  Additional Results
Here, we present additional results fromGPT-3.5-turbo,GPT-4o-mini,
andGPT-5-mini, including the results from Leiden C0, C1, and
other metrics such as Empowerment and Directness.
E.1  GPT-4o-mini Results on Post-cutoff Data
Table 11 reports head-to-head win rates for comprehensiveness and
diversity under the same experimental conditions as inGPT-3.5-turbo.
Across  datasets  and  configurations,  our  heuristics  still  achieve
higher win rates than Leiden C2/C3 in a majority of comparisons,
averaging approximately 45–55%, particularly onsemiconductor.
Among our methods,M2hCLF still achieves the strongest overall
performance, with average win rates of approximately 50–52%
across datasets and metrics, followed byRkHLF andMRCLF at 48–
50%. Dataset-wise, gains are most pronounced onsemiconductor,
whereM2hCLF reaches up to 64% wins for diversity (C2) and main-
tains 58% against C3, while comprehensiveness peaks at 52%. For
podcastandnews, win rates remain closer to parity, typically fluc-
tuating between 45–50% across heuristics and Leiden levels.
Comparing Leiden resolutions, differences between C2 and C3
are smaller than forGPT-3.5-turbo, with average win-rate gaps
generally within 2–4%. Averaged across datasets and metrics, leaf-
level (LF) variants continue to outperform L1, but by a narrower
margin of 2–5 percentage points. Overall,GPT-4o-mininarrows
the gap between푘-core heuristics and Leiden GraphRAG, with
M2hCLF remaining the most robust, especially onsemiconductor,
and generally matching or slightly surpassing Leiden baselines
despite more ties.
Note that performance on thepodcastis less reliable due to the
limited number of post-cutoff documents. With only 13 documents
available, the resulting graphs are sparse, and our heuristics of-
ten show minimal improvement, performing similarly to C2/C3
configurations.
Table 9:GPT-5-minifull: Head-to-head win rates (%), for com-
prehensiveness and diversity metrics. C3 is the Leiden com-
munity level from Edge et al. [6]. LF indicates leaf-level com-
munities, and L1 indicates the level immediately above the
leaf.
GPT-5-minipodcastnewsmicrosoft
results forC3C3C3
ComprehensivenessWinLossTieWinLossTieWinLossTie
RkH L141411852399384319
RkH LF43431447458424810
M2hC L148484493714484210
M2hC LF5047347351847485
## MRC L1454510324820454015
## MRC LF503713364618454015
DiversityWinLossTieWinLossTieWinLossTie
RkH L1444412473815335314
RkH LF4845737342948448
M2hC L140421842382045487
M2hC LF48411132333552408
## MRC L147467452924533512
## MRC LF56311334303654388

Core-based Hierarchies for Efficient GraphRAG
Table 10:GPT-3.5-turbopost-cutoff: Head-to-head win rates (%), for comprehensiveness and diversity metrics. C0 and C1 are
Leiden community levels from Edge et al. [6]. LF indicates leaf-level communities, and L1 indicates the level immediately
above the leaf.
GPT-3.5-turbopodcastnewssemiconductor
results forC0C1C0C1C0C1
ComprehensivenessWinLossTieWinLossTieWinLossTieWinLossTieWinLossTieWinLossTie
RkH L150428682485632124842106630472262
RkH LF58420524444050104244146832052462
M2hC L1484666628650401050361454460622810
M2hC LF584026828444488444976038272244
## MRC L158366484845038124644105440664324
## MRC LF64360573945634106135448421055432
DiversityWinLossTieWinLossTieWinLossTieWinLossTieWinLossTieWinLossTie
RkH L1682846036460382563866238066340
RkH LF524625640448484504466236260346
M2hC L1425447028256404603466436070300
M2hC LF5248072271603826732162380523810
## MRC L1663406040050482425265244452462
## MRC LF604006535064360643606040056440
Table 11:GPT-4o-minipost-cutoff : Head-to-head win rates (%), for comprehensiveness and diversity metrics. C2 and C3 are
Leiden community levels from Edge et al. [6]. LF indicates leaf-level communities, and L1 indicates the level immediately
above the leaf.
GPT-4o-minipodcastnewssemiconductor
results forC2C3C2C3C2C3
ComprehensivenessWinLossTieWinLossTieWinLossTieWinLossTieWinLossTieWinLossTie
RkH L1505005050038422040421846468393625
RkH LF504824648640402043401752417493219
M2hC L14846648448424216444412444016513019
M2hC LF5048250464444016464212523810502426
## MRC L148448444214383626383230364222464410
## MRC LF4846646486403525403030484210444412
DiversityWinLossTieWinLossTieWinLossTieWinLossTieWinLossTieWinLossTie
RkH L15048246486474013523993854845487
RkH LF50500485025038125537847494523612
M2hC L15050050500424810444610503812493615
M2hC LF49465464864446104644106432458348
## MRC L1484844844843342346381646468454510
## MRC LF49501485204532234836165444254451
Table 12:GPT-3.5-turbopost-cutoff: Head-to-head win rates (%), for empowerment and directness metrics. C2/C3 are Leiden
community levels, LF is leaf-level communities, and L1 is the level immediately above the leaf
GPT-3.5-turbopodcastnewssemiconductor
results forC2C3C2C3C2C3
ComprehensivenessWinLossTieWinLossTieWinLossTieWinLossTieWinLossTieWinLossTie
RkH L1485025245346522633705248047521
RkH LF524355443346504574035050050500
M2hC L1544425939263352554504059153434
M2hC LF504645446046513465406138152444
## MRC L1395474055538602386025148257376
## MRC LF3656847503504010653055346159365
DirectnessWinLossTieWinLossTieWinLossTieWinLossTieWinLossTieWinLossTie
RkH L162362405010376304545103565056431
RkH LF42553355510405734842103565058411
M2hC L15444264288564405631136336153434
M2hC LF5244462317465405831116138153443
## MRC L14350750446485025928135050047530
## MRC LF5836647503485206128115050045550