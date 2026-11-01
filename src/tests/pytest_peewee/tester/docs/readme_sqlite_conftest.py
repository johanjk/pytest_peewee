import pytest


@pytest.fixture(scope="module")
def database_string():
    """Used by the readme tests, since they visualize sqlite output."""
    yield "sqlite:///:memory:"
