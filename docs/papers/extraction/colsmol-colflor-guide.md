# ColSmol & ColFlor — Lightweight Visual Document Retrieval

Beide sind OCR-freie, ColBERT-style Multi-Vector Retrieval Modelle aus der ColPali-Familie.
Kein Text-Parsing, kein Chunking — direkt auf Seiten-Screenshots.

## Vergleich

| | ColQwen2 (7B) | ColSmol-256M | ColFlor (174M) |
|---|---|---|---|
| Parameter | 7B | 256M | 174M |
| Backbone | Qwen2-VL | SmolVLM-250M | Florence-2 |
| Speed (query) | Baseline | ~schnell | 9.8× schneller als ColPali |
| Speed (image) | Baseline | ~schnell | 5.25× schneller als ColPali |
| Qualität | SOTA | ~98.2% von ColQwen2 | ~1.8% Drop vs ColPali |
| Sprache | Multilingual | EN (zero-shot andere) | nur EN |
| GPU-Bedarf | hoch | minimal | minimal |

**Empfehlung:** ColFlor für lokale/schnelle Nutzung. ColQwen2 wenn Qualität wichtiger als Speed.

---

## ColSmol-256M

HuggingFace: https://huggingface.co/vidore/colSmol-256M

### Install

```bash
pip install "colpali-engine>=0.3.5"
pip install --upgrade transformers
```

### Quickstart

```python
import torch
from PIL import Image
from colpali_engine.models import ColIdefics3, ColIdefics3Processor

model = ColIdefics3.from_pretrained(
    "vidore/colSmol-256M",
    torch_dtype=torch.bfloat16,
    device_map="cuda:0",
    attn_implementation="flash_attention_2",
)
model = model.to("cuda").eval_mode()  # inference mode

processor = ColIdefics3Processor.from_pretrained("vidore/colSmol-256M")

images = [Image.open("page1.png"), Image.open("page2.png")]
queries = ["Was steht im Abstract?", "Welche Methode wird verwendet?"]

batch_images = processor.process_images(images).to(model.device)
batch_queries = processor.process_queries(queries).to(model.device)

with torch.no_grad():
    image_embeddings = model(**batch_images)
    query_embeddings = model(**batch_queries)

scores = processor.score_multi_vector(query_embeddings, image_embeddings)
# scores[i][j] = relevanz von query i für seite j
```

> Hinweis: In PyTorch `.eval()` auf dem model-Objekt aufrufen um Inference-Mode zu setzen.

---

## ColFlor (174M)

HuggingFace: https://huggingface.co/ahmed-masry/ColFlor

17× kleiner als ColPali, 9.8× schneller bei Query-Encoding. BERT-Größe.

### Install

```bash
git clone https://github.com/AhmedMasryKU/colflor
cd colflor
pip install -e .
```

### Quickstart

```python
import torch
from colpali_engine.models import ColFlor, ColFlorProcessor

model = ColFlor.from_pretrained("ahmed-masry/ColFlor", device_map="auto")
# model.eval() — inference mode setzen
processor = ColFlorProcessor.from_pretrained("ahmed-masry/ColFlor")

# Dokument-Seiten einbetten
batch_docs = processor.process_images(images)
with torch.no_grad():
    doc_embeddings = model(**{k: v.to(model.device) for k, v in batch_docs.items()})

# Query einbetten
batch_queries = processor.process_queries(queries)
with torch.no_grad():
    query_embeddings = model(**{k: v.to(model.device) for k, v in batch_queries.items()})

# Scoring
scores = processor.score(query_embeddings, doc_embeddings).cpu().numpy()
top_pages = scores.argmax(axis=1)
```

### Mit DataLoader (für viele Seiten)

```python
from torch.utils.data import DataLoader
from colpali_engine.utils.torch_utils import ListDataset

dataloader = DataLoader(
    dataset=ListDataset(images),
    batch_size=4,
    collate_fn=lambda x: processor.process_images(x),
)

all_embeddings = []
for batch in dataloader:
    with torch.no_grad():
        emb = model(**{k: v.to(model.device) for k, v in batch.items()})
    all_embeddings.extend(list(torch.unbind(emb.to("cpu"))))
```

---

## Typischer RAG-Workflow

```
PDF → Seiten als PNG rendern (z.B. pdf2image)
     → process_images() → Embeddings in Vektordatenbank (z.B. Qdrant)
Query → process_queries() → Embedding → ANN-Suche
     → Top-K Seiten-PNGs → Multimodales LLM (z.B. Qwen2-VL) für finale Antwort
```

### PDF zu PNG

```python
from pdf2image import convert_from_path

pages = convert_from_path("dokument.pdf", dpi=150)
# pages ist bereits eine Liste von PIL.Image — direkt in process_images() nutzbar
```

---

## Bekannte Limitierungen

- ColFlor & ColSmol: nur Englisch zuverlässig
- Schwächen bei figure-heavy Dokumenten (Diagramme, Plots) vs. ColQwen2
- Vektor-DBs ohne native Multi-Vector Support (wie pgvector) brauchen Workaround
