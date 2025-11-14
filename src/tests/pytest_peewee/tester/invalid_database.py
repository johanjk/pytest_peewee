import pytest


@pytest.fixture(scope="module", params=[
    "bananadb",
    "some-sql",
    "sqheavy",
])
def database_string(request):
    """Useless database strings."""
    yield request.param

def test_exception(database):
    """Expected to crash."""
    pass
