import warnings

import peewee as pw
import sqlfluff
from peewee import query_to_string  # type: ignore


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

    return sqlfluff.fix(
        q,
        dialect=dialect(database),
        rules=["capitalisation", "layout", "structure", "LT05"],
        exclude_rules=["CP01", "LT12", "RF06"],
        fix_even_unparsable=True,
    )


def lint_query(query: pw.Query, database: pw.Database) -> tuple[str, list[dict[str, str]]]:
    """Wrapper linting executed query."""
    s = render(query, database)
    f = sqlfluff.lint(
        s,
        dialect=dialect(database),
        rules=["all"],
        exclude_rules=[
            "CP01",  # Capitalization
            "LT12",  # Newline at end
            "RF06",  # Quoted identifier
        ],
    )
    return s, f
