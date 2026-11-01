import peewee as pw


def test_rollback(database, run_testpath):
    """Rollback of inserts."""
    result = run_testpath("rollback/rollback.py")
    result.assert_outcomes(errors=0, passed=2)


def test_rollback_table(database, run_testpath):
    """Rollback of create_table."""
    result = run_testpath("rollback/rollback_table.py")
    if isinstance(database, pw.MySQLDatabase):
        # Mysql implicitly commits DDL; the isolation guard refuses it
        result.assert_outcomes(failed=2)
        result.stdout.fnmatch_lines(["*IsolationError: MySQL implicitly commits*"])
    else:
        result.assert_outcomes(failed=0, passed=2)
