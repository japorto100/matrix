"""Small retrieval canaries for Feature 019."""

from retrieval.evals.benchmark_lab import (
    DEFAULT_MATRIX_CANDIDATES,
    MATRIX_FUSED,
    MATRIX_KG_ONLY,
    MATRIX_VECTOR_ONLY,
    RetrievalCandidate,
    compare_candidates,
    evaluate_candidate,
    write_benchmark_report,
)
from retrieval.evals.canaries import (
    CanaryExpectation,
    RetrievalCanary,
    evaluate_canary,
    evaluate_canary_set,
)

__all__ = [
    "CanaryExpectation",
    "DEFAULT_MATRIX_CANDIDATES",
    "MATRIX_FUSED",
    "MATRIX_KG_ONLY",
    "MATRIX_VECTOR_ONLY",
    "RetrievalCanary",
    "RetrievalCandidate",
    "evaluate_canary",
    "evaluate_canary_set",
    "compare_candidates",
    "evaluate_candidate",
    "write_benchmark_report",
]
