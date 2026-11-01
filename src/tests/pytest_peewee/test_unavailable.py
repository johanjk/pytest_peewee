import pytest


@pytest.fixture(params=["unavailable/unreachable_database.py", "unavailable/invalid_config.py"])
def unavailable(request: pytest.FixtureRequest, copy_testers):
    """Test file whose database can not be used."""
    yield copy_testers({"test_db.py": request.param})


@pytest.mark.parametrize(("config", "args", "outcome"), [
    (None, [], {"xfailed": 1}),
    (None, ["--runxfail"], {"errors": 1}),
    ("unavailable/unavailable_xfail.toml", [], {"xfailed": 1}),
    ("unavailable/unavailable_skip.toml", [], {"skipped": 1}),
    ("unavailable/unavailable_skip.toml", ["--runxfail"], {"skipped": 1}),
    ("unavailable/unavailable_fail.toml", [], {"errors": 1}),
])
def test_policy(unavailable: pytest.Pytester, copy_testers, config, args, outcome):
    """'peewee_unavailable' decides the outcome of tests without a usable database.

    In a subprocess: '--runxfail' on the outer session disables `pytest.xfail` for the whole process.
    """
    if config:
        copy_testers({"pyproject.toml": config})
    result = unavailable.runpytest_subprocess("-rA", *args)
    result.assert_outcomes(**outcome)
    result.stdout.fnmatch_lines(["*Could not connect*"])


def test_invalid_policy(copy_testers):
    """Bad 'peewee_unavailable' values are a usage error."""
    pytester = copy_testers({"pyproject.toml": "unavailable/unavailable_invalid.toml", "test_db.py": "uses_database.py"})
    result = pytester.runpytest()
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "peewee_unavailable must be one of" in result.stderr.str()


def test_unknown_driver(run_testpath):
    """An unknown driver scheme in 'database_string' is an error, whatever the 'peewee_unavailable' policy."""
    run_testpath("unavailable/unknown_driver.py").assert_outcomes(errors=3)
