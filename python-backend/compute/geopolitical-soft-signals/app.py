from __future__ import annotations

from typing import Any

from shared import create_service_app
from geopolitical_soft_signals.game_theory import (
    GameTheoryImpactRequest,
    GameTheoryImpactResponse,
    MonteCarloSimulationRequest,
    MonteCarloSimulationResponse,
    NashSolveRequest,
    NashSolveResponse,
    StrategemeMatchRequest,
    StrategemeMatchResponse,
    TimelineRegimeRequest,
    TimelineRegimeResponse,
    TransmissionPathRequest,
    TransmissionPathResponse,
    build_timeline_regimes,
    build_transmission_paths,
    build_game_theory_impact,
    match_strategemes,
    run_monte_carlo_simulation,
    solve_nash_equilibria,
)
from geopolitical_soft_signals.pipeline import (  # noqa: E402
    IngestClassifyRequest,
    IngestClassifyResponse,
    NLPClusterRequest,
    NLPClusterResponse,
    SignalRequest,
    SignalResponse,
    build_ingest_classification,
    build_narrative_shift,
    build_news_cluster,
    build_social_surge,
    cluster_narratives_embedding,
)


app = create_service_app("geopolitical-soft-signals", http_port=8091)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True}


@app.post("/api/v1/cluster-headlines", response_model=SignalResponse)
def cluster_headlines(payload: SignalRequest) -> SignalResponse:
    return build_news_cluster(payload)


@app.post("/api/v1/social-surge", response_model=SignalResponse)
def social_surge(payload: SignalRequest) -> SignalResponse:
    return build_social_surge(payload)


@app.post("/api/v1/narrative-shift", response_model=SignalResponse)
def narrative_shift(payload: SignalRequest) -> SignalResponse:
    return build_narrative_shift(payload)


@app.post("/api/v1/ingest/classify", response_model=IngestClassifyResponse)
def ingest_classify(payload: IngestClassifyRequest) -> IngestClassifyResponse:
    return build_ingest_classification(payload)


@app.post("/api/v1/game-theory/impact", response_model=GameTheoryImpactResponse)
def game_theory_impact(payload: GameTheoryImpactRequest) -> GameTheoryImpactResponse:
    return build_game_theory_impact(payload)


@app.post("/api/v1/game-theory/nash-solve", response_model=NashSolveResponse)
def game_theory_nash_solve(payload: NashSolveRequest) -> NashSolveResponse:
    return solve_nash_equilibria(payload)


@app.post("/api/v1/game-theory/transmission-paths", response_model=TransmissionPathResponse)
def game_theory_transmission_paths(payload: TransmissionPathRequest) -> TransmissionPathResponse:
    return build_transmission_paths(payload)


@app.post("/api/v1/game-theory/monte-carlo", response_model=MonteCarloSimulationResponse)
def game_theory_monte_carlo(payload: MonteCarloSimulationRequest) -> MonteCarloSimulationResponse:
    return run_monte_carlo_simulation(payload)


@app.post("/api/v1/game-theory/strategeme-match", response_model=StrategemeMatchResponse)
def game_theory_strategeme_match(payload: StrategemeMatchRequest) -> StrategemeMatchResponse:
    return match_strategemes(payload)


@app.post("/api/v1/game-theory/timeline-regimes", response_model=TimelineRegimeResponse)
def game_theory_timeline_regimes(payload: TimelineRegimeRequest) -> TimelineRegimeResponse:
    return build_timeline_regimes(payload)


@app.post("/api/v1/nlp/cluster", response_model=NLPClusterResponse)
def nlp_cluster(payload: NLPClusterRequest) -> NLPClusterResponse:
    """Cluster texts using sentence-transformers + HDBSCAN (Phase 12a).

    Returns cluster assignments keyed by integer label (-1 = noise) and noise_count.
    Requires sentence-transformers and hdbscan to be installed; returns 503 otherwise.
    """
    try:
        result = cluster_narratives_embedding(payload.texts, min_cluster_size=payload.min_cluster_size)
        return NLPClusterResponse(clusters=result["clusters"], noise_count=result["noise_count"])
    except ImportError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Embedding clustering unavailable: {exc}") from exc
