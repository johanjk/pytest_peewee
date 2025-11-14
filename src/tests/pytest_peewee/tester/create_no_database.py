import peewee as pw
import pytest


@pytest.fixture(scope="module")
def database_string():
    """Hardcoded invalid user."""
    yield "psycopg3://{user}:{password}@{host}:{port}/{database}".format(
        user="postgres",
        password="hunter2",  # noqa: S106
        host="localhost",
        port=5432,
        database="postgres",
    )


def test_create_no_database(database):
    """A non-existing external database wont work."""
    assert isinstance(database, pw.PostgresqlDatabase)

    with (
        pytest.raises(pw.OperationalError),
        database.atomic()
    ):
        pass
