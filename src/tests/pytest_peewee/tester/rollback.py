import peewee as pw
import pytest


class InterfereTable(pw.Model):  # noqa: D101
    x = pw.IntegerField()


@pytest.fixture(scope="module")
def setup_database(setup_database):  # noqa: D103
    InterfereTable.bind(setup_database)
    # Must bind (this is pre-hook)

    InterfereTable.create_table()
    yield setup_database
    InterfereTable.drop_table()


def count_number(num: int, pos: bool = True) -> int:
    """Count rows where 'x' is/isn't num."""
    case = (InterfereTable.x == num) if pos else (InterfereTable.x != num)
    return InterfereTable.select(InterfereTable.x).where(case).count()


def no_interference(num: int):
    """Table data should be rolled back."""
    assert InterfereTable.table_exists()
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
    no_interference(0)
