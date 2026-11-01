"""Redirect peewee database lookups to the active test database.

While a frame is active, models, schema managers and queries resolve their
database through properties installed on the peewee classes:

* unbound, or bound before the frame (e.g. at import): the mapped test database,
  or the frame's database.
* model binds made during the frame are respected, but kept in an overlay that is
  discarded when the frame ends, so they never leak into other tests.
* query binds are always redirected.
"""

from collections.abc import Generator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import peewee as pw

if TYPE_CHECKING:
    import pytest

type DatabaseMap = Mapping[Any, pw.Database]


@dataclass(eq=False, slots=True)
class _Frame:
    database: pw.Database
    mapping: DatabaseMap
    owner: str | None
    overlay: dict[tuple[int, str], tuple[object, Any]] = field(default_factory=dict)


@dataclass(eq=False, slots=True)
class Redirect:
    """Redirect frames of one pytest session, made by `install`; the plugin keeps it in the config stash."""

    frames: list[_Frame] = field(default_factory=list)
    hidden_owners: frozenset[str] = frozenset()
    visible: tuple[_Frame, ...] = field(default=(), init=False, repr=False)
    """Frames not hidden; recomputed on change, as every database lookup reads it."""

    def _update(self) -> None:
        self.visible = tuple(f for f in self.frames if f.owner not in self.hidden_owners)

    def current(self) -> pw.Database | None:
        """Database of the innermost visible frame."""
        return self.visible[-1].database if self.visible else None

    @contextmanager
    def hidden(self, owners: frozenset[str]) -> Generator[None]:
        """Ignore frames owned by `owners` while active, e.g. for tests not requesting them."""
        previous = self.hidden_owners
        self.hidden_owners = owners
        self._update()
        try:
            yield
        finally:
            self.hidden_owners = previous
            self._update()

    @contextmanager
    def active(
        self, database: pw.Database, mapping: DatabaseMap | None = None, owner: str | None = None,
    ) -> Generator[pw.Database]:
        """Redirect all peewee database lookups to `database` while active.

        Args:
            database: Default target for unbound and unmapped models and queries.
            mapping: Optional `{source_database: test_database}` for multi-database
                projects. Unmapped databases resolve to `database`.
            owner: Fixture name owning the frame; see `hidden`.

        Yields:
            The target database.
        """
        frame = _Frame(database, mapping or {}, owner)
        self.frames.append(frame)
        self._update()
        try:
            yield database
        finally:
            self.frames.remove(frame)
            self._update()


def _resolve(frame: _Frame, db: Any, *, none_to_active: bool) -> Any:
    if db is None:
        return frame.database if none_to_active else None
    # A proxy matches by itself, or by the database it was initialized with.
    candidates = [db, db.obj] if isinstance(db, pw.Proxy) and db.obj is not None else [db]
    for candidate in candidates:
        if candidate is frame.database or any(candidate is v for v in frame.mapping.values()):
            return candidate
        with suppress(TypeError):  # unhashable
            if candidate in frame.mapping:
                return frame.mapping[candidate]
    return frame.database


def _redirected(redirect: Redirect, attr: str, *, none_to_active: bool, overlay: bool) -> property:
    def fget(obj: object) -> Any:
        value = obj.__dict__.get(attr)
        frames = redirect.visible
        if not frames:
            return value

        key = (id(obj), attr)
        for frame in reversed(frames):
            if key in frame.overlay:
                bound = frame.overlay[key][1]
                if bound is not None:
                    return bound  # explicit bind during the frame is respected
                break
        if value is None and isinstance(obj, pw.BaseQuery) and (model := obj.__dict__.get("model")) is not None:
            # A model query without its own database uses its model's: peewee only fills it in when
            # this is falsy, so answering with the active database would skip mapped models.
            value = model._meta.database  # ruff: ignore[SLF001] - peewee's documented model metadata
        return _resolve(frames[-1], value, none_to_active=none_to_active)

    def fset(obj: object, value: Any) -> None:
        # First assignment (object construction) always goes to the instance, so
        # objects created during a frame stay valid after it ends.
        frames = redirect.visible
        if overlay and frames and attr in obj.__dict__:
            frames[-1].overlay[(id(obj), attr)] = (obj, value)
        else:
            obj.__dict__[attr] = value

    return property(fget, fset)


@dataclass(frozen=True, slots=True)
class _Patch:
    target: type
    """Peewee class getting the property."""
    attr: str
    none_to_active: bool
    """An unbound (None) database resolves to the active one."""
    overlay: bool
    """Binds made during a frame are kept in its overlay, and reverted after it."""


_PATCHES = (
    _Patch(pw.Metadata, "database", none_to_active=True, overlay=True),
    _Patch(pw.SchemaManager, "_database", none_to_active=False, overlay=True),
    # Queries are short-lived; binding them only needs redirecting, not reverting.
    _Patch(pw.BaseQuery, "_database", none_to_active=True, overlay=False),
)


def install(mp: pytest.MonkeyPatch) -> Redirect:
    """Install properties redirecting to a new `Redirect` on the peewee classes, undone by `mp`.

    One per pytest session, so a nested session (pytester) has its own frames.
    """
    redirect = Redirect()
    for p in _PATCHES:
        prop = _redirected(redirect, p.attr, none_to_active=p.none_to_active, overlay=p.overlay)
        mp.setattr(p.target, p.attr, prop, raising=False)
    return redirect
