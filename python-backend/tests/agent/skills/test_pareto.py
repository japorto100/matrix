from __future__ import annotations

from agent.skills import pareto


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Conn:
    def __init__(self, results):
        self._results = list(results)

    def execute(self, _sql):
        return _Rows(self._results.pop(0))

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None


def test_compute_pareto_includes_audit_only_filesystem_skills(monkeypatch):
    conn = _Conn(
        [
            [],  # agent.agent_skills is empty for filesystem skills
            [],  # skill_refined counts
            [
                ("global:market-research", 3, 3, 0.0),
                ("global:risk-assessment", 1, 1, 0.0),
            ],
            [],  # disabled skills
        ]
    )
    monkeypatch.setattr(pareto.psycopg, "connect", lambda *_args, **_kwargs: conn)

    scores = pareto.compute_pareto(min_usage=0)

    by_id = {score.skill_id: score for score in scores}
    assert set(by_id) == {"global:market-research", "global:risk-assessment"}
    assert by_id["global:market-research"].db_id is None
    assert by_id["global:market-research"].usage_count == 3
    assert by_id["global:market-research"].success_rate == 1.0


def test_compute_pareto_respects_min_usage_for_audit_only_skills(monkeypatch):
    conn = _Conn(
        [
            [],
            [],
            [("global:market-research", 1, 1, 0.0)],
            [],
        ]
    )
    monkeypatch.setattr(pareto.psycopg, "connect", lambda *_args, **_kwargs: conn)

    assert pareto.compute_pareto(min_usage=2) == []
