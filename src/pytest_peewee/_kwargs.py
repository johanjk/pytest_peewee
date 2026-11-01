from typing import ClassVar, Self, override
from urllib.parse import quote, urlencode

import pydantic


class BaseModel(pydantic.BaseModel):
    """Immutable, rejecting unknown fields."""

    model_config: ClassVar[pydantic.ConfigDict] = pydantic.ConfigDict(frozen=True, extra="forbid")


class UserSpec(BaseModel):
    """Connecting user.

    User.
        user[:password]
    """

    user: str
    password: str | None

    @pydantic.model_validator(mode="after")
    def check_user(self) -> Self:
        """Require a user with a password, it would otherwise be read as the user."""
        if self.password and not self.user:
            msg = "'password' requires 'user'"
            raise ValueError(msg)
        return self

    @override
    def __str__(self) -> str:
        """Percent-encoded, peewee decodes with 'unquote' (not 'unquote_plus')."""
        return ":".join(quote(p, safe="") for p in filter(None, [self.user, self.password]))


class HostSpec(BaseModel):
    """DB host.

    Single host, peewee does not support multiple.
        [host][:port]
    """

    host: str | None
    port: int | None

    @pydantic.model_validator(mode="after")
    def check_host_or_port(self) -> Self:
        """Require host or port, and a host expressible in an url."""
        if not self.host and not self.port:
            msg = "either 'host' or 'port' is required"
            raise ValueError(msg)
        if self.host and self.host.startswith("/"):
            msg = "unix socket hosts are not supported in urls, override 'setup_database' to pass them"
            raise ValueError(msg)
        return self

    @override
    def __str__(self) -> str:
        """Host as is, urlparse does not decode it; IPv6 in brackets."""
        host = f"[{self.host}]" if self.host and ":" in self.host else self.host
        return "".join(filter(None, [host, f":{self.port}" if self.port else None]))


class Database(BaseModel):
    """Database kwargs validation."""

    dbtype: str
    conn: HostSpec | None
    database: str | None
    cred: UserSpec | None
    params: dict[str, str] = pydantic.Field(default_factory=dict)

    @pydantic.field_validator("database")
    @classmethod
    def check_database(cls, value: str | None) -> str | None:
        """Peewee does not decode the path, so '?' and '#' cannot be escaped."""
        if value and ("?" in value or "#" in value):
            msg = "'database' cannot contain '?' or '#' in urls"
            raise ValueError(msg)
        return value

    @override
    def __str__(self) -> str:
        """Build connection string.

        dbtype://[userspec@][hostspec][/database][?paramspec]
            user[:password]
            [host][:port]
            name=value[&...]
        See:
            http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#db-url
        """
        conn_str = f"{self.dbtype}://"
        if (u := self.cred) and (us := str(u)):
            conn_str += f"{us}@"
        if h := self.conn:
            conn_str += str(h)
        if d := self.database:
            conn_str += f"/{d}"
        if p := self.params:
            conn_str += f"?{urlencode(p)}"
        return conn_str
