import pathlib

import pytest
from mktestdocs import check_md_file  # type: ignore[import-untyped]


@pytest.mark.parametrize("fpath", [
    *pathlib.Path(".").glob("**/README.md"),
    *pathlib.Path("./docs").glob("**/*.md")
], ids=str)
def test_readme(fpath):
    check_md_file(fpath=fpath, memory=True)
