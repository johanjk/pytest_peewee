def test_invalid_database(run_testpath):
    """A non-existing external database wont work."""
    result = run_testpath("invalid_database.py")
    result.assert_outcomes(errors=3)
