

## Autonomous Knowledge Graph Exploration
with Adaptive Breadth-Depth Retrieval
## Joaquín Polonuer
## 1,2,∗
## , Lucas Vittor
## 1,∗
## , Iñaki Arango
## 1,∗
## , Ayush Noori
## 1,3,∗
## ,
## David A. Clifton
## 3,4
## , Luciano Del Corro
## 5,6,†,‡
## , Marinka Zitnik
## 1,7,8,9,†,‡
## 1
Department of Biomedical Informatics, Harvard Medical School, Boston, MA, USA
## 2
Departamento de Computación, FCEyN, Universidad de Buenos Aires, Buenos Aires, Argentina
## 3
Department of Engineering Science, University of Oxford, Oxford, UK
## 4
Oxford Suzhou Centre for Advanced Research, University of Oxford, Suzhou, Jiangsu, China
## 5
ELIAS Lab, Departamento de Ingeniería, Universidad de San Andrés, Victoria, Argentina
## 6
## Lumina Labs, Buenos Aires, Argentina
## 7
Kempner Institute for the Study of Natural and Artificial Intelligence, Allston, MA, USA
## 8
Broad Institute of MIT and Harvard, Cambridge, MA, USA
## 9
Harvard Data Science Initiative, Cambridge, MA, USA
## ∗
Equal contribution.
## †
Co-senior authors.
## ‡
Correspondence: delcorrol@udesa.edu.ar, marinka@hms.harvard.edu
## Abstract
Retrieving evidence for language model queries
from  knowledge  graphs  requires  balancing
broad search across the graph with multi-hop
traversal to follow relational links. Similarity-
based retrievers provide coverage but remain
shallow, whereas traversal-based methods rely
on  selecting  seed  nodes  to  start  exploration,
which can fail when queries span multiple enti-
ties and relations. We introduce ARK: ADAP-
TIVE RETRIEVER OF KNOWLEDGE, an agen-
tic KG retriever that gives a language model
control over this breadth-depth tradeoff using
a two-operation toolset: global lexical search
over node descriptors and one-hop neighbor-
hood exploration that composes into multi-hop
traversal.   ARK  alternates  between  breadth-
oriented discovery and depth-oriented expan-
sion without depending on a fragile seed selec-
tion, a pre-set hop depth, or requiring retrieval
training. ARK adapts tool use to queries, using
global search for language-heavy queries and
neighborhood  exploration  for  relation-heavy
queries. On STaRK, ARK reaches 59.1% aver-
age Hit@1 and 67.4 average MRR, improving
average Hit@1 by up to 31.4% and average
MRR by up to 28.0% over retrieval-based and
agentic training-free methods. Finally, we dis-
till ARK’s tool-use trajectories from a large
teacher into an 8B model via label-free imi-
tation, improving Hit@1 by +7.0, +26.6, and
+13.5 absolute points over the base 8B model
on AMAZON, MAG, and PRIME datasets, re-
spectively, while retaining up to 98.5% of the
teacher’s Hit@1 rate.
## 1  Introduction
Large language models rely on knowledge retrieval
to ground and align their outputs in external evi-
dence (Ren et al., 2025; Wang et al., 2025a; Xia
et al., 2025a; Zhang et al., 2024), from retrieval-
augmented generation (RAG) to systems and mem-
ory  modules  that  operate  over  semi-structured
knowledge bases (SKB) that mix text with rela-
tional information (Lewis et al., 2020; Guu et al.,
2020; Karpukhin et al., 2020; Izacard and Grave,
2021; Mavromatis and Karypis, 2025; Chen et al.,
2025; Li et al., 2025c). Knowledge graphs (KGs)
are a natural data representation for this setting be-
cause they organize evidence around entities and
typed edges, support reuse across queries, and en-
force relational constraints that a flat text index
cannot express.  This has motivated graph-aware
retrievers and graph-grounded generation methods,
including graph-based RAG and SKB retrievers
that combine text and relational data (Edge et al.,
2025; Zhu et al., 2025b; Xia et al., 2025b; Yao
et al., 2025; Jeong et al., 2025).
Retrieving evidence from KGs is challenging
because  it  requires  coordinating  two  competing
search modes (Wu et al., 2024b; Lee et al., 2025;
Zhu et al., 2025a). Many queries require breadth:
they mention multiple entities or loosely connected
concepts,  so  the  retriever  must  cover  the  graph
broadly to reach the right region. Other queries re-
quire depth: the supporting evidence only appears
after following specific multi-hop relational paths.
Similarity-based retrievers provide global coverage
## 1
arXiv:2601.13969v1  [cs.AI]  20 Jan 2026




























































































Figure 1: Overview of ADAPTIVE RETRIEVER OF KNOWLEDGE. ARK interacts with a KG through a minimal
two-tool interface: (a) For text-dominant queries, ARK emphasizes breadth by issuing GLOBAL SEARCH to retrieve
a broad set of candidates. (b) For relation-focused queries, ARK applies NEIGHBORHOOD EXPLORATION starting
from a previously retrieved node (in this case, a drug) and expanding to related entities, enabling targeted relational
retrieval. (c) For relation-dominant queries, ARK performs multi-hop retrieval by alternating GLOBAL SEARCH
and NEIGHBORHOOD EXPLORATION: it retrieves an initial node (e.g., an article), expands to related entities (e.g.,
co-authors), and continues expanding and filtering (e.g., papers connected to each author that match query keywords)
to recover an ordered set of relevant evidence.
but often remain shallow and underuse relational
structure, whereas traversal-based methods can be
brittle because they must choose seed entities to
start exploration; when seeds are incomplete or am-
biguous, the search stays local and misses evidence
elsewhere.
Existing  work  tackles  these  breadth-depth  re-
quirements  in  isolation  rather  than  jointly  (Ko
et al., 2025; Ma et al., 2025; Wang et al., 2025b).
Structure-aware  retrievers  extend  text-based  re-
trieval with relational structure, for example, by
learning node embeddings that aggregate informa-
tion from nearby neighbors or by generating can-
didates using a local graph neighborhood before
ranking them (Lee et al., 2025; Zhu et al., 2025b;
Lei  et  al.,  2025).   These  methods  capture  local
structure, but they typically encode a fixed neigh-
borhood around each node, so deeper multi-hop
queries require expanding the encoded context or
stacking additional message-passing and retrieval
stages, which increases complexity and cost (Wan
et al., 2025; Hu et al., 2025a; Verma et al., 2024).
By contrast, traversal-based approaches perform
multi-hop exploration, but they depend on identify-
ing a small set of seed entities from which explo-
ration begins (Markowitz et al., 2024; Sun et al.,
2024). When seeds are incomplete or ambiguous,
exploration stays local and misses relevant infor-
mation elsewhere in the graph (Liu et al., 2025; Ma
et al., 2025).  Many systems also rely on task- or
graph-specific training to learn traversal or scoring
policies, which limits transfer across domains and
graph schemas (Li et al., 2025a; Lei et al., 2025;
Wu et al., 2024a; Yu et al., 2025). As a result, exist-
ing methods struggle to combine global search with
targeted relational reasoning for adaptive retrieval.
Present work. We introduce ARK: ADAPTIVE
RETRIEVER OF KNOWLEDGE, an agentic KG re-
triever that gives a language model control over
evidence discovery using a minimal set of tools
for global lexical search and neighborhood explo-
ration (Yao et al., 2023; Schick et al., 2023). ARK
does not require selecting seed entities to start ex-
ploration or establishing a maximum hop depth
in advance; instead, the model alternates between
broad global search and targeted multi-hop traver-
sal based on the query and what it has retrieved so
far. We evaluate ARK on the heterogeneous graphs
in the STaRK retrieval benchmark and show con-
sistent gains across all settings. We further study
## 2

compute-accuracy tradeoffs by varying the tool-call
budget and the number of parallel agents, and we
distill ARK’s tool-use policy into an 8B model via
label-free trajectory imitation, preserving most of
the performance of teacher model at substantially
lower inference cost (Kang et al., 2025).
Our contributions are threefold.   (i) We intro-
duce ADAPTIVE RETRIEVER OF KNOWLEDGE, a
training-free retrieval framework that equips lan-
guage models with a minimal but expressive tool
interface for adaptive retrieval from KGs. (ii) We
show that ARK balances breadth-oriented retrieval
with  depth-oriented  multi-hop  traversal  without
task- or graph-specific training, achieving strong
performance on STaRK. (iii) We distill ARK’s tool-
use policy without labeled supervision into a com-
pact Qwen3-8B model (Yang et al., 2025a; Kang
et al., 2025), preserving retrieval quality while re-
ducing inference cost.
## 2  Related Work
Knowledge graphs for document-centric RAG.
Retrieval-augmented generation (RAG) grounds
LLM outputs in external evidence by retrieving rel-
evant context from a corpus or index (Lewis et al.,
2020; Guu et al., 2020). Recent work injects struc-
ture by building graphs over textual units and using
connectivity to aggregate evidence.   GraphRAG
performs local-to-global retrieval over an entity-
centric graph (Edge et al., 2025), while KG-guided
methods steer evidence selection using external re-
lations (Zhu et al., 2025b).   Related approaches
retrieve  textual  subgraphs  to  support  multi-hop
queries under context limits (Hu et al., 2025b; He
et al., 2024; Li et al., 2025b).  These approaches
primarily focus on improving how textual evidence
is organized or aggregated, but the retrieval process
itself is typically static.
Retrieval over semi-structured knowledge bases.
Complementary to document-centric graph indices,
semi-structured knowledge base (SKB) retrievers
directly combine text and explicit relations. KAR
grounds query expansion in KG structure (Xia et al.,
2025b),  and hybrid systems mix graph and text
channels  with  iterative  refinement,  e.g.,  Graph-
Search and HybGRAG (Yang et al., 2025b; Lee
et al., 2025); CoRAG highlights cooperative hy-
brid retrieval that preserves global semantic access
beyond local neighborhoods (Zheng et al., 2025).
In parallel, parametric retrievers such as MoR and
mFAR learn to fuse lexical, semantic, and struc-
tural signals for ranking (Lei et al., 2025; Li et al.,
2025a). Across these variants, retrieval is framed
as scoring candidates from a static index. ARK dif-
fers in that retrieval is formulated as an interactive
process: the model dynamically switches between
global search and neighborhood expansion, guided
by the query requirements and without relying on
task-specific supervision.
Agents for multi-hop KG retrieval and QA. A
separate  line  of  work  treats  the  KG  as  an  envi-
ronment for iterative interaction.   Earlier agents
follow relation paths using reinforcement learning
or learned policies (Das et al., 2018; Xiong et al.,
2017; Sun et al., 2019; Asai et al., 2020).  In the
LLM era, tool-use frameworks such as ReAct (Yao
et al., 2023) and prompt-optimization methods such
as AvaTaR (Wu et al., 2024a) enable interactive
evidence gathering.  Within KG retrieval, recent
traversal-based approaches expand from seed enti-
ties using prompted heuristics or learned policies,
including Tree-of-Traversals, Think-on-Graph, and
GraphFlow  (Markowitz  et  al.,  2024;  Sun  et  al.,
2024; Yu et al., 2025; Ma et al., 2025);  related
KG-grounded reasoning methods also emphasize
multi-step planning or navigation on the KG (Luo
et  al.,  2024;  Sun  et  al.,  2025).   Traversal-based
agents are effective when the correct starting en-
tities are known, but they are prone to anchoring
errors and can over-commit to local neighborhoods
once exploration begins.  In ARK, global search
remains available throughout the trajectory, allow-
ing the agent to retain a complete view of the KG
at each step. This design enables coordination be-
tween global discovery and deep multi-hop expan-
sion within a single retrieval process.
Existing work varies in whether it treats retrieval
as  static ranking  over  an  index or  as  sequential
decision-making on the graph, and in whether it
requires graph-specific supervision to learn a rank-
ing function or a traversal policy. ARK adapts its
search strategy online through a minimal, graph-
native  tool  interface.    It  is  training-free;  when
needed, its tool-use policy can be distilled into com-
pact models from interaction trajectories without
ground-truth relevance labels, improving efficiency
while preserving retrieval quality.
3  Adaptive Retriever of Knowledge
We   study   retrieval   over   a   knowledge   graph
G = ⟨V,E,φ
## V
## ,φ
## E
## ,d
## V
## ⟩
, whereVandEdenote
entities and edges,φ
## V
andφ
## E
assign a type to
## 3

each node and relation, andd
## V
(v)denotes the text
attributes associated with nodev,  such as titles,
descriptions, or other metadata.  Given a natural-
language queryQ, retrieval is formulated as an in-
teractive process in which an agentA =⟨LLM,T⟩
queries the graph through a tool interfaceT(Yao
et al., 2023; Schick et al., 2023) and produces a tra-
jectoryτ =
##  
## (s
## 1
## ,A
## 1
## ,o
## 1
## ),..., (s
## T
## ,A
## T
## ,o
## T
## )
## 
## .  At
stept,s
t
containsQand the interaction history,
## A
t
is a sequence of tool invocations, ando
t
is the
observation returned after executing A
t
## .
Throughout the trajectory, the agent maintains
an ordered list of retrieved nodesR. At each step,
it can SELECT nodes returned by tools and append
them  toR,  or  terminate  by  issuing  a  dedicated
FINISH  action.   Execution ends either when the
agent calls FINISH or when the maximum trajectory
lengthT
max
is reached. The final retrieval output
is the ranked listR = (v
## 1
## ,v
## 2
,... ), where earlier
selections receive higher rank.
To rank candidate nodes returned by tools, we
use a relevance functionrel(q,d
## V
(v))∈R
## ≥0
that
scores nodevfor a textual subqueryqprovided
by the agent as a tool parameter.  We implement
relwith BM25 (Robertson and Zaragoza, 2009)
over an inverted index of node textual attributes
(Manning  et  al.,  2008),  yielding  fast  and  stable
scoring for the many short, evolving subqueries
issued during exploration.
## 3.1  Tools
We  implement  the  interaction  described  above
through a small set of retrieval tools.  Each tool
returns a candidate set of nodes, which the agent
may append toRor use to guide subsequent steps.
Global search  retrieves  thekhighest-scoring
nodes in the graph underrelfor an agent-issued
subquery q, as shown in Figure 1a:
## Search
## G
## (q,k) := Top-k
v∈V
rel(q,d
## V
## (v))
This tool provides broad entry points into the graph
and is primarily used (i) to locate entities related
to the user queryQ, which will then be used for
further exploration, and (ii) to handle cases where
direct  text  matching  suffices  without  requiring
multi-hop reasoning.
Neighborhood exploration returns adjacent nodes
of a nodevfiltered by optional node and edge type
constraintsF := (F
## V
## ,F
## E
## )
selected by the agent
as tool parameters, and optionally ranked using an
agent-generated subquery q (Figure 1b).
The filtered one-hop neighborhoodN
## F
of a node
v is defined as:
## N
## F
## (v) :=
## (
u∈ N(v)





φ
## V
## (u)∈ F
## V
## ,
φ
## E
## ({u,v})∈ F
## E
## )
whereN(v)denotes the open neighborhood of
vand{u,v}denotes the edge connectingvand
u, regardless of direction. Edge directionality and
relation types are exposed in the tool output.  To
control the size of the retrieved neighborhood, we
introduce a fixed retrieval budget k ∈N:
Neighbors(v,q,F) := Top-k
u∈N
## F
## (v)
rel(q,d
## V
## (u))
We restrictNeighborsto single-hop expansion
so  that  multi-hop  exploration  emerges  through
composition rather than fixed-depth traversal (Fig-
ure 1c).
## 3.2  Parallel Exploration
We increase robustness by runningnindependent
instances of the same agent in parallel and aggre-
gating their retrieved lists, akin to self-consistency
and voting-based ensembling in LLM reasoning
(Wang et al., 2023; Kaesberg et al., 2025).  Each
agent produces an ordered list of retrieved nodes
## R
## (i)
## = (v
## (i)
## 1
## ,v
## (i)
## 2
,... )from an independent trajec-
tory.  We then combine these lists using a simple
rank-fusion rule inspired by classical rank aggre-
gation and data fusion methods (Fagin et al., 2003;
Cormack et al., 2009).
Concretely, we concatenate the per-agent lists in
agent order to form:
## L := R
## (1)
## ∥R
## (2)
## ∥ ··· ∥R
## (n)
## ,
and letV
## L
be the set of unique nodes inL. The final
rankingRorders nodes by decreasing frequency in
L(vote count), breaking ties by the earliest position
at which a node appears in any trajectory, favoring
nodes discovered earlier during exploration.
## 3.3  Agent Distillation
While ARK operates on off-the-shelf models, its
behavior can be distilled into a smaller language
model to reduce inference cost and latency (Hinton
et al., 2015). We adopt a standard teacher–student
paradigm in which a student model imitates the
## 4

tool-usage trajectories of a stronger teacher LLM
via supervised fine-tuning (Schick et al., 2023).
Trajectory generation. For each training queryQ
on a given graphG, we run the teacher agent to
collect trajectoriesτas defined in Section 3. Each
trajectory contains the full interaction record: the
agent’s tool calls and parameters interleaved with
the resulting tool observations.
Training objective.  The student is trained with
next-token prediction on the collected trajectories
(Ouyang  et  al.,  2022).    We  compute  loss  only
on assistant-authored tokens; user messages and
tool outputs are masked (Huerta-Enochian and Ko,
2024; Shi et al., 2024).  This trains the student to
reproduce the teacher’s decisions, which tools to
invoke and how to parameterize them, while tool
execution remains external to the model.
Label-free supervision. Importantly, distillation
does not require ground-truth evidence nodes for
queries. Supervision is derived solely from teacher
trajectories, making the approach applicable in real-
istic settings where relevance labels are unavailable:
one can run a strong teacher to generate trajectories
on a target graph and then fine-tune a smaller model
directly from these interactions (Schick et al., 2023;
Kang et al., 2025).
## 4  Experimental Setup
We measure retrieval performance on STaRK, a
benchmark for entity-level retrieval over heteroge-
neous, text-rich KGs (Wu et al., 2024b).
## 4.1  Benchmark
STaRK   comprises   three   large,   heterogeneous
knowledge graphs. AMAZON is an e-commerce
graph with roughly 1M entities and 9.4M relations,
constructed from Amazon metadata, reviews (He
and McAuley, 2016), and question–answer pairs
(McAuley et al., 2015). MAG is a scholarly graph
with  1.9M  entities  and  39.8M  relations  derived
from the Microsoft Academic Graph (Wang et al.,
2020). PRIME is a biomedical graph built from
PrimeKG (Chandak et al., 2023), containing 129K
entities and 8.1M relations. Each node is associated
with text-rich attributes, making STaRK a natural
testbed for hybrid retrieval over structured and tex-
tual signals. Given a query, the retriever must return
a ranked list of nodes that support the answer. We
report the agent configuration and hyperparameters
in Appendix A.2.
4.2  Baselines and metrics
We compare with representative retrieval-based and
agent-based baselines, focusing on methods that
report results on all three graphs, as our goal is to
evaluate performance consistently across different
regimes and assess generality.
Retrieval-based. BM25 (Robertson and Zaragoza,
2009) is the same sparse, lexical retriever used for
global search. We also include dense embedding re-
trievers that rank nodes by cosine similarity, using
ada-002 and GritLM-7B, an instruction-tuned 7B
encoder (Muennighoff et al., 2025). mFAR (Li
et  al.,  2025a)  is  a  multi-field  adaptive  retriever
that combines keyword matching with embedding
similarity to learn query-dependent weights over
different  node  fields.  KAR  (Xia  et  al.,  2025b)
augments  queries  with  knowledge-aware  expan-
sions and applies relation-type constraints during
retrieval. MoR (Lei et al., 2025) is a trained re-
triever that combines multiple retrieval objectives.
Agent-based. Think-on-Graph (Sun et al., 2024)
is a training-free LLM agent that iteratively ex-
pands  paths  in  the  graph  using  beam  search.
GraphFlow (Yu et al., 2025) learns a policy for
generating  multi-hop  retrieval  trajectories  using
GFlowNets (Bengio et al., 2021). AvaTaR (Wu
et al., 2024a) is a tool-using agent that optimizes
prompting from positive and negative trajectories.
Results for KAR, mFAR, MoR, AvaTaR, and
GraphFlow are reported as in their respective pa-
pers, which evaluate on the official STaRK splits
and metrics.  For Think-on-Graph, we report the
numbers provided in the GraphFlow study, which
includes a direct comparison to Think-on-Graph
under the same STaRK setup (Yu et al., 2025; Sun
et al., 2024).
Metrics. We follow the STaRK protocol and report
Hit@1,  Hit@5,  Recall@20  (R@20),  and  Mean
Reciprocal Rank (MRR), which capture top-rank
precision,  coverage of the ground-truth set,  and
overall ranking quality. Note that Hit@5 is reported
in Table 5 in the Appendix.
## 4.3  Distillation Setup
For each graph, we collect teacher trajectories on
the  training  split  to  distill  ARK  into  a  smaller,
lower-cost model (Section 3.3), offering a viable
alternative when under tighter compute budgets.
Using GPT-4.1 as the teacher, we run ARK three
times per training query with stochastic decoding
(temperature= 0.7), producing three trajectories
## 5

AMAZONMAGPRIMEAverage
CategoryMethodHit@1R@20MRRHit@1R@20MRRHit@1R@20MRRHit@1R@20MRR
## Training-free
## Retrieval-based
## BM2544.9453.7755.3025.8545.6934.9112.7531.2519.8427.8543.5736.68
ada-00239.1653.2950.3529.0848.3638.6212.6336.0021.4126.9645.8836.79
GritLM-7B42.0856.5253.4637.9046.4047.2515.5739.0924.1131.8547.3441.61
## KAR54.20
## 57.2461.2950.4760.2857.5130.3550.8139.2245.0156.1152.67
## Agent-based
Think-on-Graph + GPT-4o20.6725.8130.9023.3348.0336.3816.6754.3527.0220.2242.7331.43
Think-on-Graph + LLaMA34.212.615.2512.006.7712.6721.9233.8426.6112.7114.4114.84
## ARK
## 55.8260.6164.7773.4084.4779.8748.2069.4657.6859.1471.5167.44
ARK + GPT-4o
## 55.1357.1864.2967.0179.7975.4636.0160.1346.4452.7265.7062.06
Requires training
on target graph
## Retrieval-based
mFAR53.066.364.355.974.164.340.072.652.049.6371.0060.20
MoR52.1959.9262.24
## 58.1975.0167.1436.4163.4846.9248.9366.1458.77
## Agent-based
GraphFlow47.8536.1555.4939.0957.1847.8251.3979.7161.3746.1157.6854.89
AvaTaR49.9060.6058.7044.3650.6351.1518.4039.3026.7337.5550.1845.53
ARK distilled
## 54.9960.3164.2461.6681.3970.0931.8757.2241.0849.5166.3158.47
Table 1:  Retrieval performance on STaRK synthetic test sets.Dark greenandlight greenindicate best and
second-best in the training-free category, respectively.Dark blueandlight blueindicate best and second-best in
the requires-training category, respectively. Bold indicates the best result overall for each metric column.
per query.  We cap the distillation budget by sub-
sampling up to 6,000 training queries per graph,
yielding at most 18,000 trajectories per graph (full
statistics in Table 3) and summing to 94.4 million
tokens. Each trajectory is limited toT
max
## =20steps
and ends when the agent issues FINISH or reaches
the step limit.  We apply no trajectory filtering or
rejection sampling, preserving a label-free setting.
We then distill a Qwen3-8B (Yang et al., 2025a) stu-
dent via supervised fine-tuning with LoRA adapters
(Hu et al., 2021), using next-token prediction over
assistant-authored tokens only.  We train for one
epoch with a 16,384-token context length using
AdamW (Loshchilov and Hutter, 2019) at learning
rate1× 10
## −5
, selecting checkpoints via early stop-
ping on the official validation split. Training runs
on a single NVIDIA H100 GPU and completes in
approximately five hours.
## 5  Results
## 5.1  Benchmarking
Table 1 reports retrieval performance on STaRK,
grouped by training regime.  Across all methods
assessed, ARK achieves the best average perfor-
mance.
Classical retrievers remain strong baselines on
AMAZON, when queries are predominantly de-
scriptive.  By incorporating local structural cues,
KAR improves over lexical methods, but its shal-
low neighborhood expansion is limited on multi-
hop queries (Xia et al., 2025b).
Think-on-Graph and GraphFlow highlight the
benefits of multi-hop traversal,  performing well
on PRIME. Think-on-Graph is appealing due to
its training-free setup, and GraphFlow shows that
strong performance can be achieved with smaller
backbones through reinforcement learning. How-
ever,  both  degrade  on  AMAZON’s  text-heavy,
broad queries, as they lack global search primitives
and can be sensitive to brittle anchoring and entity
identification (Sun et al., 2024; Yu et al., 2025).
ARK performs consistently across regimes and
is especially strong on MAG. This pattern aligns
with its tool design. Global search offers a reliable
anchor for text-heavy queries and supports strong
top-rank accuracy on AMAZON. Typed,  query-
ranked one-hop expansion enables controlled multi-
hop evidence gathering in relational settings, con-
tributing to the best results on MAG and solid per-
formance on PRIME, where it is surpassed only by
the RL-trained GraphFlow.
While ARK uses a large backbone, the distilled
variant preserves most of these gains with a sub-
stantially smaller Qwen3-8B model via label-free
trajectory imitation (Section 5.5).
5.2  Text vs. Relational Adaptive Retrieval
STaRK reports, for each graph, the average share of
queries that are primarily textual versus primarily
relational (multi-hop) (Fig. 5 in Wu et al. (2024b)).
We use these proportions as a reference and com-
pare them to  ARK’s tool-call allocation on our
evaluation split. Concretely, we treat the fraction
of global search calls as a proxy for text-centric
evidence use and the fraction of neighborhood ex-
ploration calls as a proxy for relation-centric evi-
dence.  Figure 2 shows a proportional match:  on
## 6

## 0%20%40%60%80%100%
## AMAZON
## MAG
## PRIME
## 87.7%12.3%
## 34.7%65.3%
## 47.7%52.3%
STaRK: Textual
## Tool: Global Search
STaRK: Relational
## Tool: Neighborhood Exploration
Figure 2: Thin bars show the share of text- vs. relation-
centric queries in STaRK; thick bars show ARK’s tool-
call use. These STaRK annotations are not provided to
ARK; instead, ARK autonomously shifts tool use to
match the dominant query type.
AMAZON, where queries are mostly textual, ARK
relies  almost  entirely  on  global  search  (87.7%),
whereas on MAG and PRIME, where relational
requirements dominate, ARK shifts toward neigh-
borhood exploration to traverse multi-hop evidence
(65.3%  and  52.3%,  respectively).   This  finding
shows that ARK  autonomously adapts retrieval,
choosing tools to match what each query needs
rather than following a fixed retrieval recipe.
5.3  Impact of Toolset Design
We conduct various ablation studies to assess the
impact of toolset design choices. Table 2 demon-
strates that neighborhood exploration is the main
source of gains on relational, multi-hop queries. Re-
moving this tool decreases performance on MAG
and PRIME as the system is then limited to global
lexical search without graph traversal. On AMA-
ZON,  performance  drops  more  moderately  and
moves toward lexical baselines (Table 1).
SetupAMAZONMAGPRIME
Hit@1R@20Hit@1R@20Hit@1R@20
## Full58.5    60.2    79.2    83.3    49.2    73.3
w/o Neighbors54.555.430.539.423.140.5
Neighbors w/o q56.057.972.179.844.768.3
Neighbors w/o F55.559.979.284.842.265.0
Table 2:  Impact of toolset design on retrieval perfor-
mance across graphs.  w/oNeighborsremoves neigh-
borhood  exploration  entirely.Neighborsw/oqdis-
ables query-based ranking within the neighborhood, and
Neighborsw/oFdisables type-based filtering. Results
are reported on a random 10% subset of the test split.
We  further  separate  two  complementary  con-
trols in neighborhood exploration. Disabling query-
based ranking causes smaller but consistent drops,
suggesting  that  lexical  matching  within  a  local
neighborhood helps surface relevant neighbors and
prevents drift toward high-degree distractors. Dis-
abling type-based filtering is more detrimental, es-
pecially in heterogeneous graphs such as PRIME
(Table 4). In such environments, type constraints
are important to direct the agent towards semanti-
cally relevant edges and nodes, preventing search
from drifting into unrelated parts of the graph.
Note that we do not ablate global search because
it is required: it maps query text to candidate nodes
and provides the node identifiers needed to start
neighborhood expansion.  Without this initial an-
chor, the agent cannot reliably enter the right part
of the graph, so the system fails outright.
5.4  Compute-Performance Trade-offs
We next study how retrieval quality scales with
the inference-time budget.   Figure 3 shows that
performance improves monotonically as compute
increases, moving from single-agent settings to par-
allel multi-agent configurations. Additional com-
pute helps most on queries that require multi-hop
expansion, and yields smaller gains when global
lexical search is already sufficient.
Parallelization yields performance benefits with
minimal  overhead.   Increasing  the  agent  count–
particularly the transition from one to two agents–
results in substantial gains while only modestly in-
creasing latency. Because agents run independently,
end-to-end latency is determined by the bottleneck
of the slowest agent rather than the cumulative run-
time of all agents.
ARKprovidesaninterpretablebudget-
performance  landscape.   Practitioners  can  fix  a
latency or compute budget and choose an operating
point in Figure 3 that matches their needs, trading
off depth and parallelism to balance quality and
cost across graph regimes.
5.5  Impact of Distillation
We also study how the distillation budget affects
final performance. Figure 4 compares Qwen3-4B
and Qwen3-8B students trained on increasing num-
bers of teacher trajectories across the three STaRK
graphs; full results for all metrics are in Table 5.
Distillation is data-efficient:  using 10% of the
trajectories recovers roughly half of the total im-
provement achieved with the full training set. This
makes distillation practical when collecting trajec-
tories is costly.   In our setup,  distilling the 600-
query setting can be done in 30 minutes on a single
## H100 GPU.
## 7

1 agent
2 agents
3 agents
## Hit@1
## 51.254.155.055.355.4
## 54.055.355.655.655.6
## 55.055.956.055.955.8
## AMAZON
## 46.959.066.268.969.4
## 53.565.070.471.972.1
## 56.767.471.773.173.4
## MAG
## 25.836.141.543.844.1
## 31.641.445.146.046.1
## 34.443.947.348.048.3
## PRIME
1 agent
2 agents
3 agents
## Recall@20
## 50.253.154.054.554.6
## 56.358.258.858.858.8
## 58.860.260.660.660.6
## 51.564.671.774.775.2
## 60.172.979.181.381.7
## 64.277.082.383.984.3
## 36.248.955.057.658.1
## 45.558.363.465.365.7
## 49.962.667.069.069.3
## 57101520
1 agent
2 agents
3 agents
## Latency (s)
## 7.707.907.988.028.04
## 8.738.999.129.179.19
## 9.229.529.679.749.76
## 57101520
## 6.867.938.789.089.14
## 9.0410.2711.2111.6311.76
## 9.7211.9912.9813.4813.63
## 57101520
## 7.168.349.129.679.85
## 8.289.6910.6711.3711.69
## 8.9410.4011.4812.3312.74
## 0.52
## 0.54
## 0.56
## 0.5
## 0.6
## 0.7
## 0.3
## 0.4
## 0.55
## 0.60
## 0.6
## 0.7
## 0.8
## 0.4
## 0.5
## 0.6
## 8
## 9
## 8
## 10
## 12
## 8
## 10
## 12
Number of steps (T
max
## )
Figure 3: Retrieval quality and latency as a function of inference-time budget. Heatmaps report Hit@1, Recall@20,
and end-to-end latency (seconds) on each STaRK graph. Moving from the top left (shallow trajectories, single agent)
to the bottom right (deeper trajectories, multi-agent) allocates more compute and improves retrieval performance at
the cost of higher latency. Color scales are normalized within each graph and metric for readability.
Hit@1Recall@20
## MRR
## 0
## 20
## 40
## 60
## 80
## 100
## AMAZON
Hit@1Recall@20
## MRR
## 0
## 20
## 40
## 60
## 80
## 100
## MAG
Hit@1Recall@20
## MRR
## 0
## 20
## 40
## 60
## 80
## 100
## PRIME
Qwen3-4BQwen3-8BGPT-4.1Base (light)Distilled 600 (medium)Distilled 6000 (dark)
Figure 4: Evaluation of the same ARK pipeline on the STaRK test sets while varying only the LLM backbone
(Qwen3-4B/8B base, Qwen3-4B/8B distilled, or GPT-4.1).  “Distilled 600” and “Distilled 6000” denote Qwen
backbones fine-tuned on trajectories generated by GPT-4.1 from 600 or 6000 training queries per graph, respectively
(three trajectories per query; tool calls and observations only; no label supervision).
## 0
## 10
## 20
## 30
## Successful
## MAG
## Successful
## PRIME
## 051015202530
## 0
## 10
## 20
## 30
## Unsuccessful
## 051015202530
## Unsuccessful
Number of neighborhood exploration calls
Percentage of trajectories
MedianMean
Figure 5: Distribution of the number of neighborhood
exploration calls, split by successful (Hit@5) and un-
successful trajectories.
Student size matters most on PRIME. Because
base models perform poorly in this regime, distil-
lation is more important, and the teacher-student
gap is the largest. The stronger performance of the
8B student suggests that higher-capacity models
better absorb the long-horizon, high-branching ex-
ploration patterns required for complex biomedical
reasoning in PRIME.
5.6  Neighborhood Exploration vs. Retrieval
We next examine how neighborhood exploration
relates to retrieval success on MAG and PRIME.
Here, successful trajectories refers to the runs (i.e.,
tool call sequences) that retrieve the correct nodes
and therefore score as correct on the retrieval metric
for that query. Figure 5 shows two failure modes.
First, many failed runs make no neighborhood calls
at all, suggesting the agent does not recognize when
relational evidence is needed and never moves be-
yond global anchoring into multi-hop expansion.
Second, failed runs also show a long tail with many
neighborhood calls, indicating the opposite prob-
lem: the agent keeps expanding without converging
on relevant support, consistent with drift in high-
branching parts of the graph.
In contrast, successful trajectories use neighbor-
## 8

hood exploration sparingly, rarely exceeding ten
calls, suggesting that strong retrieval relies on selec-
tive expansion rather than indiscriminate multi-hop
traversal. These results underscore the need for re-
trieval methods like ARK that balance the breadth-
depth tradeoff: when ARK succeeds, it adaptively
switches from global anchoring to neighborhood
expansion, and it stops expanding once it has found
the needed support.
## 6  Conclusion
We   introduced    ADAPTIVE    RETRIEVEROF
KNOWLEDGE, a training-free retrieval framework
that  exposes  knowledge  graphs  through  a  mini-
mal  set  of  primitives  for  global  search  and  lo-
cal relational expansion.  Across all three STaRK
graphs, ARK achieves strong and stable retrieval
performance  while  exhibiting  a  clear  and  inter-
pretable inference-time budget–performance trade-
off.  We further show that this adaptive retrieval
behavior  can  be  transferred  to  a  compact  back-
bone via label-free trajectory distillation with mod-
est data and compute, preserving nearly all of the
teacher’s performance. Together, these results in-
dicate  that  adaptive  graph  retrieval  can  be  both
practical and modular, and that exposing a small
set of well-chosen retrieval operations is sufficient
to unlock robust, general-purpose knowledge graph
retrieval.
## 7  Limitations
Despite strong retrieval performance,  ARK  has
limitations. First, agentic retrieval incurs higher la-
tency than single-pass retrievers because it requires
multiple LLM calls over an interaction trajectory.
Larger budgets improve retrieval quality but also
increase runtime. Second, our best-performing con-
figuration relies on a large proprietary LLM, which
can constrain scalability due to cost and availabil-
ity. While ARK is LLM-agnostic, retrieval quality
can drop with smaller models; we partially mitigate
this via trajectory distillation into Qwen3-8B (Yang
et al., 2025a), though distilled agents still trail the
teacher on challenging regimes.  Third, ARK as-
sumes that node descriptors and relation informa-
tion are sufficiently informative for BM25 global
search and for ranking neighborhood expansions.
Sparse  or  templated  text  can  prevent  the  agent
from locating relevant seed nodes or disambiguat-
ing  them.   Because  the  global  search  is  lexical,
mismatches in vocabulary (e.g., paraphrases and
domain-specific aliases) can cause under-retrieval.
Fourth, our evaluation is centered on text-rich KG
benchmarks, so performance gains may not transfer
to graphs with limited text descriptions.
Although ARK is a general retrieval approach,
agentic graph exploration can create risks if used
without safeguards. Retrieval errors can be treated
as support for downstream decisions, and interac-
tion traces may expose sensitive attributes if node
text contains private information.  Mitigation re-
quires redaction for sensitive fields and bias audits
prior to deployment.
## 8  Ethical Considerations
This study does not use human annotators, crowd-
workers, or research with human participants. Eth-
ical concerns arise in downstream use of agentic
retrieval over text-rich knowledge graphs. Retrieval
errors can be treated as evidence and multi-step ex-
ploration can surface sensitive attributes present
in graph text. The approach may also amplify bi-
ases in the underlying graph.  If some languages
and communities have sparse descriptions or differ-
ent naming conventions, global lexical search and
neighborhood ranking may under-retrieve relevant
information, leading to unequal coverage across
groups and reduced benefits for underrepresented
stakeholders.  We recommend safeguards before
deployment, including redaction of sensitive fields
and bias audits. Potential positive impact includes
improving access to large knowledge graphs for
language models, including information that may
be difficult to access with text retrieval alone.
## Acknowledgments
We   gratefully   acknowledge   the   support   of   NIH   R01-
HD108794,  NSF  CAREER  2339524,  U.S.  DoD  FA8702-
15-D-0001, ARPA-H Biomedical Data Fabric (BDF) Tool-
box  Program,  Harvard  Data  Science  Initiative,  Amazon
## Faculty  Research,  Google  Research  Scholar  Program,  As-
traZeneca Research, Roche Alliance with Distinguished Sci-
entists (ROADS) Program, Sanofi iDEA-iTECH Award, Glax-
oSmithKline Award,  Boehringer Ingelheim Award,  Merck
Award, Optum AI Research Collaboration Award, Pfizer Re-
search, Gates Foundation (INV-079038), Aligning Science
Across Parkinson’s Initiative (ASAP), Chan Zuckerberg Initia-
tive, John and Virginia Kaneb Fellowship at Harvard Medical
School, Biswas Computational Biology Initiative in partner-
ship with the Milken Institute, Harvard Medical School Dean’s
Innovation Fund for the Use of Artificial Intelligence, and
the Kempner Institute for the Study of Natural and Artificial
Intelligence at Harvard University.  A.N. was supported by
the Rhodes Scholarship.   D.A.C. was funded by an NIHR
Research Professorship, Royal Academy of Engineering Re-
search Chair, and the InnoHK Hong Kong Centre for Cerebro-
Cardiovascular Engineering, and was supported by the Na-
tional Institute for Health Research Oxford Biomedical Re-
## 9

search Centre and the Pandemic Sciences Institute at the Uni-
versity of Oxford.  Any opinions, findings, conclusions, or
recommendations expressed in this material are those of the
authors and do not necessarily reflect the views of the funders.
## References
## Akari   Asai,   Kazuma   Hashimoto,   Hannaneh   Hajishirzi,
Richard Socher, and Caiming Xiong. 2020. Learning to Re-
trieve Reasoning Paths over Wikipedia Graph for Question
Answering. arXiv preprint. ArXiv:1911.10470 [cs].
## Emmanuel Bengio, Moksh Jain, Maksym Korablyov, Doina
Precup, and Yoshua Bengio. 2021.  Flow Network based
Generative Models for Non-Iterative Diverse Candidate
Generation. arXiv preprint. Version Number: 2.
Payal  Chandak,  Kexin  Huang,  and  Marinka  Zitnik.  2023.
Building a knowledge graph to enable precision medicine.
## Scientific Data, 10(1):67.  Publisher:  Nature Publishing
## Group.
## Jialin Chen, Houyu Zhang, Seongjun Yun, Alejandro Mot-
tini, Rex Ying, Xiang Song, Vassilis N. Ioannidis, Zheng
Li,  and  Qingjun  Cui.  2025.   GRIL:  Knowledge  Graph
Retrieval-Integrated Learning with Large Language Mod-
els.   In  Findings  of  the  Association  for  Computational
Linguistics: EMNLP 2025, pages 16306–16319, Suzhou,
China. Association for Computational Linguistics.
Gordon V. Cormack, Charles L A Clarke, and Stefan Buettcher.
- Reciprocal rank fusion outperforms condorcet and
individual rank learning methods.  In Proceedings of the
32nd international ACM SIGIR conference on Research
and development in information retrieval, SIGIR ’09, pages
758–759, New York, NY, USA. Association for Computing
## Machinery.
## Rajarshi Das, Shehzaad Dhuliawala, Manzil Zaheer, Luke Vil-
nis, Ishan Durugkar, Akshay Krishnamurthy, Alex Smola,
and Andrew McCallum. 2018.   Go for a Walk and Ar-
rive  at  the  Answer:   Reasoning  Over  Paths  in  Knowl-
edge Bases using Reinforcement Learning. arXiv preprint.
ArXiv:1711.05851 [cs].
## Darren  Edge,  Ha  Trinh,  Newman  Cheng,  Joshua  Bradley,
## Alex Chao, Apurva Mody, Steven Truitt, Dasha Metropoli-
tansky,   Robert  Osazuwa  Ness,   and  Jonathan  Larson.
2025.From  Local  to  Global:    A  Graph  RAG  Ap-
proach to Query-Focused Summarization. arXiv preprint.
ArXiv:2404.16130 [cs].
Ronald Fagin, Ravi Kumar, and D. Sivakumar. 2003. Efficient
similarity search and classification via rank aggregation.
In Proceedings of the 2003 ACM SIGMOD international
conference on Management of data, SIGMOD ’03, pages
301–312, New York, NY, USA. Association for Computing
## Machinery.
Kelvin Guu, Kenton Lee, Zora Tung, Panupong Pasupat, and
Ming-Wei Chang. 2020.   REALM: retrieval-augmented
language model pre-training.  In Proceedings of the 37th
International Conference on Machine Learning, volume
119 of ICML’20, pages 3929–3938. JMLR.org.
Ruining  He  and  Julian  McAuley.  2016.   Ups  and  Downs:
Modeling the Visual Evolution of Fashion Trends with
One-Class Collaborative Filtering. In Proceedings of the
25th International Conference on World Wide Web, WWW
’16, pages 507–517, Republic and Canton of Geneva, CHE.
## International World Wide Web Conferences Steering Com-
mittee.
## Xiaoxin He, Yijun Tian, Yifei Sun, Nitesh V. Chawla, Thomas
Laurent, Yann LeCun, Xavier Bresson, and Bryan Hooi.
-  G-Retriever: Retrieval-Augmented Generation for
Textual Graph Understanding and Question Answering.
arXiv preprint. ArXiv:2402.07630 [cs].
Geoffrey Hinton, Oriol Vinyals, and Jeff Dean. 2015. Distill-
ing the Knowledge in a Neural Network.  arXiv preprint.
ArXiv:1503.02531 [stat].
Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu,
Yuanzhi Li,  Shean Wang,  Lu Wang,  and Weizhu Chen.
-  LoRA: Low-Rank Adaptation of Large Language
Models. arXiv preprint. ArXiv:2106.09685 [cs].
Yikuan Hu, Jifeng Zhu, Lanrui Tang, and Chen Huang. 2025a.
ReMindRAG:  low-cost  LLM-guided  knowledge  graph
traversal for efficient RAG. NeurIPS.
## Yuntong  Hu,  Zhihan  Lei,  Zheng  Zhang,  Bo  Pan,  Chen
Ling, and Liang Zhao. 2025b.  GRAG: Graph Retrieval-
Augmented Generation.   In Findings of the Association
for Computational Linguistics: NAACL 2025, pages 4145–
4157, Albuquerque, New Mexico. Association for Compu-
tational Linguistics.
Mathew Huerta-Enochian and Seung Yong Ko. 2024. Instruc-
tion Fine-Tuning:  Does Prompt Loss Matter?In Pro-
ceedings of the 2024 Conference on Empirical Methods in
Natural Language Processing, pages 22771–22795, Miami,
Florida, USA. Association for Computational Linguistics.
Gautier Izacard and Edouard Grave. 2021.  Leveraging Pas-
sage Retrieval with Generative Models for Open Domain
Question  Answering.   In  Proceedings  of  the  16th  Con-
ference of the European Chapter of the Association for
Computational Linguistics: Main Volume, pages 874–880,
Online. Association for Computational Linguistics.
## Soyeong Jeong, Jinheon Baek, Sukmin Cho, Sung Ju Hwang,
and Jong C Park. 2025.  Database-augmented query rep-
resentation for information retrieval.   In Proceedings of
the 2025 Conference on Empirical Methods in Natural
Language Processing, pages 16622–16644.
## Lars  Benedikt  Kaesberg,  Jonas  Becker,  Jan  Philip  Wahle,
Terry Ruas, and Bela Gipp. 2025.  Voting or Consensus?
Decision-Making in Multi-Agent Debate.  In Findings of
the Association for Computational Linguistics: ACL 2025,
pages 11640–11671. ArXiv:2502.19130 [cs].
Minki Kang, Jongwon Jeong, Seanie Lee, Jaewoong Cho, and
Sung Ju Hwang. 2025. Distilling LLM Agent into Small
Models with Retrieval and Code Tools.   arXiv preprint.
ArXiv:2505.17612 [cs].
## Vladimir Karpukhin, Barlas Oguz, Sewon Min, Patrick Lewis,
Ledell Wu, Sergey Edunov, Danqi Chen, and Wen-tau Yih.
-  Dense Passage Retrieval for Open-Domain Ques-
tion Answering.  In Proceedings of the 2020 Conference
on Empirical Methods in Natural Language Processing
(EMNLP), pages 6769–6781, Online. Association for Com-
putational Linguistics.
Youmin Ko, Sungjong Seo, and Hyunjoon Kim. 2025.  Co-
operative retrieval-augmented generation for question an-
swering:  Mutual information exchange and ranking by
contrasting layers. In NeurIPS.
## 10

Meng-Chieh Lee, Qi Zhu, Costas Mavromatis, Zhen Han, Soji
Adeshina, Vassilis N. Ioannidis, Huzefa Rangwala, and
Christos Faloutsos. 2025.  HybGRAG: Hybrid Retrieval-
Augmented Generation on Textual and Relational Knowl-
edge Bases. In Proceedings of the 63rd Annual Meeting of
the Association for Computational Linguistics (Volume 1:
Long Papers), pages 879–893, Vienna, Austria. Associa-
tion for Computational Linguistics.
## Yongjia Lei, Haoyu Han, Ryan A. Rossi, Franck Dernoncourt,
## Nedim Lipka, Mahantesh M Halappanavar, Jiliang Tang,
and Yu Wang. 2025.  Mixture of Structural-and-Textual
Retrieval over Text-rich Graph Knowledge Bases. In Find-
ings of the Association for Computational Linguistics: ACL
2025, pages 18306–18321, Vienna, Austria. Association
for Computational Linguistics.
## Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni,
## Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike
## Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel,
and Douwe Kiela. 2020. Retrieval-augmented generation
for knowledge-intensive NLP tasks. In Proceedings of the
34th International Conference on Neural Information Pro-
cessing Systems, NIPS ’20, pages 9459–9474, Red Hook,
NY, USA. Curran Associates Inc.
Millicent Li, Tongfei Chen, Benjamin Van Durme, and Patrick
Xia. 2025a. Multi-Field Adaptive Retrieval. arXiv preprint.
ArXiv:2410.20056 [cs].
Mufei Li, Siqi Miao, and Pan Li. 2025b.  Simple Is Effec-
tive:  The Roles of Graphs and Large Language Models
in Knowledge-Graph-Based Retrieval-Augmented Genera-
tion. arXiv preprint. ArXiv:2410.20724 [cs].
## Xiaoxi Li, Jiajie Jin, Yujia Zhou, Yongkang Wu, Zhonghua Li,
Ye Qi, and Zhicheng Dou. 2025c. RetroLLM: Empowering
large language models to retrieve fine-grained evidence
within  generation.   In  Proceedings  of  the  63rd  Annual
Meeting of the Association for Computational Linguistics
(Volume 1: Long Papers), pages 16754–16779.
## Runxuan Liu, Luobei Luobei, Jiaqi Li, Baoxin Wang, Ming
Liu,  Dayong  Wu,  Shijin  Wang,  and  Bing  Qin.  2025.
Ontology-guided reverse thinking makes large language
models stronger on knowledge graph question answering.
In Proceedings of the 63rd Annual Meeting of the Asso-
ciation for Computational Linguistics (Volume 1:  Long
Papers), pages 15269–15284.
Ilya Loshchilov and Frank Hutter. 2019. Decoupled Weight
Decay Regularization. arXiv preprint. ArXiv:1711.05101
## [cs].
Linhao Luo, Yuan-Fang Li, Gholamreza Haffari, and Shirui
Pan.  2024.    Reasoning  on  Graphs:   Faithful  and  Inter-
pretable Large Language Model Reasoning. arXiv preprint.
ArXiv:2310.01061 [cs].
## Shengjie Ma, Chengjin Xu, Xuhui Jiang, Muzhi Li, Huaren
Qu, Cehao Yang, Jiaxin Mao, and Jian Guo. 2025. Think-
on-graph 2.0: Deep and faithful large language model rea-
soning with knowledge-guided retrieval augmented genera-
tion. ICLR.
Christopher D. Manning, Prabhakar Raghavan, and Hinrich
Schütze. 2008. Introduction to information retrieval. Cam-
bridge university press, Cambridge.
## Elan Markowitz, Anil Ramakrishna, Jwala Dhamala, Ninareh
Mehrabi,  Charith  Peris,  Rahul  Gupta,  Kai-Wei  Chang,
and Aram Galstyan. 2024.   Tree-of-Traversals:  A Zero-
Shot Reasoning Algorithm for Augmenting Black-box Lan-
guage Models with Knowledge Graphs.  In Proceedings
of the 62nd Annual Meeting of the Association for Com-
putational Linguistics (Volume 1:  Long Papers),  pages
12302–12319, Bangkok, Thailand. Association for Compu-
tational Linguistics.
Costas Mavromatis and George Karypis. 2025.  GNN-RAG:
Graph  Neural  Retrieval  for  Efficient  Large  Language
Model  Reasoning  on  Knowledge  Graphs.   In  Findings
of the Association for Computational Linguistics:  ACL
2025, pages 16682–16699, Vienna, Austria. Association
for Computational Linguistics.
Julian  McAuley,  Rahul  Pandey,  and  Jure  Leskovec.  2015.
Inferring Networks of Substitutable and Complementary
Products. In Proceedings of the 21th ACM SIGKDD Inter-
national Conference on Knowledge Discovery and Data
Mining, KDD ’15, pages 785–794, New York, NY, USA.
Association for Computing Machinery.
## Niklas Muennighoff, Hongjin Su, Liang Wang, Nan Yang,
Furu Wei, Tao Yu, Amanpreet Singh, and Douwe Kiela.
## 2025.   Generative  Representational  Instruction  Tuning.
arXiv preprint. ArXiv:2402.09906 [cs].
## Long Ouyang, Jeff Wu, Xu Jiang, Diogo Almeida, Carroll L.
## Wainwright,  Pamela  Mishkin,  Chong  Zhang,  Sandhini
## Agarwal, Katarina Slama, Alex Ray, John Schulman, Ja-
cob Hilton, Fraser Kelton, Luke Miller, Maddie Simens,
## Amanda Askell, Peter Welinder, Paul Christiano, Jan Leike,
and Ryan Lowe. 2022.  Training language models to fol-
low instructions with human feedback.   arXiv preprint.
ArXiv:2203.02155 [cs].
## Ruiyang Ren, Yuhao Wang,  Yingqi Qu, Wayne Xin Zhao,
Jing Liu, Hua Wu, Ji-Rong Wen, and Haifeng Wang. 2025.
Investigating the factual knowledge boundary of large lan-
guage models with retrieval augmentation. In Proceedings
of the 31st International Conference on Computational
Linguistics, pages 3697–3715.
Stephen Robertson and Hugo Zaragoza. 2009.  The Proba-
bilistic Relevance Framework: BM25 and Beyond. Found.
## Trends Inf. Retr., 3(4):333–389.
Timo  Schick,  Jane  Dwivedi-Yu,  Roberto  Dessì,  Roberta
## Raileanu, Maria Lomeli, Luke Zettlemoyer, Nicola Can-
cedda,  and  Thomas  Scialom.  2023.   Toolformer:  Lan-
guage Models Can Teach Themselves to Use Tools. arXiv
preprint. ArXiv:2302.04761 [cs].
## Zhengyan Shi,  Adam X. Yang,  Bin Wu,  Laurence Aitchi-
son,  Emine  Yilmaz,  and  Aldo  Lipani.  2024.    Instruc-
tion Tuning With Loss Over Instructions.  arXiv preprint.
ArXiv:2405.14394 [cs].
Haitian Sun, Tania Bedrax-Weiss, and William Cohen. 2019.
PullNet: Open Domain Question Answering with Iterative
Retrieval on Knowledge Bases and Text.  In Proceedings
of the 2019 Conference on Empirical Methods in Natu-
ral Language Processing and the 9th International Joint
Conference on  Natural  Language  Processing  (EMNLP-
IJCNLP), pages 2380–2390, Hong Kong, China. Associa-
tion for Computational Linguistics.
## Jia Ao Sun, Hao Yu, Fabrizio Gotti, Fengran Mo, Yihong
Wu,  Yuchen  Hui,  and  Jian-Yun  Nie.  2025.   Search-on-
Graph: Iterative Informed Navigation for Large Language
Model Reasoning on Knowledge Graphs. arXiv preprint.
ArXiv:2510.08825 [cs].
## 11

## Jiashuo Sun, Chengjin Xu, Lumingyuan Tang, Saizhuo Wang,
Chen Lin, Yeyun Gong, Lionel M. Ni, Heung-Yeung Shum,
and Jian Guo. 2024. Think-on-Graph: Deep and Respon-
sible Reasoning of Large Language Model on Knowledge
Graph. arXiv preprint. ArXiv:2307.07697 [cs].
## Prakhar Verma, Sukruta Prakash Midigeshi, Gaurav Sinha,
Arno Solin, Nagarajan Natarajan, and Amit Sharma. 2024.
Plan* RAG: Efficient test-time planning for retrieval aug-
mented generation. arXiv:2410.20753.
## Junhong Wan, Tao Yu, Kunyu Jiang, Yao Fu, Weihao Jiang,
and Jiang Zhu. 2025.  Digest the knowledge:  Large lan-
guage models empowered message passing for knowledge
graph question answering.   In Proceedings of the 63rd
Annual Meeting of the Association for Computational Lin-
guistics (Volume 1: Long Papers), pages 15426–15442.
## Cunxiang  Wang,  Xiaoze  Liu,  Yuanhao  Yue,  Qipeng  Guo,
## Xiangkun Hu, Xiangru Tang, Tianhang Zhang, Cheng Ji-
ayang, Yunzhi Yao, Xuming Hu, and 1 others. 2025a. Sur-
vey on factuality in large language models. ACM Comput-
ing Surveys, 58(1):1–37.
Kuansan Wang, Zhihong Shen, Chiyuan Huang, Chieh-Han
Wu, Yuxiao Dong, and Anshul Kanakia. 2020. Microsoft
Academic Graph: When experts are not enough. Quantita-
tive Science Studies, 1(1):396–413.
## Liang  Wang,  Haonan  Chen,  Nan  Yang,  Xiaolong  Huang,
Zhicheng Dou, and Furu Wei. 2025b.  Chain-of-retrieval
augmented generation. In NeurIPS.
## Xuezhi  Wang,  Jason  Wei,  Dale  Schuurmans,  Quoc  Le,
Ed  Chi,  Sharan  Narang,  Aakanksha  Chowdhery,  and
Denny Zhou. 2023. Self-Consistency Improves Chain of
Thought Reasoning in Language Models. arXiv preprint.
ArXiv:2203.11171 [cs].
## Shirley Wu, Shiyu Zhao, Qian Huang, Kexin Huang, Michi-
hiro Yasunaga, Kaidi Cao, Vassilis N. Ioannidis, Karthik
Subbian, Jure Leskovec, and James Zou. 2024a. AvaTaR:
Optimizing LLM Agents for Tool Usage via Contrastive
Reasoning. arXiv preprint. ArXiv:2406.11200 [cs].
## Shirley Wu, Shiyu Zhao, Michihiro Yasunaga, Kexin Huang,
## Kaidi Cao, Qian Huang, Vassiiis N. Ioannidis, Karthik Suh-
hian,  James  Zou,  and  Jure  Leskovec.  2024b.   STARK:
benchmarking  LLM  retrieval  on  textual  and  relational
knowledge bases. In Proceedings of the 38th International
Conference on Neural Information Processing Systems, vol-
ume 37 of NIPS ’24, pages 127129–127153, Red Hook,
NY, USA. Curran Associates Inc.
## Sirui Xia, Xintao Wang, Jiaqing Liang, Yifei Zhang, Weikang
Zhou,  Jiaji  Deng,  Fei  Yu,  and  Yanghua  Xiao.  2025a.
Ground every sentence:  Improving retrieval-augmented
llms with interleaved reference-claim generation. In Find-
ings  of  the  Association  for  Computational  Linguistics:
NAACL 2025, pages 969–988.
## Yu Xia, Junda Wu, Sungchul Kim, Tong Yu, Ryan A. Rossi,
Haoliang Wang, and Julian McAuley. 2025b. Knowledge-
Aware  Query  Expansion  with  Large  Language  Models
for  Textual  and  Relational  Retrieval.arXiv  preprint.
ArXiv:2410.13765 [cs].
Wenhan Xiong, Thien Hoang, and William Yang Wang. 2017.
DeepPath: A Reinforcement Learning Method for Knowl-
edge Graph Reasoning. In Proceedings of the 2017 Confer-
ence on Empirical Methods in Natural Language Process-
ing, pages 564–573, Copenhagen, Denmark. Association
for Computational Linguistics.
## An Yang, Anfeng Li, Baosong Yang, Beichen Zhang, Binyuan
## Hui, Bo Zheng, Bowen Yu, Chang Gao, Chengen Huang,
## Chenxu Lv, Chujie Zheng, Dayiheng Liu, Fan Zhou, Fei
## Huang, Feng Hu, Hao Ge, Haoran Wei, Huan Lin, Jialong
Tang,  and  41  others.  2025a.   Qwen3  Technical  Report.
arXiv preprint. ArXiv:2505.09388 [cs].
## Cehao Yang, Xiaojun Wu, Xueyuan Lin, Chengjin Xu, Xuhui
Jiang, Yuanliang Sun, Jia Li, Hui Xiong, and Jian Guo.
2025b. GraphSearch: An Agentic Deep Searching Work-
flow for Graph Retrieval-Augmented Generation.  arXiv
preprint. ArXiv:2509.22009 [cs].
## Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran,
Karthik Narasimhan, and Yuan Cao. 2023. ReAct: Syner-
gizing Reasoning and Acting in Language Models. arXiv
preprint. ArXiv:2210.03629 [cs].
## Sijia Yao, Pengcheng Huang, Zhenghao Liu, Yu Gu, Yukun
Yan, Shi Yu, and Ge Yu. 2025. ExpandR: teaching dense
retrievers beyond queries with LLM guidance.   In Pro-
ceedings of the 2025 Conference on Empirical Methods in
Natural Language Processing, pages 19047–19065.
Junchi Yu, Yujie Liu, Jindong Gu, Philip Torr, and Dongzhan
Zhou. 2025. Can Knowledge-Graph-based Retrieval Aug-
mented Generation Really Retrieve What You Need?  arXiv
preprint. ArXiv:2510.16582 [cs].
Shuo    Zhang,Liangming    Pan,Junzhou    Zhao,and
William  Yang  Wang.  2024.The  knowledge  align-
ment problem: Bridging human and external knowledge
for large language models.   In Findings of the Associa-
tion  for  Computational  Linguistics:   ACL  2024,  pages
## 2025–2038.
## Zaiyi Zheng, Song Wang, Zihan Chen, Yaochen Zhu, Yin-
han He, Liangjie Hong, Qi Guo, and Jundong Li. 2025.
CoRAG: Enhancing Hybrid Retrieval-Augmented Gener-
ation through a Cooperative Retriever Architecture.   In
Findings of the Association for Computational Linguis-
tics: EMNLP 2025, pages 16088–16101, Suzhou, China.
Association for Computational Linguistics.
Rongzhi Zhu, Xiangyu Liu, Zequn Sun, Yiwei Wang, and
Wei Hu. 2025a.  Mitigating lost-in-retrieval problems in
retrieval augmented multi-hop question answering. In Pro-
ceedings of the 63rd Annual Meeting of the Association for
Computational Linguistics (Volume 1: Long Papers), pages
22362–22375, Vienna, Austria. Association for Computa-
tional Linguistics.
Xiangrong Zhu, Yuexiang Xie, Yi Liu, Yaliang Li, and Wei Hu.
2025b.  Knowledge Graph-Guided Retrieval Augmented
Generation.   In Proceedings of the 2025 Conference of
the Nations of the Americas Chapter of the Association
for Computational Linguistics:  Human Language Tech-
nologies (Volume 1: Long Papers), pages 8912–8924, Al-
buquerque, New Mexico. Association for Computational
## Linguistics.
## 12

## A  Appendix
## A.1  Dataset Statistics
DatasetTrainValidationTest
## PRIME6,1622,2402,016
## MAG7,9932,6642,664
## AMAZON5,9151,5471,638
Table 3:  Number of queries per dataset split for each
STaRK graph.
## Dataset
## Entity
types
## Relation
types
## Average
degree
EntitiesRelationsTokens
## AMAZON4518.21,035,5429,443,802592,067,882
## MAG4443.51,872,96839,802,116212,602,571
## PRIME1018125.2129,3758,100,49831,844,769
Table 4:  Statistics of the constructed semi-structured
knowledge graphs used in STaRK.
## A.2  Implementation Details
ADAPTIVE RETRIEVER  OF KNOWLEDGE is run withn=3
parallel agents and a maximum trajectory length ofT
max
## =20.
Our  primary  configuration  uses  GPT-4.1  as  the  decision-
making backbone. For comparability with prior KG retrievers
such as KAR and Think-on-Graph,  we additionally report
results using GPT-4o, the backbone used in those works. For
the distilled variant, we use Qwen3-8B (Yang et al., 2025a)
(matching the model scale used by GraphFlow and Think-on-
Graph with LLaMA3), trained via imitation on ADAPTIVE
RETRIEVER OF KNOWLEDGE teacher trajectories, while keep-
ing the tool interface and exploration hyperparameters fixed.
Each tool call is executed with a bounded retrieval budget.
Neighborhood exploration uses a fixed budget ofk=20neigh-
bors per expansion. Global search returns up toknodes from
the full graph.  By defaultk=5, but the agent may override
this value as a tool parameter.
Each agent outputs an ordered list of selected nodes. We
aggregate these lists by ranking nodes first by the number of
agents that selected them (vote count), and breaking ties by
the earliest position at which the node appears in any agent’s
list Section 3.2.  The aggregated ranking is truncated to the
top 20 nodes to compute Recall@20; Hit@1 and MRR are
computed on the same ranking.
## A.3  Knowledge Graph Exploration Agent
## System Prompt
This section contains the system prompt used for the Knowl-
edge Graph Exploration Agent.
## # Knowledge  Graph  Exploration  Agent
You  are  exploring a knowledge  graph  to
find  specific  entities  that  answer
complex  questions. The  graph
structure  and  entity  types  vary by
domain , but  the  exploration  strategy
remains  consistent.
## ##  Available  Node  Types
The  graph  contains  the  following  node
types: {node_types}
Between  the nodes , the  possible  relation
types  are: {edge_types}
## ##  Available  Tools
###  search_in_graph
- ** query ** (required): Keywords , entity
names , or  descriptive  terms
relevant  to the  query
- **size** (optional): Number  of  results
to  return (default  20)
- Use  this  for  initial  broad  searches
across  the  entire  graph  to  identify
relevant  entities
- The  search  uses BM25 , which  works  well
for  keyword -based  retrieval
###  search_in_neighborhood
- ** node_index ** (required): The  node
index  to  explore  around
- ** query ** (optional): Keywords  to
filter  neighborhood  results
- ** node_type ** (optional): Filter  by
entity  type
- ** edge_type ** (optional): Filter  by
specific  relation  types
- Shows  relation  types  between  the
reference  node  and  its  neighbors
with  directional  arrows
- Use  this to  explore  the  immediate
neighborhood  (1 hop) of  specific
nodes  found  through  initial  searches
###  add_to_answer
- ** answer_nodes ** (required): List of
answer  nodes , each  with:
- ** node_index **:  The  index  of the
node to add as an  answer
- ** reasoning **:  Explanation  of why
this  node is  relevant  to the
question
- Use  this to  collect  relevant  entities
with  justifications
###  finish
- ** comment ** (optional): Optional
comment  explaining  why  exploration
is  finished
- Use  this  when  you  have  found  all
relevant  nodes  or  exhausted  useful
exploration  paths
## ##  Exploration  Strategy
Your  approach  should  adapt  based  on the
query  structure:
###  Strategy  1:  Queries  without  explicit
entity  mentions
When  the  query  does  not  explicitly
mention  specific  entities (e.g.,
product  names , paper  titles , gene
names , author  names , etc.), use a
broad  search  strategy  to  provide  the
user  with  many  options:
- Use`search_in_graph` with  the  full
question  as the  query  and  size =30 to
cast a wide  net
## 13

## AMAZONMAGPRIME
MethodHit@1Hit@5R@20MRRHit@1Hit@5R@20MRRHit@1Hit@5R@20MRR
GPT-4o55.1376.3757.1864.2967.0186.6779.7975.4636.0160.1760.1346.44
## GPT-4.155.8275.8060.6164.7773.4087.9284.4779.8748.2069.5769.4657.68
Qwen3-4B45.6967.4647.1755.2637.6456.5654.5446.0118.0237.0035.4326.20
Qwen3-4B-60050.1071.2653.7359.3249.9069.2168.4758.4326.5247.2749.5436.01
Qwen3-4B-600054.4674.6658.9164.7860.1678.7979.8868.5927.4649.1551.4036.95
Qwen3-8B47.9570.0353.1057.9535.0957.0253.4244.9618.3736.4136.1326.28
Qwen3-8B-60050.0670.0755.2959.1348.8969.4168.4858.1325.2447.2050.1635.08
Qwen3-8B-600054.9974.3560.3164.2461.6680.4181.3970.0931.8751.1057.2241.08
Table 5: Retrieval performance on STaRK synthetic test sets.
-  Review  all 30  results  and  select
approximately  15 of the  most
suitable  entities  to add to the
answer (aim  for  roughly  half of the
search  results)
- Add  the  selected  entities  to the
answer  with  clear  reasoning  for  each
** Important **:  The  goal is to  provide
users  with  multiple  relevant  options
. When  the  query  is  descriptive  and
doesn't name  specific  entities , you
should  return a substantial  number
of  results (around  15 from a search
of size  30). This  ensures  users  have
many  options  to  choose  from. Only
exclude  results  that  are  clearly
irrelevant  to the  query.
This  strategy  works  well  when:
- The  query  is  descriptive  but doesn't
name  specific  entities
- You  want to  provide  multiple  options
to the  user (which  is  often  the  case
## )
- The graph's search  function (BM25) can
effectively  match  keywords  from  the
query
###  Strategy  2:  Queries  with  explicit
entity  mentions
When  the  query  explicitly  mentions
specific  entities (e.g., "product X
## ", "paper Y", "gene Z", "author W"),
use a targeted  exploration  strategy
## :
- ** Entity  disambiguation **: First ,
search  for  the  mentioned  entities
using`search_in_graph` with  the
entity  name
- ** Neighborhood  exploration **:  Once
you've  identified  the  relevant
entity  nodes , use`
search_in_neighborhood` to  explore
their  connections
- ** Filtered  search **:  Use  the`query`
parameter  in  neighborhood  searches
to  filter  results  by  keywords  from
the  original  question
This  strategy  works  well  when:
- The  query  mentions  specific  entities
that  likely  exist  in the  graph
- You  need to  explore  relationships
around  known  entities
- The  query  requires  multi -hop  reasoning
###  Strategy  3: Multi -entity  or  complex
queries
For  queries  that  involve  multiple
entities  or  require  combining
information:
-  Start  by  disambiguating  all  mentioned
entities
-  Explore  neighborhoods  of key  entities
with  relevant  filters
-  Combine  information  from  multiple
exploration  paths
## ##  Examples
###  Example  1:  Simple  broad  search (
## Strategy  1)
** Query **: "Find  products  suitable  for
outdoor  camping"
** Approach **:  Since  no  specific  products
are  mentioned , use`search_in_graph
(query ="Find  products  suitable  for
outdoor  camping", size =30)`. This
will  return  30  results. Then , review
all 30  results  and  add
approximately  15 of the  most
suitable  products  to the  answer
using`add_to_answer`. This  gives
the  user  many  options  to  choose  from
## .
###  Example  2: Entity -specific  query (
## Strategy  2)
** Query **: "What  are  some  winter -themed
accessories  from  the  BrandX  company
## ?"
## ** Approach **:
- First , search  for  the  brand/company:
`search_in_graph (" BrandX  company ")`
- Then  explore  its  neighborhood:`
search_in_neighborhood(node_index=<
found_brand_index >, query ="winter -
themed  accessories ")`
###  Example  3: Multi -hop  reasoning (
## Strategy  2)
** Query **: "Can  you  find  other
publications  from  the co -authors  of
## 14

the  paper  titled'Machine  Learning
Applications  in  Healthcare' that
relate  to  neural  networks ?"
## ** Approach **:
-  Search  for  the  paper:`
search_in_graph (" Machine  Learning
Applications  in  Healthcare ")`
- Find co -authors:`
search_in_neighborhood(node_index=<
paper_index >, node_type=author)`
- For  each  author , search  their  papers:
## `search_in_neighborhood(node_index
=<author_index >, query =" neural
networks", node_type=paper)`
###  Example  4:  Multiple  constraints (
## Strategy  3)
** Query **: "What  medications  interact
synergistically  with  DrugX  and  are
also  used to  treat  DiseaseY ?"
## ** Approach **:
- Find  DrugX:`search_in_graph (" DrugX ")
## `
- Find  DiseaseY:`search_in_graph ("
DiseaseY ")`
-  Explore  neighborhoods:`
search_in_neighborhood(node_index=<
disease_index >, node_type=drug)` and
## `search_in_neighborhood(node_index
=<drugx_index >, node_type=drug)`
- Add  the  drugs  to the  answer
## ##  General  Guidelines
- ** Provide  multiple  options  when
appropriate **:  For  queries  without
explicit  entity  mentions , aim to
give  users  many  relevant  options (
typically  10-20  entities  from a
search  of size  30)
- ** Start  broad , then  narrow **:  Begin
with  global  searches , then  focus  on
specific  neighborhoods
- **Use  filters  strategically **:  Apply`
node_type` and`edge_type` filters
to  reduce  noise  and  focus
exploration
- ** Combine  multiple  strategies **:
Complex  queries  may  require  mixing
broad  searches  and  neighborhood
exploration
- ** Balance  relevance  and  coverage **:
When  selecting  entities  to add to
answers , prioritize  relevance  but
also  aim  for  good  coverage  when  the
query  allows  for  multiple  valid
answers
- ** Provide  reasoning **:  Always  include
clear  reasoning  when  adding  entities
to  answers
- ** Adapt  to  graph  characteristics **:
Some  graphs  may  benefit  more  from
broad  searches (e.g., when  BM25
works  well), while  others  may
require  more  targeted  exploration
## 15