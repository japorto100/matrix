from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
import random
from typing import Literal, cast

from pydantic import BaseModel, Field


MarketBias = Literal["risk_on", "risk_off", "neutral"]
TransmissionDirection = Literal["up", "down", "flat"]


class GameTheoryEventInput(BaseModel):
    id: str = Field(min_length=1)
    eventDate: str
    country: str = ""
    region: str | None = None
    eventType: str = Field(min_length=1)
    subEventType: str | None = None
    fatalities: int = Field(default=0, ge=0)
    source: str | None = None
    notes: str | None = None


class GameTheoryImpactRequest(BaseModel):
    generatedAt: str
    events: list[GameTheoryEventInput] = Field(default_factory=list)
    limit: int = Field(default=12, ge=1, le=200)


class GameTheoryImpactItem(BaseModel):
    id: str
    eventId: str
    eventTitle: str
    region: str
    marketBias: MarketBias
    impactScore: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    drivers: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    eventDate: str


class GameTheoryImpactSummary(BaseModel):
    analyzedEvents: int
    avgImpactScore: float = Field(ge=0.0, le=1.0)
    riskOnCount: int = Field(default=0, ge=0)
    riskOffCount: int = Field(default=0, ge=0)
    neutralCount: int = Field(default=0, ge=0)
    topRegion: str | None = None


class GameTheoryImpactResponse(BaseModel):
    source: str = "game_theory_heuristic_v1"
    summary: GameTheoryImpactSummary
    items: list[GameTheoryImpactItem]


class NashOutcomeInput(BaseModel):
    strategies: dict[str, str] = Field(default_factory=dict)
    payoffs: dict[str, float] = Field(default_factory=dict)


class NashSolveRequest(BaseModel):
    players: list[str] = Field(default_factory=list, min_length=2, max_length=8)
    outcomes: list[NashOutcomeInput] = Field(default_factory=list, min_length=1)


class NashSolveResponse(BaseModel):
    equilibria: list[NashOutcomeInput] = Field(default_factory=list)
    selected: NashOutcomeInput | None = None
    status: Literal["equilibrium_found", "fallback_best_sum_payoff"]


class TransmissionPathRequest(BaseModel):
    region: str = "Global"
    eventType: str = Field(min_length=1)
    impactScore: float = Field(default=0.5, ge=0.0, le=1.0)
    channels: list[str] = Field(default_factory=lambda: ["energy", "rates", "equity", "fx"])


class TransmissionArc(BaseModel):
    channel: str
    market: str
    direction: Literal["up", "down", "flat"]
    impact: float = Field(ge=0.0, le=1.0)


class TransmissionPathResponse(BaseModel):
    region: str
    eventType: str
    arcs: list[TransmissionArc] = Field(default_factory=list)


class MonteCarloSimulationRequest(BaseModel):
    initialPrice: float = Field(gt=0.0)
    drift: float = 0.0
    volatility: float = Field(gt=0.0, le=5.0)
    days: int = Field(default=30, ge=1, le=365)
    paths: int = Field(default=1000, ge=10, le=10000)
    seed: int = 42


class MonteCarloSimulationResponse(BaseModel):
    paths: int
    days: int
    p10: float
    p50: float
    p90: float
    expectedPrice: float
    samplePathTerminal: list[float] = Field(default_factory=list)


class StrategemeMatchRequest(BaseModel):
    text: str = Field(min_length=1)


class StrategemeMatch(BaseModel):
    code: str
    title: str
    confidence: float = Field(ge=0.0, le=1.0)


class StrategemeMatchResponse(BaseModel):
    matches: list[StrategemeMatch] = Field(default_factory=list)
    topMatch: StrategemeMatch | None = None


class TimelineEventInput(BaseModel):
    date: str
    impactScore: float = Field(ge=0.0, le=1.0)


class TimelineRegimeRequest(BaseModel):
    events: list[TimelineEventInput] = Field(default_factory=list)


class TimelineRegimeBand(BaseModel):
    date: str
    regime: Literal["elevated", "watch", "calm"]
    impactScore: float = Field(ge=0.0, le=1.0)


class TimelineRegimeResponse(BaseModel):
    bands: list[TimelineRegimeBand] = Field(default_factory=list)
    elevatedCount: int = Field(default=0, ge=0)
    watchCount: int = Field(default=0, ge=0)
    calmCount: int = Field(default=0, ge=0)


REGION_SYMBOLS: dict[str, list[str]] = {
    "europe": ["DAX", "SX5E", "EURUSD"],
    "middle east": ["BRENT", "XAUUSD", "USDILS"],
    "asia": ["NIKKEI", "HSI", "USDJPY"],
    "americas": ["SPY", "VIX", "US10Y"],
    "africa": ["XAUUSD", "WTI", "DXY"],
    "global": ["SPY", "DXY", "XAUUSD"],
}

COUNTRY_TO_REGION: dict[str, str] = {
    "ukraine": "Europe",
    "russia": "Europe",
    "germany": "Europe",
    "france": "Europe",
    "united kingdom": "Europe",
    "israel": "Middle East",
    "iran": "Middle East",
    "saudi arabia": "Middle East",
    "china": "Asia",
    "taiwan": "Asia",
    "japan": "Asia",
    "south korea": "Asia",
    "united states": "Americas",
    "usa": "Americas",
    "canada": "Americas",
    "brazil": "Americas",
    "sudan": "Africa",
    "congo": "Africa",
    "nigeria": "Africa",
}

RISK_OFF_TOKENS: tuple[str, ...] = (
    "battle",
    "armed clash",
    "air strike",
    "missile",
    "drone",
    "attack",
    "explosion",
    "violence",
    "sanction",
    "embargo",
    "export control",
    "retaliation",
)

RISK_ON_TOKENS: tuple[str, ...] = (
    "ceasefire",
    "de-escalation",
    "deescalation",
    "truce",
    "talks",
    "agreement",
    "negotiation",
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().strip().split())


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _normalize_date(raw: str) -> str:
    trimmed = raw.strip()
    if not trimmed:
        return datetime.now(timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(trimmed.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        if len(trimmed) == 10 and trimmed[4] == "-" and trimmed[7] == "-":
            return f"{trimmed}T00:00:00+00:00"
        return datetime.now(timezone.utc).isoformat()


def _infer_region(event: GameTheoryEventInput) -> str:
    direct = event.region.strip() if event.region else ""
    if direct:
        return direct
    by_country = COUNTRY_TO_REGION.get(_normalize_text(event.country))
    if by_country:
        return by_country
    return "Global"


def _symbols_for_region(region: str) -> list[str]:
    normalized = _normalize_text(region)
    for key, symbols in REGION_SYMBOLS.items():
        if key in normalized:
            return symbols
    return REGION_SYMBOLS["global"]


def _score_event(event: GameTheoryEventInput, index: int) -> GameTheoryImpactItem:
    text = _normalize_text(f"{event.eventType} {event.subEventType or ''} {event.notes or ''}")
    drivers: list[str] = []
    score = 0.28

    if event.fatalities >= 50:
        score += 0.38
        drivers.append("fatalities_extreme")
    elif event.fatalities >= 10:
        score += 0.25
        drivers.append("fatalities_high")
    elif event.fatalities >= 1:
        score += 0.12
        drivers.append("fatalities_nonzero")

    if any(token in text for token in RISK_OFF_TOKENS):
        score += 0.22
        drivers.append("kinetic_or_sanctions_escalation")
    if "protest" in text or "riot" in text or "civil unrest" in text:
        score += 0.08
        drivers.append("civil_unrest")
    if "election" in text:
        score += 0.06
        drivers.append("election_volatility")

    has_risk_on_token = any(token in text for token in RISK_ON_TOKENS)
    if has_risk_on_token:
        score -= 0.14
        drivers.append("deescalation_signal")

    if "central bank" in text or "rate" in text or "inflation" in text:
        score += 0.05
        drivers.append("policy_rate_channel")

    score = _clamp(score, 0.05, 0.98)

    if has_risk_on_token and score < 0.55:
        bias: MarketBias = "risk_on"
    elif score >= 0.6:
        bias = "risk_off"
    else:
        bias = "neutral"

    confidence = 0.44 + min(0.3, len(drivers) * 0.06)
    if _normalize_text(event.source):
        confidence += 0.06
        drivers.append("source_attribution")
    confidence = _clamp(confidence, 0.2, 0.96)

    region = _infer_region(event)
    symbols = _symbols_for_region(region)
    title_left = event.subEventType or event.eventType
    title_right = event.country or "Unknown"

    return GameTheoryImpactItem(
        id=f"gt-{index}-{event.id}"[:64],
        eventId=event.id,
        eventTitle=f"{title_left}: {title_right}",
        region=region,
        marketBias=bias,
        impactScore=round(score, 4),
        confidence=round(confidence, 4),
        drivers=drivers[:6],
        symbols=symbols,
        eventDate=_normalize_date(event.eventDate),
    )


def build_game_theory_impact(payload: GameTheoryImpactRequest) -> GameTheoryImpactResponse:
    if not payload.events:
        return GameTheoryImpactResponse(
            summary=GameTheoryImpactSummary(
                analyzedEvents=0,
                avgImpactScore=0.0,
                riskOnCount=0,
                riskOffCount=0,
                neutralCount=0,
                topRegion=None,
            ),
            items=[],
        )

    scored = [_score_event(event, idx + 1) for idx, event in enumerate(payload.events)]
    scored.sort(key=lambda item: (item.impactScore, item.confidence), reverse=True)
    limited = scored[: payload.limit]

    bias_counter = Counter(item.marketBias for item in limited)
    region_counter = Counter(_normalize_text(item.region) for item in limited if item.region.strip())
    top_region = None
    if region_counter:
        key = region_counter.most_common(1)[0][0]
        top_region = key.title()

    avg_score = sum(item.impactScore for item in limited) / max(1, len(limited))

    return GameTheoryImpactResponse(
        summary=GameTheoryImpactSummary(
            analyzedEvents=len(payload.events),
            avgImpactScore=round(avg_score, 4),
            riskOnCount=int(bias_counter.get("risk_on", 0)),
            riskOffCount=int(bias_counter.get("risk_off", 0)),
            neutralCount=int(bias_counter.get("neutral", 0)),
            topRegion=top_region,
        ),
        items=limited,
    )


def _payoff_for_outcome(player: str, outcome: NashOutcomeInput) -> float:
    return float(outcome.payoffs.get(player, 0.0))


def _is_best_response(
    player: str, players: list[str], candidate: NashOutcomeInput, universe: list[NashOutcomeInput]
) -> bool:
    candidate_strategy = candidate.strategies.get(player, "")
    candidate_payoff = _payoff_for_outcome(player, candidate)
    for other in universe:
        if other.strategies.get(player, "") == candidate_strategy:
            continue
        same_others = True
        for actor in players:
            if actor == player:
                continue
            if other.strategies.get(actor, "") != candidate.strategies.get(actor, ""):
                same_others = False
                break
        if not same_others:
            continue
        if _payoff_for_outcome(player, other) > candidate_payoff + 1e-12:
            return False
    return True


def solve_nash_equilibria(payload: NashSolveRequest) -> NashSolveResponse:
    equilibria: list[NashOutcomeInput] = []
    for outcome in payload.outcomes:
        if all(_is_best_response(player, payload.players, outcome, payload.outcomes) for player in payload.players):
            equilibria.append(outcome)

    if equilibria:
        selected = max(equilibria, key=lambda o: sum(float(v) for v in o.payoffs.values()))
        return NashSolveResponse(equilibria=equilibria, selected=selected, status="equilibrium_found")

    best = max(payload.outcomes, key=lambda o: sum(float(v) for v in o.payoffs.values()))
    return NashSolveResponse(equilibria=[], selected=best, status="fallback_best_sum_payoff")


def build_transmission_paths(payload: TransmissionPathRequest) -> TransmissionPathResponse:
    region_symbols = _symbols_for_region(payload.region)
    arcs: list[TransmissionArc] = []
    channel_coefficients: dict[str, tuple[str, TransmissionDirection, float]] = {
        "energy": ("BRENT" if "BRENT" in region_symbols else region_symbols[0], "up", 1.0),
        "rates": ("US10Y" if "US10Y" in region_symbols else region_symbols[-1], "up", 0.85),
        "equity": (region_symbols[0], "down", 0.95),
        "fx": (region_symbols[-1], "up", 0.65),
    }
    for channel in payload.channels:
        rule = channel_coefficients.get(channel.lower())
        if rule is None:
            continue
        market, direction, weight = rule
        impact = _clamp(payload.impactScore * weight, 0.0, 1.0)
        if "ceasefire" in _normalize_text(payload.eventType) or "deescalation" in _normalize_text(payload.eventType):
            direction = cast(TransmissionDirection, "up" if channel.lower() == "equity" else "down")
            impact = _clamp(impact * 0.7, 0.0, 1.0)
        arcs.append(
            TransmissionArc(
                channel=channel.lower(),
                market=market,
                direction=direction,
                impact=round(impact, 4),
            )
        )
    return TransmissionPathResponse(region=payload.region, eventType=payload.eventType, arcs=arcs)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = percentile * (len(values) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return values[lo]
    weight = rank - lo
    return values[lo] * (1.0 - weight) + values[hi] * weight


def run_monte_carlo_simulation(payload: MonteCarloSimulationRequest) -> MonteCarloSimulationResponse:
    rng = random.Random(payload.seed)
    dt = 1.0 / 252.0
    terminals: list[float] = []
    for _ in range(payload.paths):
        price = payload.initialPrice
        for _ in range(payload.days):
            shock = rng.gauss(0.0, 1.0)
            drift_term = (payload.drift - 0.5 * payload.volatility * payload.volatility) * dt
            diffusion_term = payload.volatility * math.sqrt(dt) * shock
            price *= math.exp(drift_term + diffusion_term)
        terminals.append(price)
    terminals.sort()
    expected = sum(terminals) / len(terminals)
    sample = terminals[-5:] if len(terminals) >= 5 else terminals
    return MonteCarloSimulationResponse(
        paths=payload.paths,
        days=payload.days,
        p10=round(_percentile(terminals, 0.1), 4),
        p50=round(_percentile(terminals, 0.5), 4),
        p90=round(_percentile(terminals, 0.9), 4),
        expectedPrice=round(expected, 4),
        samplePathTerminal=[round(v, 4) for v in sample],
    )


STRATEGEM_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("S06", "Im Osten laermen, im Westen angreifen", ("diversion", "decoy", "misdirection", "loud rhetoric")),
    ("S08", "Offener Weg, heimlicher Marsch", ("mobilization", "costly signal", "exercise", "troops")),
    ("S05", "Bei Feuer plündern", ("exploit crisis", "opportunistic", "secondary strike", "during chaos")),
    ("S27", "Verruecktheit vortaeuschen", ("madman", "unpredictable", "irrational threat")),
)


def match_strategemes(payload: StrategemeMatchRequest) -> StrategemeMatchResponse:
    text = _normalize_text(payload.text)
    scored: list[StrategemeMatch] = []
    for code, title, cues in STRATEGEM_RULES:
        hits = sum(1 for cue in cues if cue in text)
        if hits == 0:
            continue
        confidence = _clamp(0.35 + 0.18 * hits, 0.0, 0.95)
        scored.append(StrategemeMatch(code=code, title=title, confidence=round(confidence, 4)))
    scored.sort(key=lambda item: item.confidence, reverse=True)
    top = scored[0] if scored else None
    return StrategemeMatchResponse(matches=scored, topMatch=top)


def build_timeline_regimes(payload: TimelineRegimeRequest) -> TimelineRegimeResponse:
    bands: list[TimelineRegimeBand] = []
    elevated = 0
    watch = 0
    calm = 0
    for item in payload.events:
        score = float(item.impactScore)
        if score >= 0.67:
            regime = "elevated"
            elevated += 1
        elif score >= 0.4:
            regime = "watch"
            watch += 1
        else:
            regime = "calm"
            calm += 1
        bands.append(TimelineRegimeBand(date=_normalize_date(item.date), regime=regime, impactScore=round(score, 4)))
    return TimelineRegimeResponse(bands=bands, elevatedCount=elevated, watchCount=watch, calmCount=calm)
