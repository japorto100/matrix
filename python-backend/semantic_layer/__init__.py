"""Provider-agnostic semantic catalog primitives."""

from semantic_layer.catalog import (
    DEFAULT_SEMANTIC_CATALOG,
    CorrectionProposal,
    PermissionContext,
    SemanticCatalog,
    SemanticMetric,
    SemanticTerm,
    build_default_catalog,
    lookup_phrase,
    plan_metric_query,
    propose_correction,
    review_correction,
    validate_catalog,
)

__all__ = [
    "DEFAULT_SEMANTIC_CATALOG",
    "CorrectionProposal",
    "PermissionContext",
    "SemanticCatalog",
    "SemanticMetric",
    "SemanticTerm",
    "build_default_catalog",
    "lookup_phrase",
    "plan_metric_query",
    "propose_correction",
    "review_correction",
    "validate_catalog",
]
