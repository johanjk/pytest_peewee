"""Database behavior while a test owns the connection.

`under_test` swaps the database's class for a subclass mixing in
`RollbackDatabase`, which keeps the shared connection open, attaches failed
queries to their exceptions for the failure report, and guards the isolation
transaction against commits. MySQL databases get `MySQLRollbackDatabase`, which
also guards against statements implicitly committing.
"""

import inspect
import os
import re
import warnings
from contextlib import ExitStack, contextmanager, suppress
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast, override

import peewee as pw
import playhouse  # type: ignore[reportMissingTypeStubs]
import pytest
from peewee import query_to_string

from . import _fmt as fmt

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

type IsolationPolicy = Literal["strict", "warn", "off"]
POLICIES: tuple[IsolationPolicy, ...] = ("strict", "warn", "off")

_LIBRARY_FILES = (
    pw.__file__,
    f"{Path(playhouse.__path__[0])}{os.sep}",
    f"{Path(__file__).parent}{os.sep}",
)
"""Warnings point at the first frame outside these: the code calling into peewee."""

FAILED_QUERY = "_pytest_peewee_query"
"""Exception attribute holding `(query, database)` of the failed query."""


def exception_chain(exc: BaseException | None) -> Iterator[BaseException]:
    """`exc` and its causes (or contexts), outermost first."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def failed_query(error: BaseException) -> BaseException | None:
    """`error`, or the first of its causes, with a failed query attached."""
    return next((exc for exc in exception_chain(error) if hasattr(exc, FAILED_QUERY)), None)


# MySQL/MariaDB statements causing an implicit commit, ending the test transaction.
# https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html
_IMPLICIT_COMMIT = re.compile(
    r"""^\s*(?:
        (?:CREATE|DROP)\s+(?!TEMPORARY\b)
        | (?:ALTER|TRUNCATE|RENAME|LOCK|UNLOCK|GRANT|REVOKE|ANALYZE|OPTIMIZE|REPAIR|BEGIN)\b
        | START\s+TRANSACTION\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def implicit_commit(sql: str) -> bool:
    """Whether MySQL implicitly commits when executing `sql`."""
    return _IMPLICIT_COMMIT.match(sql) is not None


class IsolationError(Exception):
    """Statement would break the per test rollback isolation."""


class IsolationWarning(UserWarning):
    """Statement breaks (or was prevented from breaking) test isolation."""


class RollbackDatabase(pw.Database):
    """Database owned by a test.

    Mixed into the database's own class by `under_test`, so `isinstance`
    checks against e.g. `pw.PostgresqlDatabase` keep working.
    """

    _ppw_closed: bool = False
    _ppw_isolated: int = 0
    _ppw_policy: IsolationPolicy = "strict"

    # Connection: the shared connection must stay open (sqlite memory), so
    # close/connect only toggle a flag.

    @override
    def connect(self, reuse_if_open: bool = False) -> bool:
        """Reopen the shared connection; only marks it open again."""
        if not self._ppw_closed:
            if reuse_if_open:
                return False
            msg = "Connection already opened."
            raise pw.OperationalError(msg)
        self._ppw_closed = False
        super().connect(reuse_if_open=True)
        return True

    @override
    def close(self) -> bool:
        """Mark the connection closed; the shared connection itself stays open."""
        was_open = not self._ppw_closed
        self._ppw_closed = True
        return was_open

    @override
    def is_closed(self) -> bool:
        """Whether the test closed the connection."""
        return self._ppw_closed

    # Isolation guards.

    @override
    def commit(self) -> None:
        """Commit, unless it would commit the isolation transaction; see `peewee_isolation`."""
        if self._ppw_isolated and self.in_transaction():
            reason = "COMMIT inside a test would commit the isolation transaction."
            if self._ppw_breach(reason, "COMMIT", skip_on_warn=True):
                return None
        return super().commit()

    def _ppw_breach(self, reason: str, sql: str, *, skip_on_warn: bool) -> bool:
        """Apply the isolation policy.

        Returns:
            True if the statement must be skipped.
        """
        __tracebackhide__ = True
        policy = self._ppw_policy
        if policy == "off":
            return False
        with suppress(Exception):  # formatting is best effort
            sql = fmt.format_sql(sql, self)
        msg = f"{reason}\n\n{sql}\n\nSet 'peewee_isolation = warn' or 'off' to allow it."
        if policy == "strict":
            raise IsolationError(msg)
        warnings.warn(msg, IsolationWarning, skip_file_prefixes=_LIBRARY_FILES)
        return skip_on_warn

    # Failure report.

    @override
    def execute(self, query: Any, **context_options: Any) -> Any:
        """Execute `query`; a failure carries it for the failure report."""
        __tracebackhide__ = True
        try:
            return super().execute(query, **context_options)
        except pw.DatabaseError as err:
            if not hasattr(err, FAILED_QUERY):
                setattr(err, FAILED_QUERY, (query, self))
                with suppress(Exception):  # the note is best effort
                    err.add_note(f"peewee query: {query_to_string(query)}")
            raise


class MySQLRollbackDatabase(RollbackDatabase, pw.MySQLDatabase):
    """MySQL/MariaDB database owned by a test, refusing implicitly committing statements."""

    @override
    def execute_sql(self, sql: str, params: Any = None, *args: Any, **kwargs: Any) -> Any:
        """Execute `sql`, unless MySQL would implicitly commit the isolation transaction."""
        __tracebackhide__ = True
        if self._ppw_isolated and self.in_transaction() and implicit_commit(sql):
            self._ppw_breach(
                "MySQL implicitly commits on this statement; the test transaction would end and "
                "everything after it in this test would be committed. Create tables once via the "
                "'database_models' fixture, or use 'create_table(temporary=True)'.",
                sql,
                skip_on_warn=False,
            )
        return super().execute_sql(sql, params, *args, **kwargs)


@cache  # one subclass per database class; stateless, the state is on the instance
def _test_class(base: type[pw.Database]) -> type[RollbackDatabase]:
    mixin = MySQLRollbackDatabase if issubclass(base, pw.MySQLDatabase) else RollbackDatabase
    return type(f"Test{base.__name__}", (mixin, base), {})


@contextmanager
def under_test(database: pw.Database) -> Generator[RollbackDatabase]:
    """Make `database` a `RollbackDatabase` while active. Reentrant.

    Yields:
        The same database object, with its class swapped.
    """
    if isinstance(database, RollbackDatabase):
        closed = database._ppw_closed  # ruff: ignore[SLF001]
        database._ppw_closed = False  # ruff: ignore[SLF001]
        try:
            yield database
        finally:
            database._ppw_closed = closed  # ruff: ignore[SLF001]
        return

    with pytest.MonkeyPatch.context() as mp:
        # State first, while the class has no defaults for it, so undo removes it again.
        for attr in inspect.get_annotations(RollbackDatabase):
            mp.setattr(database, attr, getattr(RollbackDatabase, attr), raising=False)
        mp.setattr(database, "__class__", _test_class(type(database)))
        yield cast(RollbackDatabase, database)


@contextmanager
def isolate(database: RollbackDatabase, policy: IsolationPolicy = "strict") -> Generator[None]:
    """Roll back everything done while active.

    Opens a transaction if none is active, otherwise a savepoint.

    Yields:
        Nothing.
    """
    outermost = database.transaction_depth() == 0

    with ExitStack() as stack:
        txn = stack.enter_context(
            database.transaction()
            if outermost else
            database.savepoint(),
        )

        @stack.callback  # runs before `txn` exits, which commits (or RELEASEs) it
        def rollback() -> None:
            database._ppw_closed = False  # ruff: ignore[SLF001]
            # a test may have closed it; rollback needs it open
            if outermost:
                while database.transaction_depth() > 1:
                    database.pop_transaction()  # left open by the test
                txn.rollback()  # and BEGIN, so exiting commits an empty transaction
            else:
                txn.rollback(begin=False)

        mp = stack.enter_context(pytest.MonkeyPatch.context())
        mp.setattr(database, "_ppw_isolated", database._ppw_isolated + 1)  # ruff: ignore[SLF001]
        mp.setattr(database, "_ppw_policy", policy)
        yield
