import peewee as pw


def test_rollback(run_testpath):
    """Rollback of inserts."""
    result = run_testpath("rollback.py")
    result.assert_outcomes(errors=0, passed=2)


def test_rollback_table(database, run_testpath):
    """Rollback of create_table."""
    result = run_testpath("rollback_table.py")
    if isinstance(database, pw.MySQLDatabase):
        # Mysql does not support rollback of table create
        result.assert_outcomes(failed=1, passed=1)
    else:
        result.assert_outcomes(failed=0, passed=2)
