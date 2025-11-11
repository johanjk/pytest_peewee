import pytest


@pytest.fixture(scope="module", params=[
    "bananadb",
    "some-sql",
    "sqheavy",
])
def database_string(request):
    yield request.param

def test_exception(database):
    pass
