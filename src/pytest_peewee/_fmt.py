import functools
import warnings
from typing import Any, TypedDict, cast

import peewee as pw
import sqlfluff
from peewee import query_to_string  # type: ignore  # ruff: ignore[PGH003]


def dialect(database: pw.Database) -> str | None:
    """Format using a closest match dialect.

    See: https://docs.sqlfluff.com/en/stable/reference/dialects.html
    """
    match database:
        case pw.PostgresqlDatabase():
            return "postgres"
        case pw.MySQLDatabase():
            return "mysql"
        case pw.SqliteDatabase():
            return "sqlite"
        case _:
            msg = f"Database dialect '{type(database)}' not supported, falling back to base SQL."
            warnings.warn(msg, stacklevel=1)
    return None


def render(query: pw.Query, database: pw.Database) -> str:
    """Render query."""
    q = query_to_string(query)
    if not q:
        msg = f"Could not render query {query}"
        raise ValueError(msg)

    return format_sql(q, database)


def format_sql(sql: str, database: pw.Database) -> str:
    """Format raw SQL in the closest matching dialect."""
    return _fix(sql, dialect(database))


@functools.lru_cache(maxsize=256)
def _fix(sql: str, dialect: str | None) -> str:
    # sqlfluff is slow; failure reports render the same query more than once.
    return sqlfluff.fix(
        sql,
        dialect=dialect,
        rules=["capitalisation", "layout", "LT05", "LT09"],
        exclude_rules=[
            "CP01",
            "LT12",
            "RF06",
        ],
        fix_even_unparsable=True,
    )


class LintInfo(TypedDict):
    """Lint return of sqlfluff."""
    start_line_no: int
    start_line_pos: int
    end_line_no: int
    end_line_pos: int

    start_file_pos: int
    end_file_pos: int

    code: str
    description: str
    name: str
    warning: bool
    fixes: list[dict[str, Any]]


def lint_query(query: pw.Query, database: pw.Database) -> tuple[str, list[LintInfo]]:
    """Wrapper linting executed query."""
    s = render(query, database)
    return s, _lint(s, dialect(database))


@functools.lru_cache(maxsize=256)
def _lint(sql: str, dialect: str | None) -> list[LintInfo]:
    # the failure report lints the same query for its panel and its .sql file
    f = sqlfluff.lint(
        sql,
        dialect=dialect,
        rules=["all"],
        exclude_rules=[
            "ST05",  # Subquery to cte
            "ST06",  # Column order
            "ST07",  # USING
            "ST08",  # Distinct brackets
            "LT05",  # Line too long
            "LT09",  # Select targets should be on a new line
            "CP01",  # Capitalization
            "LT12",  # Newline at end
            "RF06",  # Quoted identifier
            "CV04",  # Peewee prefers COUNT(1) over COUNT(*)
        ],
    )
    return cast(list[LintInfo], f)  # ty: ignore[disjoint-cast]
