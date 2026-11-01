def test_module_seed(run_testpath):
    """Module seed data is shared, test data is rolled back."""
    result = run_testpath("schema/schema.py")
    result.assert_outcomes(passed=2)


def test_session_scope(copy_testers):
    """With 'peewee_scope = session' all modules share one database."""
    pytester = copy_testers({
        "pyproject.toml": "schema/scope_session.toml",
        "conftest.py": "schema/seen_conftest.py",
        "test_a.py": "schema/seen_one.py",
        "test_b.py": "schema/seen_one.py",
    })
    pytester.runpytest().assert_outcomes(passed=2)


def test_module_scope(copy_testers):
    """By default every module gets its own database."""
    pytester = copy_testers({
        "conftest.py": "schema/seen_conftest.py",
        "test_a.py": "schema/seen_one.py",
        "test_b.py": "schema/seen_two.py",
    })
    pytester.runpytest().assert_outcomes(passed=2)


def test_invalid_scope(copy_testers):
    """Bad 'peewee_scope' values are a usage error."""
    pytester = copy_testers({"pyproject.toml": "schema/scope_invalid.toml", "test_db.py": "uses_database.py"})
    result = pytester.runpytest()
    assert result.ret != 0
    assert "peewee_scope must be one of" in result.stdout.str() + result.stderr.str()
