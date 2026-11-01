import pytest


@pytest.fixture(scope="module")
def database_string():
    """Sqlite file in a directory that does not exist."""
    yield "sqlite:////nonexistent-pytest-peewee/dir/db.sqlite"


def test_db(database):
    """Database can not be opened."""
