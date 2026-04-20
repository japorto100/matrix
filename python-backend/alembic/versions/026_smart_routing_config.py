"""agent.user_llm_settings.smart_routing — per-user cheap-vs-strong routing policy.

Adds a single JSONB column for the smart-routing configuration read by
:mod:`agent.llm.smart_routing`. Chose a separate column over stuffing the
policy into the existing ``utility_models`` / ``selected_models`` JSONB
fields because the semantics are distinct:

* ``selected_models`` — which models appear in the user's Model-Picker
* ``utility_models`` — per-role assignments (summarizer, stt, tts, ...)
* ``smart_routing`` — runtime routing policy (cheap-vs-strong heuristic)

Expected shape::

    {
      "enabled": true,
      "cheap_model": "gpt-4o-mini",
      "max_simple_chars": 160,
      "max_simple_words": 28
    }

Default ``{}`` means "feature off" — no behaviour change for existing
users. The Control-UI surfaces the toggle + model-dropdown + threshold
sliders (future frontend task, not this migration).

Cross-ref: `exec-a2fm-adaptive-routing.md`, `agent/llm/smart_routing.py`.

Revision ID: 026_smart_routing_config
Revises: 025_agent_ab_experiments
"""

from __future__ import annotations

from alembic import op

revision = "026_smart_routing_config"
down_revision = "025_agent_ab_experiments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE agent.user_llm_settings
        ADD COLUMN IF NOT EXISTS smart_routing JSONB NOT NULL DEFAULT '{}'::jsonb
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE agent.user_llm_settings
        DROP COLUMN IF EXISTS smart_routing
    """)
