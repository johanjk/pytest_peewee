from pathlib import Path

import mktestdocs as mt  # type: ignore[import-untyped]
import peewee as pw
import pytest

ignore_patterns = {"dist", ".git", ".venv", "__pycache__"}

files = {
    *Path(".").glob("**/README.md"),
    *Path("./docs").glob("**/*.md"),
}
files = {p for p in files if not any(part in ignore_patterns for part in p.parts)}
files.remove(Path("./docs/fixtures.md"))


@pytest.fixture(params=files, ids=str)
def markdown(database: pw.Database, request: pytest.FixtureRequest, toplevel_path: Path):
    """All markdown docs."""
    yield toplevel_path / request.param


@pytest.fixture
def md_pytester(markdown: Path, pytester: pytest.Pytester):
    with open(markdown, 'r', encoding='utf-8') as f:
        text = f.read()

    code = mt.grab_code_blocks(text)
    pytester.makepyfile("\n".join(code))
    yield pytester


def test_readme(markdown: Path):
    """Make sure README code is parsable."""
    print(markdown)
    mt.check_md_file(fpath=markdown, memory=True)


def test_readme_pytest(md_pytester: pytest.Pytester):
    """Make sure README code runnable as tests."""
    result = md_pytester.runpytest()
    outcomes = result.parseoutcomes()

    nouns = ["skipped", "failed", "errors", "xpassed", "xfailed", "warnings", "deselected"]
    assert outcomes.get("passed", 0) >= 0
    for n in nouns:
        assert outcomes.get(n, 0) == 0
