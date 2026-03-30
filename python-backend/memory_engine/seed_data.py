"""Seed data: 36 Stratagems, 5 Regimes, TransmissionChannels, Institutions.

Based on the 36 Stratagems (Sānshíliù Jì) as mapped in docs/GAME_THEORY.md,
extended with geopolitical regime nodes and financial transmission channels.
"""
from __future__ import annotations

STRATAGEMS: list[dict] = [
    {"id": "S01", "name": "Cross the sea by fooling the sky", "category": "deception", "market_bias": "risk_on", "confidence_base": 0.72},
    {"id": "S02", "name": "Besiege Wei to rescue Zhao", "category": "indirect_action", "market_bias": "neutral", "confidence_base": 0.68},
    {"id": "S03", "name": "Kill with a borrowed knife", "category": "proxy_action", "market_bias": "risk_off", "confidence_base": 0.65},
    {"id": "S04", "name": "Wait at leisure while the enemy labors", "category": "attrition", "market_bias": "risk_off", "confidence_base": 0.71},
    {"id": "S05", "name": "Loot a burning house", "category": "opportunism", "market_bias": "risk_on", "confidence_base": 0.75},
    {"id": "S06", "name": "Clamor in the east, attack in the west", "category": "deception", "market_bias": "volatile", "confidence_base": 0.69},
    {"id": "S07", "name": "Create something from nothing", "category": "deception", "market_bias": "neutral", "confidence_base": 0.63},
    {"id": "S08", "name": "Openly repair the gallery roads, but sneak through the passage of Chencang", "category": "deception", "market_bias": "neutral", "confidence_base": 0.67},
    {"id": "S09", "name": "Watch the fires burning across the river", "category": "attrition", "market_bias": "risk_off", "confidence_base": 0.74},
    {"id": "S10", "name": "Hide a knife behind a smile", "category": "deception", "market_bias": "risk_on", "confidence_base": 0.66},
    {"id": "S11", "name": "Sacrifice the plum tree to preserve the peach tree", "category": "sacrifice", "market_bias": "risk_off", "confidence_base": 0.70},
    {"id": "S12", "name": "Take the opportunity to pilfer a goat", "category": "opportunism", "market_bias": "risk_on", "confidence_base": 0.73},
    {"id": "S13", "name": "Startle the snake by hitting the grass around it", "category": "intelligence", "market_bias": "volatile", "confidence_base": 0.62},
    {"id": "S14", "name": "Borrow a corpse to resurrect the soul", "category": "proxy_action", "market_bias": "neutral", "confidence_base": 0.61},
    {"id": "S15", "name": "Entice the tiger to leave its mountain lair", "category": "deception", "market_bias": "neutral", "confidence_base": 0.64},
    {"id": "S16", "name": "In order to capture, one must let loose", "category": "attrition", "market_bias": "volatile", "confidence_base": 0.68},
    {"id": "S17", "name": "Tossing out a brick to get a jade gem", "category": "negotiation", "market_bias": "neutral", "confidence_base": 0.65},
    {"id": "S18", "name": "Defeat the enemy by capturing their chief", "category": "direct_action", "market_bias": "risk_off", "confidence_base": 0.72},
    {"id": "S19", "name": "Remove the firewood from under the pot", "category": "attrition", "market_bias": "risk_off", "confidence_base": 0.71},
    {"id": "S20", "name": "Muddle the water to catch the fish", "category": "deception", "market_bias": "volatile", "confidence_base": 0.67},
    {"id": "S21", "name": "The golden cicada sheds its shell", "category": "evasion", "market_bias": "neutral", "confidence_base": 0.63},
    {"id": "S22", "name": "Shut the door to catch the thief", "category": "containment", "market_bias": "risk_off", "confidence_base": 0.70},
    {"id": "S23", "name": "Befriend a distant state while attacking a neighboring state", "category": "alliance", "market_bias": "neutral", "confidence_base": 0.66},
    {"id": "S24", "name": "Obtain safe passage to conquer the State of Guo", "category": "alliance", "market_bias": "neutral", "confidence_base": 0.65},
    {"id": "S25", "name": "Replace the beams with rotten timbers", "category": "deception", "market_bias": "risk_off", "confidence_base": 0.69},
    {"id": "S26", "name": "Point at the mulberry tree while cursing the locust tree", "category": "deception", "market_bias": "neutral", "confidence_base": 0.62},
    {"id": "S27", "name": "Play a sober-minded fool", "category": "deception", "market_bias": "volatile", "confidence_base": 0.64},
    {"id": "S28", "name": "Remove the ladder when the enemy has ascended to the roof", "category": "containment", "market_bias": "risk_off", "confidence_base": 0.72},
    {"id": "S29", "name": "Deck the tree with false blossoms", "category": "deception", "market_bias": "risk_on", "confidence_base": 0.66},
    {"id": "S30", "name": "Make the host and the guest exchange roles", "category": "reversal", "market_bias": "volatile", "confidence_base": 0.68},
    {"id": "S31", "name": "The beauty trap", "category": "deception", "market_bias": "risk_on", "confidence_base": 0.61},
    {"id": "S32", "name": "The empty fort strategy", "category": "deception", "market_bias": "neutral", "confidence_base": 0.69},
    {"id": "S33", "name": "Let the enemy's own spy sow discord in the enemy camp", "category": "intelligence", "market_bias": "volatile", "confidence_base": 0.65},
    {"id": "S34", "name": "Inflict injury on oneself to win the enemy's trust", "category": "deception", "market_bias": "neutral", "confidence_base": 0.63},
    {"id": "S35", "name": "Chain stratagems", "category": "complex", "market_bias": "volatile", "confidence_base": 0.70},
    {"id": "S36", "name": "If all else fails, retreat", "category": "evasion", "market_bias": "risk_off", "confidence_base": 0.75},
]

REGIMES: list[dict] = [
    {"id": "R_RISK_ON", "name": "Risk-On", "description": "Equities bid, credit tight, USD soft", "typical_duration_days": 90},
    {"id": "R_RISK_OFF", "name": "Risk-Off", "description": "Flight to safety, USD/JPY bid, EM sell-off", "typical_duration_days": 30},
    {"id": "R_STAGFLATION", "name": "Stagflation", "description": "High inflation + low growth, commodities bid", "typical_duration_days": 180},
    {"id": "R_DEFLATION", "name": "Deflation", "description": "Credit crunch, bonds bid, equities sold", "typical_duration_days": 60},
    {"id": "R_TRANSITION", "name": "Regime Transition", "description": "Mixed signals, high uncertainty, elevated volatility", "typical_duration_days": 21},
]

TRANSMISSION_CHANNELS: list[dict] = [
    {"id": "TC_OIL_USD", "from": "oil_price", "to": "usd_index", "direction": "inverse", "lag_days": 5},
    {"id": "TC_RATE_EM_FX", "from": "rate_hike", "to": "em_fx", "direction": "negative", "lag_days": 3},
    {"id": "TC_TARIFF_EQUITY", "from": "tariff_announcement", "to": "equity_index", "direction": "negative", "lag_days": 1},
    {"id": "TC_SANCTION_ENERGY", "from": "sanction", "to": "energy_commodities", "direction": "positive", "lag_days": 7},
    {"id": "TC_CONFLICT_GOLD", "from": "armed_conflict", "to": "gold", "direction": "positive", "lag_days": 2},
    {"id": "TC_ELECTION_BOND", "from": "election_outcome", "to": "sovereign_bond", "direction": "variable", "lag_days": 0},
    {"id": "TC_CB_POLICY_CREDIT", "from": "central_bank_policy", "to": "credit_spreads", "direction": "inverse", "lag_days": 14},
    {"id": "TC_CURRENCY_DEVALUE_EXPORT", "from": "currency_devaluation", "to": "export_equities", "direction": "positive", "lag_days": 10},
    {"id": "TC_TRADE_WAR_SUPPLY", "from": "trade_war", "to": "supply_chain_equities", "direction": "negative", "lag_days": 30},
    {"id": "TC_CYBER_INFRA", "from": "cyber_attack", "to": "infrastructure_equities", "direction": "negative", "lag_days": 0},
]

INSTITUTIONS: list[dict] = [
    {"id": "INST_FED", "name": "Federal Reserve", "type": "central_bank", "currency": "USD", "influence_score": 0.95},
    {"id": "INST_ECB", "name": "European Central Bank", "type": "central_bank", "currency": "EUR", "influence_score": 0.85},
    {"id": "INST_PBOC", "name": "People's Bank of China", "type": "central_bank", "currency": "CNY", "influence_score": 0.80},
    {"id": "INST_IMF", "name": "International Monetary Fund", "type": "multilateral", "currency": "SDR", "influence_score": 0.75},
    {"id": "INST_BIS", "name": "Bank for International Settlements", "type": "multilateral", "currency": "CHF", "influence_score": 0.70},
    {"id": "INST_OPEC", "name": "OPEC+", "type": "cartel", "currency": "USD", "influence_score": 0.78},
    {"id": "INST_BOJ", "name": "Bank of Japan", "type": "central_bank", "currency": "JPY", "influence_score": 0.72},
    {"id": "INST_WB", "name": "World Bank", "type": "multilateral", "currency": "USD", "influence_score": 0.65},
]
