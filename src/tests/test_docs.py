from pathlib import Path

import mktestdocs as mt  # type: ignore[import-untyped]
import pytest

files = {
    *Path(".").glob("**/README.md"),
    *Path("./docs").glob("**/*.md"),
}
# files.remove(Path("./docs/fixtures.md"))


@pytest.fixture(scope="module", params=files, ids=str)
def markdown(request: pytest.Request, toplevel_path: Path):
    """All markdown docs."""
    yield toplevel_path / request.param


@pytest.fixture(scope="module")
def md_testdir(markdown: Path, testdir: pytest.TestDir):
    with open(markdown, 'r', encoding='utf-8') as f:
        text = f.read()

    code = mt.grab_code_blocks(text)
    testdir.makepyfile("\n".join(code))
    yield testdir


def test_readme(markdown: Path):
    """Make sure README code is parsable."""
    mt.check_md_file(fpath=markdown, memory=True)


def test_readme_pytest(md_testdir: pytest.TestDir):
    """Make sure README code runnable as tests."""
    result = md_testdir.runpytest()
    outcomes = result.parseoutcomes()

    nouns = ["skipped", "failed", "errors", "xpassed", "xfailed", "warnings", "deselected"]
    assert outcomes.get("passed", 0) >= 0
    for n in nouns:
        assert outcomes.get(n, 0) == 0
