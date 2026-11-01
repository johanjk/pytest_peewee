import re
from pathlib import Path
from typing import NamedTuple

import peewee as pw
import pytest
from rich.console import Console
from rich.style import Style
from rich.text import Text

from pytest_peewee import RollbackDatabase, fmt
from pytest_peewee.console import dialect, lint_messages
from pytest_peewee.lint_highlight import lint_message

from . import queries as qs


@pytest.fixture(scope="module")
def database_models():  # ruff: ignore[D103]
    yield [qs.OtherTable]


def test_query_lint_ok(database: RollbackDatabase):
    """Expect lint ok error."""
    assert qs.maybe_bad_query(False).lint()


class Malformed(NamedTuple):
    """Malformed query, the lint error it produces, and words its message must and must not color."""

    code: str
    query: pw.Query
    keywords: set[str]
    plain: set[str]


@pytest.fixture(params=[
    pytest.param(("RF01", qs.wrong_selector, {"FROM"}, {"Reference", "clause"}), id="RF01"),
    pytest.param(("CV05", qs.compare_to_null, {"NULL", "IS", "NOT"}, {"Comparisons"}), id="CV05"),
    pytest.param(("ST03", qs.unused_cte, set(), {"CTE", "Query"}), id="ST03"),
    pytest.param(("PRS", qs.unparsable_with_string, {"AND"}, {"Found", "unparsable"}), id="PRS"),
])
def malformed(request: pytest.FixtureRequest) -> Malformed:
    """Malformed queries, by the lint error they produce."""
    code, make_query, keywords, plain = request.param
    return Malformed(code, make_query(), keywords, plain)


def test_query_lint_err(capsys: pytest.CaptureFixture[str], database: RollbackDatabase, malformed: Malformed):
    """`.lint()` fails on malformed queries, printing the lint error with its SQL words colored."""
    assert not malformed.query.lint()

    stdout = capsys.readouterr().out
    print(stdout)
    assert f"{malformed.code}: " in Text.from_ansi(stdout).plain
    for keyword in malformed.keywords:
        assert re.search(rf"\x1b\[[;\d]*m{keyword}\x1b\[0m", stdout), keyword


def colored(text: Text) -> set[str]:
    """Words of `text` with a color."""
    return {text.plain[span.start:span.end].strip() for span in text.spans if Style.parse(str(span.style)).color} - {""}


def test_lint_message_coloring(database: RollbackDatabase, malformed: Malformed):
    """Lint messages keep their text; quoted SQL and SQL words are highlighted, other words are not."""
    _, warns = fmt.lint_query(malformed.query, database)
    (desc,) = {d for c, d in lint_messages(warns) if c == malformed.code}
    text = lint_message(desc, dialect(database))
    assert text.plain == desc
    assert malformed.keywords <= colored(text)
    assert not malformed.plain & colored(text)


def test_lint_message_positions(database: RollbackDatabase, malformed: Malformed):
    """With positions, each lint code starts with the spans of its occurrences."""
    _, warns = fmt.lint_query(malformed.query, database)
    plain = lint_messages(warns)
    positioned = lint_messages(warns, positions=True)
    assert [d for _, d in positioned] == [d for _, d in plain]
    for (code, _), (label, _) in zip(plain, positioned, strict=True):
        assert re.fullmatch(rf"(L\d+:\d+(-(L\d+:)?\d+)? )+{code}", label)


def test_agent_console(monkeypatch: pytest.MonkeyPatch):
    """`.print()` and `.lint()` print without colors for AI agents."""
    from pytest_peewee import console as c  # ruff: ignore[PLC0415]

    monkeypatch.setenv("AI_AGENT", "third-grade-boatswain")
    assert not c.colored(c.console())
    monkeypatch.delenv("AI_AGENT")
    assert c.colored(c.console())


def test_print(capsys: pytest.CaptureFixture[str], database: RollbackDatabase, monkeypatch: pytest.MonkeyPatch):
    """The query is printed formatted, numbered and framed, with the caller under it."""
    from pytest_peewee import console as c  # ruff: ignore[PLC0415]

    monkeypatch.setattr(c, "console", lambda _style="framed": Console(color_system=None, width=80))
    qs.maybe_bad_query(False).print()
    source = Path(__file__).read_text(encoding="utf-8").splitlines()
    lineno = next(i for i, line in enumerate(source, 1) if line.strip() == "qs.maybe_bad_query(False).print()")

    sql = [
        'WITH t2 AS (SELECT "sq"."x" FROM "othertable" AS "sq")',
        "",
        "SELECT",
        '    "t1"."id",',
        '    "t1"."x",',
        '    "t1"."y"',
        'FROM "othertable" AS "t1"',
        'INNER JOIN t2 ON ("t1"."x" = "t2"."x")',
    ]
    if isinstance(database, pw.MySQLDatabase):
        sql = [line.replace('"', "`") for line in sql]
    caller = f"Called from: {Path(__file__).relative_to(Path.cwd())}:{lineno}"
    body = [f"{i:>3} {line}".rstrip() for i, line in enumerate(sql, 1)] + [caller]
    expected = ["╭" + "─" * 78 + "╮", *(f"│ {line:<76} │" for line in body), "╰" + "─" * 78 + "╯"]
    assert capsys.readouterr().out.splitlines() == expected
