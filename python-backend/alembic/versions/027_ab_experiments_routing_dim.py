"""agent.ab_experiments — routing dimension (ADR-001 G4).

Adds a first-class routing-decision dimension to the A/B experiment
ledger so fitness-regression analysis can decouple runner-variant
effects (LangGraph vs SimpleLoop) from smart-routing effects
(cheap-vs-primary). Without these columns, the two factors are
confounded whenever smart-routing is enabled on self-selected users —
exactly the case when rollout starts.

Columns added to ``agent.ab_experiments``:

* ``routing_used`` — ``BOOLEAN NOT NULL DEFAULT FALSE``. TRUE iff the
  turn was silently switched from primary to a cheap model by
  :mod:`agent.llm.smart_routing`.
* ``routing_reason`` — ``TEXT NULL``. Mirror of the ``llm.routing_reason``
  span attribute; one of ``simple_turn`` / ``complex_heuristic`` /
  ``config_absent`` / ``config_disabled`` / ``no_cheap_configured`` /
  ``no_cheap_credentials`` / ``not_evaluated``.
* ``routing_picked_model`` — ``TEXT NULL``. The model that was actually
  called (cheap-model id when ``routing_used`` is TRUE). Present
  regardless of ``routing_used`` for joinable ops-visibility.

Index ``ix_ab_experiments_routing`` on ``(experiment_id, variant,
routing_used)`` makes the harness's bucketed fitness queries fast.

Cross-ref: ``specs/execution/exec-16-llm-provider-gateway.md §2.D``,
``docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md``.

Revision ID: 027_ab_experiments_routing_dim
Revises: 026_smart_routing_config
"""

from __future__ import annotations

from alembic import op

revision = "027_ab_experiments_routing_dim"
down_revision = "026_smart_routing_config"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE agent.ab_experiments
            ADD COLUMN IF NOT EXISTS routing_used BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS routing_reason TEXT NULL,
            ADD COLUMN IF NOT EXISTS routing_picked_model TEXT NULL
        """
    )
    op.create_index(
        "ix_ab_experiments_routing",
        "ab_experiments",
        ["experiment_id", "variant", "routing_used"],
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ab_experiments_routing",
        "ab_experiments",
        schema=SCHEMA,
        if_exists=True,
    )
    op.execute(
        """
        ALTER TABLE agent.ab_experiments
            DROP COLUMN IF EXISTS routing_picked_model,
            DROP COLUMN IF EXISTS routing_reason,
            DROP COLUMN IF EXISTS routing_used
        """
    )
