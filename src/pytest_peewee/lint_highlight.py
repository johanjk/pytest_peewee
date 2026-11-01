"""Sqlfluff lint messages, with the SQL they mention highlighted."""

import re

from pygments.token import Token
from rich.syntax import Syntax
from rich.text import Text

# All-caps words in sqlfluff messages, highlighted when the SQL lexer knows them, e.g. "the FROM clause".
_CAPS = re.compile(r"\b[A-Z][A-Z_]+\b")
# Token types of SQL words; mysql has e.g. NULL as a constant. Plain names, like "CTE", are not SQL words.
_SQL_WORDS = (Token.Keyword, Token.Name.Constant, Token.Name.Builtin, Token.Operator.Word)
# SQL quoted in sqlfluff messages. Single quotes come from `repr`, with backslash escapes:
#   Reference '"t"."field"' ...   Found unparsable section: 'x = \'it\'\'s\' "t"'
# Double quotes end before a space, punctuation or the end, so they may hold quoted identifiers:
#   should use "IS" or "IS NOT".   Query defines CTE ""c"" but ...
_QUOTED = re.compile(
    r"""
        '(?P<single>(?:[^'\\]|\\.)*)'   # 'repr', with backslash escapes
      | "(?P<double>.+?)"               # "double", shortest match
        (?=[\s.,;:)]|$)                 #   followed by a space, punctuation or the end
    """,
    re.VERBOSE,
)


def _sql(code: str, dialect: str | None) -> Text:
    """`code` highlighted as SQL, on the default background."""
    text = Syntax(code, dialect or "SQL", background_color="default").highlight(code)
    text.rstrip()  # highlight adds a newline
    return text


def _escaped(text: Text, chars: str) -> Text:
    """`text` with a backslash before each of `chars`, keeping the styles."""
    offsets = [i for i, char in enumerate(text.plain) if char in chars]
    if not offsets:
        return text
    first, *parts = text.divide(offsets)
    for part in parts:
        first.append("\\")
        first.append_text(part)
    return first


def _keywords(message: str, dialect: str | None) -> Text:
    """`message` with its all-caps SQL words highlighted, other words left as they are."""
    lexer = Syntax("", dialect or "SQL").lexer
    text = Text()
    end = 0
    for word in _CAPS.finditer(message):
        text.append(message[end:word.start()])
        tokens = list(lexer.get_tokens(word[0])) if lexer else []
        if tokens and any(tokens[0][0] in kind for kind in _SQL_WORDS):
            text.append_text(_sql(word[0], dialect))
        else:
            text.append(word[0])
        end = word.end()
    text.append(message[end:])
    return text


def lint_message(message: str, dialect: str | None = None) -> Text:
    """Lint `message` of sqlfluff, with quoted SQL and SQL keywords highlighted.

    The text stays as sqlfluff wrote it, escapes included.
    """
    text = Text()
    end = 0
    for quoted in _QUOTED.finditer(message):
        text.append_text(_keywords(message[end:quoted.start()], dialect))
        if quoted["single"] is not None:
            code = re.sub(r"\\(.)", r"\1", quoted["single"])  # undo repr escapes
            text.append_text(Text.assemble("'", _escaped(_sql(code, dialect), "\\'"), "'"))
        else:
            text.append_text(Text.assemble('"', _sql(quoted["double"], dialect), '"'))
        end = quoted.end()
    text.append_text(_keywords(message[end:], dialect))
    return text
