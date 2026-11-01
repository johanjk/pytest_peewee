import pytest


@pytest.fixture(scope="module", params=[
    "bananadb",
    "some-sql",
    "sqheavy",
])
def database_string(request):
    """Database strings with unknown driver schemes."""
    yield request.param


def test_exception(database):
    """Errors in setup: not an unavailable database, but a broken configuration."""
