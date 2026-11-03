"""Folder for failure artifacts, one subfolder per run."""

import re
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

import pytest


def output_dir(config: pytest.Config) -> Path:
    """Folder for failure artifacts, from the 'peewee_output' ini option, relative to the rootdir."""
    return config.rootpath / cast(str, config.getini("peewee_output"))


_RUN = re.compile(r"run-(\d+)")
_KEEP_RUNS = 3  # as pytest keeps its base temp dirs
_run_dir = pytest.StashKey[Path]()
_WORKER_RUN_DIR = "peewee_run_dir"
"""Key of the controller's run folder in the `workerinput` of pytest-xdist workers."""


def run_dir(config: pytest.Config) -> Path:
    """This run's `<output>/run-<N>` folder, made on first use; older runs beyond the last 3 are removed.

    `<output>/run-current` links to it. pytest-xdist workers use the folder of their controller.

    Other content of the output folder is kept. The output folder ignores itself in git.
    """
    workerinput: dict[str, Any] = getattr(config, "workerinput", {})
    if _run_dir not in config.stash and _WORKER_RUN_DIR in workerinput:
        config.stash[_run_dir] = Path(workerinput[_WORKER_RUN_DIR])
    if _run_dir not in config.stash:
        output = output_dir(config)
        output.mkdir(parents=True, exist_ok=True)
        gitignore = output / ".gitignore"
        if not gitignore.exists():  # as pytest does for its cache dir
            gitignore.write_text("# Created by pytest-peewee automatically.\n*\n", encoding="utf-8")

        runs = sorted(
            (int(match[1]), path) for path in output.iterdir()
            if path.is_dir() and (match := _RUN.fullmatch(path.name))
        )
        path = output / f"run-{runs[-1][0] + 1 if runs else 1}"
        path.mkdir()
        current = output / "run-current"  # as pytest's 'pytest-current'
        with suppress(OSError):  # no symlinks, e.g. on Windows without privileges
            current.unlink(missing_ok=True)
            current.symlink_to(path.name, target_is_directory=True)
        for _, old in runs[:max(0, len(runs) - (_KEEP_RUNS - 1))]:
            shutil.rmtree(old, ignore_errors=True)
        config.stash[_run_dir] = path
    return config.stash[_run_dir]


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node: Any) -> None:
    """pytest-xdist: make the run folder once, in the controller, for its workers to share."""
    node.workerinput[_WORKER_RUN_DIR] = str(run_dir(node.config))
