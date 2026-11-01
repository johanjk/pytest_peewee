import peewee as pw
import pytest


class RebindTable(pw.Model):  # ruff: ignore[D101]
    x = pw.IntegerField()


other = pw.SqliteDatabase(":memory:")


@pytest.fixture(scope="module")
def database_models():
    """Tables created once for the module."""
    yield [RebindTable]


def test_rebind(database):
    """Binding during a test is respected for that test."""
    RebindTable.bind(other)
    assert RebindTable._meta.database is other


def test_rebind_is_reverted(database):
    """Runs after `test_rebind`: its binding does not leak."""
    assert RebindTable._meta.database is database
