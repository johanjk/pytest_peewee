import peewee as pw
import pytest


class DDLTable(pw.Model):  # ruff: ignore[D101]
    pass


@pytest.fixture(scope="module")
def setup_database(setup_database):  # ruff: ignore[D103]
    DDLTable.bind(setup_database)
    # Must bind (this is pre-hook)
    DDLTable.drop_table()
    yield setup_database
    if setup_database.is_connection_usable():
        DDLTable.drop_table()


def test_insert_one(database):
    """Expect no test interference between cases."""
    DDLTable.create_table(safe=False)


def test_insert_two(database):
    """Interference case."""
    DDLTable.create_table(safe=False)
