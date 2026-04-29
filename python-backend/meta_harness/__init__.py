"""Harness Feedback Loop — Meta-Harness inspired optimization (exec-17 Phase 5).

Automated harness engineering: analyze execution traces, propose improvements,
evaluate variants, promote the best configuration.

Reference: "Meta-Harness: End-to-End Optimization of Model Harnesses"
           (arxiv:2603.28052v1, Stanford/KRAFTON/MIT)

Modules:
  config.py    — Serialize/deserialize current harness configuration
  scorer.py    — Compute quality scores from audit data
  proposer.py  — LLM-based proposer: reads traces → suggests changes
  evaluator.py — Run agent variants against a search set
"""
