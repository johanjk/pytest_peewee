import peewee as pw
import pytest


class InterfereTable(pw.Model):  # ruff: ignore[D101]
    x = pw.IntegerField()


@pytest.fixture(scope="module")
def setup_database(setup_database):  # ruff: ignore[D103]
    InterfereTable.bind(setup_database)
    # Must bind (this is pre-hook)

    InterfereTable.create_table()
    yield setup_database
    if setup_database.is_connection_usable():
        assert InterfereTable.table_exists()
        InterfereTable.drop_table()


@pytest.fixture
def database(database):  # ruff: ignore[D103]
    assert InterfereTable.table_exists()
    yield database


def count_number(num: int, pos: bool = True) -> int:
    """Count rows where 'x' is/isn't num."""
    matching = (InterfereTable.x == num)
    case = matching == pos
    return InterfereTable.select(InterfereTable.x).where(case).count()


def no_interference(num: int):
    """Table data should be rolled back."""
    assert count_number(num) == 0
    assert count_number(num, False) == 0
    InterfereTable.insert(x=num).execute()
    assert count_number(num) == 1
    assert count_number(num, False) == 0


def test_insert_one(database):
    """Expect no test interference between cases."""
    no_interference(1)


def test_insert_two(database):
    """Interference case."""
    no_interference(2)
