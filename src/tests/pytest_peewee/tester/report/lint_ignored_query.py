import peewee as pw


class Table(pw.Model):  # ruff: ignore[D101]
    field = pw.IntegerField()


def test_lint_ignored(database):
    """'.lint()' passes, as its only lint error (RF01) is ignored."""
    a = Table.alias("t")
    q = Table.select().join(a.select(a.field), on=(Table.field == a.field))
    assert q.lint()
