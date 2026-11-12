import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.elements import BooleanClauseList, BinaryExpression


BACKEND_PATH = Path(__file__).resolve().parents[2] / "Backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from Models import (  # noqa: E402
    CandidateProfile,
    Job,
    LearningTask,
    PipelineRun,
    Resume,
    SkillGap,
    User,
)
from Core.database import Base, get_db


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type, _compiler, **_kw):
    return "JSON"


MODEL_BY_TABLE = {
    model.__tablename__: model
    for model in (
        CandidateProfile,
        Job,
        LearningTask,
        PipelineRun,
        Resume,
        SkillGap,
        User,
    )
}


class FakeQuery:
    def __init__(self, db, entity, model, column=None):
        self.db = db
        self.entity = entity
        self.model = model
        self.column = column
        self.conditions = []
        self.joined_models = []
        self.limit_value = None
        self.offset_value = 0

    def filter(self, *conditions):
        self.conditions.extend(conditions)
        return self

    def join(self, model, *_args, **_kwargs):
        self.joined_models.append(model)
        return self

    def order_by(self, *_expressions):
        return self

    def offset(self, value):
        self.offset_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def _rows(self):
        rows = list(self.db.rows.get(self.model, []))
        rows = [
            row
            for row in rows
            if all(self._matches(condition, row) for condition in self.conditions)
        ]
        return rows[self.offset_value :] if self.limit_value is None else rows[
            self.offset_value : self.offset_value + self.limit_value
        ]

    def _value_for_column(self, column, row):
        model = MODEL_BY_TABLE[column.table.name]
        if model is self.model:
            target = row
        elif model in self.joined_models and isinstance(row, LearningTask):
            target = next(
                (
                    run
                    for run in self.db.rows.get(PipelineRun, [])
                    if run.id == row.pipeline_run_id
                ),
                None,
            )
        else:
            target = None
        return getattr(target, column.key) if target is not None else None

    def _matches(self, condition, row):
        if isinstance(condition, BooleanClauseList):
            results = [self._matches(item, row) for item in condition.clauses]
            return all(results) if condition.operator.__name__ == "and_" else any(results)
        if not isinstance(condition, BinaryExpression):
            return True

        left = self._value_for_column(condition.left, row)
        right = getattr(condition.right, "value", condition.right)
        operation = condition.operator.__name__
        if operation == "contains_op":
            return _contains_json(left, right)
        if operation in {"eq", "is_"}:
            return left == right
        if operation == "ne":
            return left != right
        if operation == "gt":
            return left > right
        if operation == "contains_op":
            return _contains_json(left, right)
        return True

    def all(self):
        return self._rows()

    def first(self):
        rows = self._rows()
        return rows[0] if rows else None

    def count(self):
        return len(self._rows())

    def scalar(self):
        rows = self._rows()
        if self.entity.name == "count":
            return len(rows)
        if self.entity.name == "avg":
            values = [getattr(row, self.column.key) for row in rows]
            values = [value for value in values if value is not None]
            return sum(values) / len(values) if values else None
        return None


class FakeSession:
    def __init__(self, rows=None):
        self.rows = {model: [] for model in MODEL_BY_TABLE.values()}
        for model, records in (rows or {}).items():
            self.rows[model] = list(records)
        self._next_ids = {}
        self.rollback_count = 0

    def query(self, entity):
        if isinstance(entity, type) and hasattr(entity, "__tablename__"):
            return FakeQuery(self, entity, entity)
        if hasattr(entity, "name") and hasattr(entity, "clauses"):
            column = list(entity.clauses)[0]
            model = MODEL_BY_TABLE[column.table.name]
            return FakeQuery(self, entity, model, column=column)
        model = MODEL_BY_TABLE[entity.table.name]
        return FakeQuery(self, entity, model, column=entity)

    def add(self, instance):
        model = type(instance)
        if getattr(instance, "id", None) is None:
            next_id = self._next_ids.get(model, 1)
            instance.id = next_id
            self._next_ids[model] = next_id + 1
        now = datetime.now(timezone.utc)
        for field in ("created_at", "updated_at"):
            if hasattr(instance, field) and getattr(instance, field) is None:
                setattr(instance, field, now)
        if isinstance(instance, LearningTask):
            if instance.status is None:
                instance.status = "not_started"
            if instance.progress is None:
                instance.progress = 0
            if instance.roadmap_item_data is None:
                instance.roadmap_item_data = {}
        self.rows.setdefault(model, []).append(instance)

    def execute(self, statement):
        for values in statement.rows:
            existing = next(
                (
                    task
                    for task in self.rows[LearningTask]
                    if task.pipeline_run_id == values["pipeline_run_id"]
                    and task.logical_item_key == values["logical_item_key"]
                ),
                None,
            )
            if existing is None:
                self.add(LearningTask(**values))

    def commit(self):
        return None

    def flush(self):
        return None

    def refresh(self, _instance):
        return None

    def rollback(self):
        self.rollback_count += 1


def _contains_json(actual, expected):
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return actual == expected
    return all(
        key in actual and _contains_json(actual[key], value)
        for key, value in expected.items()
    )


@pytest.fixture
def fake_session():
    return FakeSession


@pytest.fixture
def test_user():
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        password_hash="not-used",
    )


@pytest.fixture
def sqlite_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        User.__table__,
        Resume.__table__,
        CandidateProfile.__table__,
        PipelineRun.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine, tables=tables)
        engine.dispose()


@pytest.fixture
def api_client(sqlite_session):
    from Main import app

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: sqlite_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def auth_headers():
    from Core.security import create_access_token

    def headers_for(email):
        token = create_access_token({"sub": email})
        return {"Authorization": f"Bearer {token}"}

    return headers_for
