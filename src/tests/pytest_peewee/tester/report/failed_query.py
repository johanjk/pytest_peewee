import peewee as pw
import pytest


class Unique(pw.Model):  # ruff: ignore[D101]
    x = pw.IntegerField(unique=True)


@pytest.fixture(scope="module")
def database_models():  # ruff: ignore[D103]
    yield [Unique]


def test_expected_error(database):
    """Expected errors produce no output."""
    Unique.create(x=1)
    with pytest.raises(pw.IntegrityError):
        Unique.create(x=1)


def test_unexpected_error(database):
    """Unexpected errors get the query in the report."""
    q = Unique.select()
    q.select_from(q.c.missing).execute()
