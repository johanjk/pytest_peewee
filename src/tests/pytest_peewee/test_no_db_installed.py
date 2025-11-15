import pytest

pytest.importorskip("psycopg")


def test_create_no_database(run_testpath):
    """A non-existing external database wont work."""
    result = run_testpath("create_no_database.py")
    outcomes = result.parseoutcomes()
    assert outcomes.get("xfailed") == 1 or outcomes.get("failed") == 1
