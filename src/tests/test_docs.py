import pathlib

import mktestdocs as mt  # type: ignore[import-untyped]
import pytest


@pytest.fixture(scope="module", params=[
    *pathlib.Path(".").glob("**/README.md"),
    *pathlib.Path("./docs").glob("**/*.md"),
], ids=str)
def markdown(request, toplevel_path):
    """All markdown docs."""
    yield toplevel_path / request.param


def test_readme(markdown):
    """Make sure README code is parsable."""
    mt.check_md_file(fpath=markdown, memory=True)


def test_readme_pytest(markdown, testdir):
    """Make sure README code runable as tests."""
    with open(markdown, 'r', encoding='utf-8') as f:
        text = f.read()

    code = mt.grab_code_blocks(text)
    testdir.makepyfile("\n".join(code))
    result = testdir.runpytest()
    outcomes = result.parseoutcomes()

    nouns = ["skipped", "failed", "errors", "xpassed", "xfailed", "warnings", "deselected"]
    assert outcomes.get("passed", 0) >= 0
    for n in nouns:
        assert outcomes.get(n, 0) == 0
