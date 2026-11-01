import peewee as pw
import pytest


class Parent(pw.Model):  # ruff: ignore[D101]
    name = pw.TextField()


class Child(pw.Model):  # ruff: ignore[D101]
    parent = pw.ForeignKeyField(Parent)


@pytest.fixture(scope="module")
def database_models():  # ruff: ignore[D103]
    yield [Child, Parent]  # created in dependency order


@pytest.fixture(scope="module")
def module_database(module_database):
    """Data shared by all tests in the module; no bind needed."""
    Parent.create(name="seed")
    yield module_database


def test_insert(database):
    """Seed is visible; inserts are rolled back after the test."""
    Child.create(parent=Parent.create(name="new"))
    assert Parent.select().count() == 2
    assert Child.select().count() == 1


def test_rolled_back(database):
    """Only the seed remains."""
    assert [p.name for p in Parent.select()] == ["seed"]
    assert Child.select().count() == 0
