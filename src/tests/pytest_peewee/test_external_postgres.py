import peewee as pw
import pytest

pytest.importorskip("psycopg")


@pytest.fixture(scope="module")
def database_string():
    """Hardcoded same as default test env is expected to generate."""
    yield "psycopg3://{user}:{password}@{host}:{port}/{database}".format(
        user="dbuser",
        password="secret",  # noqa: S106
        host="localhost",
        port=30000,
        database="test_db",
    )


def test_connect(database):
    """Can use external db."""
    assert isinstance(database, pw.PostgresqlDatabase)

    # Only an existing db can be opened
    with database.atomic():
        pass
