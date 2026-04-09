"""Control API router (mounted by agent/app.py).

Houses thin HTTP proxies + read-only query endpoints for the control-ui frontend.
Decoupling rule (D17): proxies in this package MUST NOT import from
ingestion/, retrieval/, or kg_pipeline/ — only via httpx HTTP calls.
"""

from agent.control.router import router

__all__ = ["router"]
