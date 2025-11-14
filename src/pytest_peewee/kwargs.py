from typing import override
from urllib.parse import quote_plus, urlencode

import pydantic


class BaseModel(pydantic.BaseModel):  # noqa: D101
    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")


class UserSpec(BaseModel):
    """Connecting user.

    User.
        user[:password]
    """

    user: str
    password: str | None

    @override
    def __str__(self):
        return ":".join(map(quote_plus, filter(None, [self.user, self.password])))


class HostSpecBlock(BaseModel):
    """DB host.

    Single host.
        [host][:port][,...]
    """
    host: str | None
    port: str | None

    @pydantic.model_validator(mode="after")
    def check_host_or_port(self):
        """Require host or port."""
        if not self.host and not self.port:
            msg = "either 'host' or 'port' is required"
            raise ValueError(msg)
        return self

    @override
    def __str__(self):
        return "".join(filter(None, [
            quote_plus(self.host) if self.host else None,
            f":{self.port}" if self.port else None]
        ))


class Database(BaseModel):
    """Database kwargs validation."""

    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")

    dbtype: str
    conn: list[HostSpecBlock] | None
    database: str | None
    cred: UserSpec | None
    params: dict[str, str] = pydantic.Field(default_factory=dict)

    @override
    def __str__(self):
        """Build connection string.

        postgresql://[userspec@][hostspec][/dbname][?paramspec]
            user[:password]
            [host][:port][,...]
            name=value[&...]
        See:
            https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING-URIS
        """
        conn_str = f"{self.dbtype}://"
        if u := self.cred:
            conn_str += f"{u}@"
        if h := self.conn:
            conn_str += ",".join(map(str, h))
        if d := self.database:
            conn_str += f"/{d}"
        if p := self.params:
            conn_str += f"?{urlencode(p)}"
        return conn_str
