import peewee as pw
import pytest

from pytest_peewee import IsolationError, RollbackDatabase

analytics = pw.SqliteDatabase(None)
"""Production database of a second set of models; never connected in tests."""


class Event(pw.Model):  # ruff: ignore[D101]
    name = pw.TextField()

    class Meta:  # ruff: ignore[D106]
        database = analytics


@pytest.fixture(scope="module")
def database_redirect(database_from_env):
    """Analytics goes to its own test database; without ANALYTICS_* env vars an in-memory sqlite."""
    yield {analytics: database_from_env("ANALYTICS_")}


@pytest.fixture(scope="module")
def database_models():  # ruff: ignore[D103]
    yield [Event]


@pytest.fixture
def analytics_test(database_redirect):
    """The analytics test database."""
    yield database_redirect[analytics]


def test_redirected(database, analytics_test):
    """Mapped models use their test database, not 'database'; its tables are created by 'setup_schema'."""
    assert Event._meta.database is analytics_test
    assert Event._meta.database is not database
    assert analytics_test.table_exists("event")


@pytest.mark.parametrize("name", ["first", "second"])
def test_rolled_back(database, name):
    """Writes to a mapped test database are rolled back after each test, so each starts empty."""
    Event.create(name=name)
    assert Event.select().count() == 1


def test_under_test(database, analytics_test):
    """A mapped test database gets the commit guard and the failure report, as 'database' does."""
    assert isinstance(analytics_test, RollbackDatabase)
    with pytest.raises(IsolationError, match="COMMIT"):
        analytics_test.commit()


def test_from_env(database_from_env, monkeypatch, tmp_path):
    """'database_from_env' reads the prefixed env vars, like 'database' reads DBDRIVER, ..."""
    path = tmp_path / "reports.db"
    monkeypatch.setenv("REPORTS_DBDRIVER", "sqlite")
    monkeypatch.setenv("REPORTS_DBDATABASE", str(path))
    reports = database_from_env("REPORTS_")
    assert isinstance(reports, pw.SqliteDatabase)
    assert reports.database == str(path)
    assert not reports.is_closed()


def test_from_env_default(database_from_env):
    """Without env vars it is a separate in-memory sqlite database each time."""
    one = database_from_env("UNSET_ONE_")
    two = database_from_env("UNSET_TWO_")
    assert one.database == two.database == ":memory:"
    assert one is not two
