import peewee as pw


class Unbound(pw.Model):  # ruff: ignore[D101]
    pass


def test_inner():
    """The outer session's redirect does not reach this session."""
    assert Unbound._meta.database is None
