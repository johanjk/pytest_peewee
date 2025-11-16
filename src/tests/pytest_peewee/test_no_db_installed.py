import pytest

pytest.importorskip("psycopg")


def test_create_no_database(run_testpath):
    """A non-existing external database wont work."""
    result = run_testpath("create_no_database.py")
    print(result.parseoutcomes())
    outcomes = result.parseoutcomes()
    assert outcomes.get("xfailed") == 1 or outcomes.get("errors") == 1
    # will error with '--runxfail' flag
