"""Resilience primitives: error classification + rate-limit tracking.

Ports from ``_ref/hermes-agent`` adapted for the matrix LiteLLM-gateway
harness. Each module is pure (no I/O, no logging) so callers compose
their own retry / failover / rotation policies.
"""
