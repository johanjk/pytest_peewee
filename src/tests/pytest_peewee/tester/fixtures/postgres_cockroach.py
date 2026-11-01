import peewee as pw
import playhouse.cockroachdb as pwc  # type: ignore[reportMissingTypeStubs]
import pytest


@pytest.fixture(params=[pw.PostgresqlDatabase(None), pwc.CockroachDatabase(None)], ids=["postgres", "cockroach"])
def database(request):
    """Unconnected databases; the dialect fixtures only check the class."""
    yield request.param


def test_postgres(postgres):
    """Runs on postgres only."""
    assert not isinstance(postgres, pwc.CockroachDatabase)


def test_cockroach(cockroach):
    """Runs on cockroach only."""
    assert isinstance(cockroach, pwc.CockroachDatabase)
