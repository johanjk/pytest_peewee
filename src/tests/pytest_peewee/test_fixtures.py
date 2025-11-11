import peewee as pw
import pytest


def test_fixtures(
    database_string, setup_database, database,
    query_error, use_database, query_helpers,
):
    """Fixtures exists and patches are active."""


def has_helper(exp: bool) -> pw.Query:
    q = pw.Select(columns=[pw.Value(1)])
    assert hasattr(q, "print") == exp
    assert hasattr(q, "lint") == exp
    return q


def test_no_helpers(pre_hook_database):
    """Hooked print/lint should not exist yet."""
    has_helper(False)


def test_helpers(post_hook_database):
    """Hooked print/lint should exist."""
    q = has_helper(True)
    q.print()
    assert q.lint()


def test_fixture_database(
    pre_hook_database, post_hook_database,
    pre_transaction_database, post_transaction_database,
):
    """Database hook fixtures."""


@pytest.fixture(params=[
    "query_error",
    "use_database",
    "query_helpers",
])
def hooks(request):
    yield request.param


def test_no_hooks(request, pre_hook_database, hooks):
    assert hooks not in request.fixturenames


def test_hooks(request, post_hook_database, hooks):
    assert hooks in request.fixturenames
    assert request.getfixturevalue(hooks)
