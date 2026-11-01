import pytest

SEEN = []  # keeps the databases alive, so their ids are unique


@pytest.fixture
def seen(setup_database):
    """Ids of all databases seen so far."""
    SEEN.append(setup_database)
    yield {id(db) for db in SEEN}
