import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Backend"))

from Api import career_insights
from Services import pipeline_service
from Services.roadmap_utils import logical_item_key


class FakeStatement:
    def __init__(self):
        self.rows = None
        self.constraint = None

    def values(self, rows):
        self.rows = rows
        return self

    def on_conflict_do_nothing(self, *, constraint):
        self.constraint = constraint
        return self


class FakeSession:
    def __init__(self):
        self.executed = []
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement):
        self.executed.append(statement)

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_pipeline_builds_roadmap_tasks_with_shared_logical_key(monkeypatch):
    session = FakeSession()
    statement = FakeStatement()

    monkeypatch.setattr(
        pipeline_service,
        "pg_insert",
        lambda model: statement,
    )

    canonical_output = {
        "learning_roadmap": {
            "phases": [
                {
                    "phase_number": 1,
                    "phase_name": "Foundations",
                    "items": [
                        {
                            "skill_name": "Python",
                            "skill_uri": "https://example.test/python",
                            "priority": "high",
                        }
                    ],
                }
            ]
        }
    }

    pipeline_service._add_learning_tasks(session, 42, canonical_output)

    assert len(session.executed) == 1
    assert statement.constraint == "uq_learning_task_pipeline_run_logical_item"
    assert statement.rows == [
        {
            "pipeline_run_id": 42,
            "logical_item_key": logical_item_key(
                1, "Python", "https://example.test/python"
            ),
            "roadmap_phase_number": 1,
            "roadmap_phase_name": "Foundations",
            "skill_name": "Python",
            "skill_uri": "https://example.test/python",
            "priority": "high",
            "roadmap_item_data": canonical_output["learning_roadmap"]["phases"][0]["items"][0],
        }
    ]
    assert session.commits == 0
    assert session.rollbacks == 0


def test_roadmap_get_does_not_write_when_task_is_missing():
    class EmptyQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return []

    class ReadOnlyDatabase:
        def __init__(self):
            self.added = []
            self.executed = []
            self.commits = 0
            self.rollbacks = 0

        def query(self, *_args, **_kwargs):
            return EmptyQuery()

        def add(self, item):
            self.added.append(item)

        def execute(self, statement):
            self.executed.append(statement)

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    db = ReadOnlyDatabase()
    run = type(
        "Run",
        (),
        {
            "id": 42,
            "canonical_output": {
                "learning_roadmap": {
                    "phases": [
                        {
                            "phase_number": 1,
                            "phase_name": "Foundations",
                            "items": [{"skill_name": "Python"}],
                        }
                    ]
                }
            },
        },
    )()

    with pytest.raises(HTTPException) as exc:
        career_insights._learning_roadmap_response(db, run)

    assert exc.value.status_code == 503
    assert db.added == []
    assert db.executed == []
    assert db.commits == 0
    assert db.rollbacks == 0
