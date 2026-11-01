import re
from typing import TYPE_CHECKING

import peewee as pw
import pytest
from rich.text import Text


if TYPE_CHECKING:
    from pathlib import Path


def test_failed_query_report(run_testpath):
    """Only the failing test reports its formatted query."""
    result = run_testpath("report/failed_query.py")
    result.assert_outcomes(passed=1, failed=1)

    assert result.stdout.str().count("peewee query call") == 1
    result.stdout.fnmatch_lines([
        "*_ test_unexpected_error _*",
        "*- peewee query call -*",
        "*SELECT ?t1?.?missing?*",
        "*Error: *missing*",
    ])


def test_report_caller(copy_testers):
    """The report shows where in the test the query failed."""
    pytester = copy_testers({"test_failed.py": "report/failed_query.py"})
    lines = (pytester.path / "test_failed.py").read_text(encoding="utf-8").splitlines()
    lineno = next(i for i, line in enumerate(lines, 1) if ".execute()" in line and "missing" in line)
    result = pytester.runpytest("--color=no")
    report = result.stdout.str().split("peewee query call", 1)[1]
    assert f"Called from: test_failed.py:{lineno} " in report


def test_report_links_and_colors(copy_testers):
    """With colors, the caller's file name links (OSC 8) to its line, and the exception name is colored."""
    pytester = copy_testers({"test_failed.py": "report/failed_query.py"})
    lines = (pytester.path / "test_failed.py").read_text(encoding="utf-8").splitlines()
    lineno = next(i for i, line in enumerate(lines, 1) if ".execute()" in line and "missing" in line)
    result = pytester.runpytest("--color=yes")
    report = result.stdout.str().split("peewee query call", 1)[1]
    uri = f"{(pytester.path / 'test_failed.py').as_uri()}#L{lineno}"
    assert f";{uri}\x1b\\\x1b[36mtest_failed.py\x1b[0m\x1b]8;;\x1b\\:\x1b[33m{lineno}\x1b[0m" in report
    assert re.search(r"\x1b\[1;31m(Operational|Programming)Error\x1b\[0m: ", report)


def test_plain_report(copy_testers):
    """'peewee_report = plain' drops the panel and line numbers, keeping the formatted query."""
    pytester = copy_testers({"pyproject.toml": "report/report_plain.toml", "test_failed.py": "report/failed_query.py"})
    result = pytester.runpytest("--color=no")
    result.assert_outcomes(passed=1, failed=1)

    report = result.stdout.str().split("peewee query call", 1)[1].replace("`", '"')  # MySQL quoting
    assert "SELECT" in report
    assert not any(c in report for c in "╭│╰")
    assert '\nSELECT "t1"."missing"\nFROM (SELECT\n    "t2"."id",\n' in report  # formatted, no gutter or padding


@pytest.mark.parametrize(("color", "positions"), [("no", True), ("yes", False)])
def test_report_lint_positions(copy_testers, color: str, positions: bool):
    """Without colors, where the error is not highlighted, lint errors start with their line and column."""
    pytester = copy_testers({"test_failed.py": "report/failed_lint_query.py"})
    result = pytester.runpytest(f"--color={color}")
    result.assert_outcomes(failed=1)

    report = Text.from_ansi(result.stdout.str().split("peewee query call", 1)[1]).plain
    assert "RF01: " in report
    assert bool(re.search(r"\bL\d+:\d+-\d+ RF01: ", report)) == positions


def test_query_file_lint_positions(copy_testers):
    """The query file has the span (line, from and to column) of lint errors, the line of the file itself."""
    pytester = copy_testers({"test_failed.py": "report/failed_lint_query.py"})
    result = pytester.runpytest("--color=yes")
    path = pytester.path / "test-results/run-1/test_failed.py-test_wrong_join/query.sql"
    lines = path.read_text(encoding="utf-8").splitlines()

    match = re.search(r"^-- L(\d+):(\d+)-(\d+) RF01: ", "\n".join(lines), re.MULTILINE)
    assert match, result.stdout.str()
    line, start, end = map(int, match.groups())
    assert lines[line - 1][start - 1:end].replace("`", '"') == '"t"'  # the table of the reference, not in the FROM clause


def test_invalid_report(copy_testers):
    """Bad 'peewee_report' values are a usage error."""
    pytester = copy_testers({"pyproject.toml": "report/report_invalid.toml", "test_failed.py": "report/failed_query.py"})
    result = pytester.runpytest()
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "peewee_report must be one of" in result.stderr.str()


def query_file(result: pytest.RunResult, root: Path) -> Path:
    """The .sql file in the failure report; its full path without colors."""
    (line,) = [line for line in result.stdout.lines if line.startswith("Query file: ")]
    return root / line.removeprefix("Query file: ")


def test_query_file(copy_testers):
    """The failed query is written to the output folder, with the caller's full path and error as comments."""
    pytester = copy_testers({"test_failed.py": "report/failed_query.py"})
    result = pytester.runpytest("--color=no")
    result.assert_outcomes(passed=1, failed=1)

    path = query_file(result, pytester.path)
    assert path == pytester.path / "test-results/run-1/test_failed.py-test_unexpected_error/query.sql"
    text = path.read_text(encoding="utf-8").replace("`", '"')  # MySQL quoting
    assert text.startswith('SELECT "t1"."missing"\nFROM (SELECT\n')
    assert f"\n\n-- Called from: {pytester.path / 'test_failed.py'}:" in text
    assert "\n-- OperationalError: " in text or "\n-- ProgrammingError: " in text


def test_output_gitignore(copy_testers):
    """The output folder ignores itself in git."""
    pytester = copy_testers({"test_failed.py": "report/failed_query.py"})
    pytester.runpytest("--color=no")
    assert (pytester.path / "test-results/.gitignore").read_text(encoding="utf-8").splitlines()[-1] == "*"


def test_output_option(copy_testers):
    """'peewee_output' sets the output folder."""
    pytester = copy_testers({"pyproject.toml": "report/output_artifacts.toml", "test_failed.py": "report/failed_query.py"})
    result = pytester.runpytest("--color=no")
    assert query_file(result, pytester.path).parent.parent == pytester.path / "artifacts/run-1"


def test_runs(copy_testers):
    """Each run gets its own folder, linked by 'run-current'; the last 3 runs are kept, other artifacts too."""
    pytester = copy_testers({"test_failed.py": "report/failed_query.py"})
    output = pytester.path / "test-results"
    for name in ("run-1/test_a.py-test_a", "run-2/test_a.py-test_a", "run-10/test_a.py-test_a", "trace"):
        (output / name).mkdir(parents=True)
    result = pytester.runpytest("--color=no")
    assert query_file(result, pytester.path).parent.parent == output / "run-11"
    assert sorted(p.name for p in output.iterdir() if p.is_dir()) == ["run-10", "run-11", "run-2", "run-current", "trace"]
    assert (output / "run-current").resolve() == output / "run-11"


def test_nested_session_restores_helpers(copy_testers):
    """A nested session (pytester) leaves the outer session's helpers and redirect in place."""
    patched = (pw.Query.print, pw.Context.lint, pw.Metadata.__dict__["database"])
    pytester = copy_testers({"pyproject.toml": "report/report_plain.toml", "test_failed.py": "report/failed_query.py"})
    pytester.runpytest().assert_outcomes(passed=1, failed=1)
    assert (pw.Query.print, pw.Context.lint, pw.Metadata.__dict__["database"]) == patched


def test_query_link(copy_testers):
    """With colors, the file name is shown in cyan, a hyperlink (OSC 8) to the file."""
    pytester = copy_testers({"test_failed.py": "report/failed_query.py"})
    result = pytester.runpytest("--color=yes")
    path = pytester.path / "test-results/run-1/test_failed.py-test_unexpected_error/query.sql"
    assert "Query file: \x1b]8;id=" in result.stdout.str()
    assert f";{path.as_uri()}\x1b\\\x1b[36mquery.sql\x1b[0m\x1b]8;;\x1b\\" in result.stdout.str()


def test_fixture_query_files(copy_testers):
    """Queries failing in fixtures are reported under their phase, and written to 'query-<phase>.sql'."""
    pytester = copy_testers({"test_failed.py": "report/failed_fixture_query.py"})
    result = pytester.runpytest("--color=no")
    result.assert_outcomes(passed=1, errors=2)

    result.stdout.fnmatch_lines(["*- peewee query setup -*"])
    result.stdout.fnmatch_lines(["*- peewee query teardown -*"])
    run = pytester.path / "test-results/run-1"
    assert sorted(run.glob("*/*.sql")) == [
        run / "test_failed.py-test_setup/query-setup.sql",
        run / "test_failed.py-test_teardown/query-teardown.sql",
    ]
