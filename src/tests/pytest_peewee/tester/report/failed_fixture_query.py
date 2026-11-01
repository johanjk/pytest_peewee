import peewee as pw
import pytest


class Unique(pw.Model):  # ruff: ignore[D101]
    x = pw.IntegerField(unique=True)


@pytest.fixture(scope="module")
def database_models():  # ruff: ignore[D103]
    yield [Unique]


def failing_query():
    """Select a column that does not exist."""
    q = Unique.select()
    q.select_from(q.c.missing).execute()


@pytest.fixture
def fails_in_setup(database):
    """Query failing before the test runs."""
    failing_query()
    yield


@pytest.fixture
def fails_in_teardown(database):
    """Query failing after the test ran."""
    yield
    failing_query()


def test_setup(fails_in_setup):
    """Errors in setup, before running."""


def test_teardown(fails_in_teardown):
    """Passes, then errors in teardown."""
