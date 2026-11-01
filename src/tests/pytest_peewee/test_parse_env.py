import pytest

from pytest_peewee._parse_env import parse_env


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch):
    """A few env vars, and one known to be unset."""
    monkeypatch.setenv("DBHOST", "db.local")
    monkeypatch.setenv("X", "x")
    monkeypatch.setenv("db_user", "bob")
    monkeypatch.delenv("PEEWEE_UNSET", raising=False)


@pytest.mark.parametrize(("value", "expected"), [
    ("$DBHOST", "db.local"),
    ("${DBHOST}", "db.local"),
    ("$X", "x"),  # single character
    ("$db_user", "bob"),  # lowercase
    ("${DBHOST}:5432", "db.local:5432"),  # braces end the name
    ("$PEEWEE_UNSET", ""),  # unset: empty, so the default applies
    ("plain", "plain"),
    ("$", "$"),
    ("$5", "$5"),  # no name
])
def test_values(env, value, expected):
    """Env var references are replaced in values."""
    assert parse_env({"key": value}) == {"key": expected}


def test_input_unchanged(env):
    """A new dict is returned; the given one keeps its references."""
    kwargs = {"host": "$DBHOST"}
    assert parse_env(kwargs) == {"host": "db.local"}
    assert kwargs == {"host": "$DBHOST"}
