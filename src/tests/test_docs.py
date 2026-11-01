from pathlib import Path
from typing import TYPE_CHECKING

import mktestdocs as mt  # type: ignore[import-untyped]
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

TOPLEVEL = Path(__file__).parents[2]
"""Same as the `toplevel_path` fixture; params are needed at collection."""

# User docs with code; docs/fixtures.md only lists fixture signatures.
DOCS = [
    Path("README.md"),
    *sorted(
        path.relative_to(TOPLEVEL)
        for path in TOPLEVEL.glob("docs/*.md")
        if path.name != "fixtures.md"
    ),
]


@pytest.fixture(params=DOCS, ids=str)
def markdown(request: pytest.FixtureRequest, toplevel_path: Path) -> Iterator[str]:
    """Text of each markdown doc."""
    yield (toplevel_path / request.param).read_text(encoding="utf-8")


@pytest.fixture
def readme(toplevel_path: Path) -> Iterator[str]:
    """Text of the README."""
    yield (toplevel_path / "README.md").read_text(encoding="utf-8")


@pytest.fixture
def md_pytester(markdown: str, pytester: pytest.Pytester) -> Iterator[pytest.Pytester]:
    """Pytester with the 'python' code blocks of a doc as one test file."""
    pytester.makepyfile("\n".join(mt.grab_code_blocks(markdown)))
    yield pytester


@pytest.fixture
def readme_pytester(
    readme: str, pytester: pytest.Pytester, toplevel_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Iterator[pytest.Pytester]:
    """Pytester with the README's standalone 'py' example, on sqlite, 80 columns wide as the README shows it.

    The example is fenced as 'py', so it is left out of the 'python' blocks of `md_pytester`.
    """
    (example,) = mt.grab_code_blocks(readme, lang="py")
    pytester.makepyfile(test_example=example)
    conftest = toplevel_path / "src/tests/pytest_peewee/tester/docs/readme_sqlite_conftest.py"
    pytester.makeconftest(conftest.read_text(encoding="utf-8"))
    monkeypatch.setenv("COLUMNS", "80")
    yield pytester


def test_readme_failure_report(readme: str, readme_pytester: pytest.Pytester):
    """The README failure report and query file are what its standalone example produces."""
    result = readme_pytester.runpytest("--color=no")
    result.assert_outcomes(failed=1)

    # Query output matches README
    report = readme.split("peewee query call", 1)[1]
    expected = [line for line in report.splitlines() if line.startswith(("╭", "│", "╰", "Query file: "))]
    lines = result.stdout.lines
    start = lines.index(expected[0])
    assert lines[start:start + len(expected)] == expected

    # Query file content matches README
    query_file = readme_pytester.path / expected[-1].removeprefix("Query file: ")
    (sql,) = mt.grab_code_blocks(readme, lang="sql")
    assert query_file.read_text(encoding="utf-8") == sql.replace("/path/to/project", str(readme_pytester.path))


def test_readme_pytest(md_pytester: pytest.Pytester):
    """The 'python' code of each doc runs as tests, without failures, skips or warnings."""
    outcomes = md_pytester.runpytest().parseoutcomes()

    nouns = ["skipped", "failed", "errors", "xpassed", "xfailed", "warnings", "deselected"]
    for n in nouns:
        assert outcomes.get(n, 0) == 0
