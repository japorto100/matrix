"""sentence-transformers Embedder (default: all-MiniLM-L6-v2, 384 dim, CPU)."""

from __future__ import annotations

from loguru import logger

from ingestion.core.exceptions import EmbeddingError
from ingestion.embedders.base import Embedder


class SentenceTransformerEmbedder(Embedder):
    """Local CPU embedder via sentence-transformers.

    Lazy-loads the model on first embed() call to avoid startup cost.
    Default model all-MiniLM-L6-v2 = 384 dim, ~80 MB download.
    """

    name = "sentence_transformer"

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None  # lazy
        self.dim = 384  # known for MiniLM-L6-v2; updated after load

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if os.getenv("EMBEDDER_ALLOW_MODEL_DOWNLOAD", "true").lower() not in ("1", "true", "yes"):
            raise EmbeddingError(
                "Model download disabled (EMBEDDER_ALLOW_MODEL_DOWNLOAD=false). "
                f"Pre-download '{self.model_name}' or enable downloads."
            )
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise EmbeddingError(
                "sentence-transformers not installed. Run: uv add sentence-transformers"
            ) from e
        logger.info("loading embedding model {}", self.model_name)
        self._model = SentenceTransformer(self.model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension() or self.dim)
        logger.info("embedder loaded — dim={}", self.dim)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure_loaded()
        assert self._model is not None
        try:
            vectors = self._model.encode(
                texts, convert_to_numpy=True, show_progress_bar=False
            )
        except Exception as e:
            raise EmbeddingError(f"embedding failed: {e}") from e
        return vectors.tolist()
