import peewee as pw
import pytest

from pytest_peewee.redirect import install

prod = pw.SqliteDatabase(None)
analytics = pw.SqliteDatabase(None)


class Unbound(pw.Model):  # ruff: ignore[D101]
    pass


class Prod(pw.Model):  # ruff: ignore[D101]
    class Meta:  # ruff: ignore[D106]
        database = prod


class Analytics(pw.Model):  # ruff: ignore[D101]
    class Meta:  # ruff: ignore[D106]
        database = analytics


@pytest.fixture
def redirect(monkeypatch):
    """A `Redirect` of its own, replacing the session's for the test."""
    yield install(monkeypatch)


@pytest.fixture
def test_db():
    """Unconnected database to redirect to; resolution needs no connection."""
    yield pw.SqliteDatabase(":memory:")


def test_unbound_model(redirect, test_db):
    """Unbound models resolve to the active database only while active."""
    assert Unbound._meta.database is None
    with redirect.active(test_db):
        assert Unbound._meta.database is test_db
    assert Unbound._meta.database is None


def test_bound_model_is_redirected(redirect, test_db):
    """Models bound at import are redirected, and restored after."""
    with redirect.active(test_db):
        assert Prod._meta.database is test_db
    assert Prod._meta.database is prod


def test_mapping(redirect, test_db):
    """Mapped databases go to their own test database."""
    test_analytics = pw.SqliteDatabase(":memory:")
    with redirect.active(test_db, {analytics: test_analytics}):
        assert Analytics._meta.database is test_analytics
        assert Prod._meta.database is test_db


def test_schema_manager(redirect, test_db):
    """Schema operations (create_table, ...) follow the redirect."""
    with redirect.active(test_db):
        assert Prod._schema.database is test_db


def test_query(redirect, test_db):
    """Queries are redirected, even when bound."""
    with redirect.active(test_db):
        assert pw.Select().bind(prod)._database is test_db
        assert Prod.select()._database is test_db


def test_bind_in_frame_is_reverted(redirect, test_db):
    """Binds during a frame hold within it and are discarded after."""
    other = pw.SqliteDatabase(":memory:")
    with redirect.active(test_db):
        Prod.bind(other)
        assert Prod._meta.database is other
        assert Prod._schema.database is other
    assert Prod._meta.database is prod
    assert Prod._schema._database is None


def test_nested_frames(redirect, test_db):
    """The innermost frame wins; binds in an inner frame end with it."""
    inner = pw.SqliteDatabase(":memory:")
    other = pw.SqliteDatabase(":memory:")
    with redirect.active(test_db):
        with redirect.active(inner):
            assert Unbound._meta.database is inner
            Unbound.bind(other)
            assert Unbound._meta.database is other
        assert Unbound._meta.database is test_db


def test_model_created_in_frame(redirect, test_db):
    """Models defined during a frame keep working after it."""
    with redirect.active(test_db):

        class Late(pw.Model):
            pass

        assert Late._meta.database is test_db
    assert Late._meta.database is None


def test_installed_for_session():
    """Properties are installed by the plugin for the session, and pass lookups through without frames."""
    assert "database" in pw.Metadata.__dict__
    assert Prod._meta.database is prod


def test_nested_session(redirect, test_db, run_testpath):
    """A nested pytest session (pytester) has its own frames; the outer ones are back after it."""
    with redirect.active(test_db):
        run_testpath("redirect/unbound_model.py").assert_outcomes(passed=1)
        assert Unbound._meta.database is test_db


def test_hidden(redirect, test_db):
    """Frames of hidden owners are ignored."""
    with redirect.active(test_db, owner="some_fixture"):
        with redirect.hidden(frozenset({"some_fixture"})):
            assert Unbound._meta.database is None
            assert redirect.current() is None
        assert redirect.current() is test_db


proxy = pw.DatabaseProxy()


class Proxied(pw.Model):  # ruff: ignore[D101]
    class Meta:  # ruff: ignore[D106]
        database = proxy


@pytest.fixture
def initialized_proxy():
    """The proxy initialized with the 'prod' database, as an app does at startup."""
    proxy.initialize(prod)
    yield proxy
    proxy.initialize(None)


def test_proxy_mapped_by_itself(redirect, test_db):
    """A proxy can be mapped directly."""
    test_proxied = pw.SqliteDatabase(":memory:")
    with redirect.active(test_db, {proxy: test_proxied}):
        assert Proxied._meta.database is test_proxied


def test_proxy_mapped_by_its_database(redirect, test_db, initialized_proxy):
    """An initialized proxy matches by the database it points at."""
    test_prod = pw.SqliteDatabase(":memory:")
    with redirect.active(test_db, {prod: test_prod}):
        assert Proxied._meta.database is test_prod


def test_proxy_unmapped(redirect, test_db, initialized_proxy):
    """An unmapped proxy, initialized or not, goes to the active database."""
    with redirect.active(test_db):
        assert Proxied._meta.database is test_db
    proxy.initialize(None)
    with redirect.active(test_db):
        assert Proxied._meta.database is test_db


def test_model_query_of_mapped_model(redirect, test_db):
    """Queries of a mapped model, without a database of their own, use the model's test database."""
    test_analytics = pw.SqliteDatabase(":memory:")
    with redirect.active(test_db, {analytics: test_analytics}):
        assert Analytics.insert()._database is test_analytics
        assert Analytics.select()._database is test_analytics
        assert Prod.select()._database is test_db
