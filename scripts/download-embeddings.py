"""Download Embedding + Reranker Modelle fuer Hindsight Memory Engine.

Einmalig ausfuehren: uv run python scripts/download-embeddings.py
Modelle werden in HF_HOME Cache gespeichert (default: ~/.cache/huggingface/).

Modelle:
  - BAAI/bge-small-en-v1.5 (Embeddings, 384-dim, ~30MB)
  - cross-encoder/ms-marco-MiniLM-L-6-v2 (Reranker, ~80MB)
"""

import os
import sys

# Cache-Pfad setzen (optional, default ist ~/.cache/huggingface/)
CACHE_DIR = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
print(f"Cache dir: {CACHE_DIR}")

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

print(f"\n=== Downloading Embedding Model: {EMBEDDING_MODEL} ===")
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
    dim = model.get_sentence_embedding_dimension()
    print(f"  OK: {EMBEDDING_MODEL} loaded (dim: {dim})")

    # Quick test
    emb = model.encode(["test sentence"])
    print(f"  Test embedding shape: {emb.shape}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

print(f"\n=== Downloading Reranker Model: {RERANKER_MODEL} ===")
try:
    from sentence_transformers import CrossEncoder
    reranker = CrossEncoder(RERANKER_MODEL, device="cpu")
    print(f"  OK: {RERANKER_MODEL} loaded")

    # Quick test
    score = reranker.predict([("query", "document")])
    print(f"  Test score: {score}")
except Exception as e:
    print(f"  WARNING (optional): {e}")

print("\n=== Done ===")
print(f"Models cached at: {CACHE_DIR}")
print("Hindsight will use these cached models automatically.")
