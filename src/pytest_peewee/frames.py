"""Tracebacks of failed queries without the frames running them: peewee's, this plugin's and the driver's."""

import site
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, get_args

import pytest

from . import console
from .isolation import exception_chain, failed_query

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest._code import Traceback

type TracebackStyle = Literal["short", "full"]


def traceback_style(config: pytest.Config) -> TracebackStyle:
    """The 'peewee_traceback' ini option; full with `--fulltrace`."""
    style = config.getini("peewee_traceback")
    if style not in get_args(TracebackStyle.__value__):
        msg = f"peewee_traceback must be one of {get_args(TracebackStyle.__value__)}, got {style!r}"
        raise pytest.UsageError(msg)
    return "full" if config.getoption("fulltrace", default=False) else style


_SITE = tuple(Path(p) for p in (*site.getsitepackages(), site.getusersitepackages()))
"""Directories of installed packages."""


def _installed(name: str, path: Path | str) -> bool:
    """Whether module `name` at `path` is installed code (packages, the standard library), not the project's."""
    return name.partition(".")[0] in sys.stdlib_module_names or any(Path(path).is_relative_to(p) for p in _SITE)


_PYTEST = ("_pytest", "pytest", "pluggy")
"""Packages hiding their own frames."""

FULL_TRACEBACK = "-o peewee_traceback=full"
HIDDEN_FRAMES = f"Traceback hides library frames; show them with {FULL_TRACEBACK}"
"""Note under failed queries whose traceback leaves out frames."""


def query_modules(traceback: Traceback) -> list[dict[str, Any]]:
    """Globals of the modules running the query in `traceback`: peewee, this plugin and installed code (drivers).

    Project code called back by them, e.g. a custom field, is left out.
    """
    found: dict[str, dict[str, Any]] = {}
    for entry in traceback:
        frame = entry.frame.raw
        name = frame.f_globals.get("__name__", "")
        if not name or name.partition(".")[0] in _PYTEST:
            continue
        if console.is_library(frame) or _installed(name, entry.path):
            found[name] = frame.f_globals
    return list(found.values())


@contextmanager
def hide_query_frames(excinfo: pytest.ExceptionInfo[BaseException]) -> Generator[None]:
    """Leave the frames running the failed query out of the traceback of `excinfo`, while its report is made.

    pytest rebuilds tracebacks from the raw frames, so they are hidden by `__tracebackhide__` in their module,
    which only hides in failed query tracebacks.
    The driver error peewee re-raises (the context of the failed query) is left out too: its frames are hidden,
    and its message is peewee's.
    """
    hiding = {id(exc) for exc in exception_chain(excinfo.value)}

    def hidden(info: pytest.ExceptionInfo[BaseException]) -> bool:
        return id(info.value) in hiding

    with pytest.MonkeyPatch.context() as mp:
        for module in query_modules(excinfo.traceback):
            if "__tracebackhide__" not in module:
                mp.setitem(module, "__tracebackhide__", hidden)
        exc = failed_query(excinfo.value)
        suppressed = exc.__suppress_context__ if exc else False
        if exc:
            exc.__suppress_context__ = True
        try:
            yield
        finally:
            if exc:
                exc.__suppress_context__ = suppressed
