import peewee as pw
import pytest


class Missing(pw.Model):
    """Table never created."""
    name = pw.TextField()


@pytest.mark.parametrize("name", ["a b", "a-b"])
def test_missing(database, name):
    """Ids that clean up to the same name, each failing with its own query."""
    Missing.select().where(Missing.name == name).execute()
