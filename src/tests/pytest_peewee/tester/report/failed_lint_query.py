import peewee as pw
import pytest


class Table(pw.Model):  # ruff: ignore[D101]
    field = pw.IntegerField()


@pytest.fixture(scope="module")
def database_models():  # ruff: ignore[D103]
    yield [Table]


def test_wrong_join(database):
    """Fails with a query that lints (RF01)."""
    a = Table.alias("t")
    q = Table.select().join(a.select(a.field), on=(Table.field == a.field))
    q.execute()
