import pytest


@pytest.fixture(scope="module")
def database_kwargs():
    """Postgres without host or port."""
    yield {"dbtype": "postgres", "database": "db"}


def test_db(database):
    """Database is not configured correctly."""
