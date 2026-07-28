"""Reading, writing and redacting the system user token.

The token has spend authority. It is written once, read per invocation, and
never rendered — not to stdout, not to stderr, not inside an error message the
kit relays from somewhere else. :func:`redact` is the last line of that
defence and is applied to whole output buffers, not to individual fields.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

from .config import TOKEN_ENV_VAR, Paths

#: Directory and file modes. Owner-only, both.
DIR_MODE = 0o700
FILE_MODE = 0o600

#: Redaction stands in for any secret we scrub.
REDACTED = "[redacted]"

_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")

#: Meta access tokens are long opaque strings. System user tokens seen in the
#: wild start ``EAA``; the generic fallback catches anything else long enough to
#: be a credential so a rotated format does not silently start leaking.
_TOKEN_SHAPES = (
    re.compile(r"EAA[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\b[A-Za-z0-9_\-]{60,}\b"),
)


def readToken(paths: Paths) -> str | None:
    """The stored token, or None when there isn't one.

    A file that exists but holds no usable token reads as None rather than as
    an error — a half-written file is the same problem as no file, and has the
    same fix.
    """
    try:
        contents = paths.env_file.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError, UnicodeDecodeError):
        return None

    for line in contents.splitlines():
        match = _ENV_LINE.match(line)
        if not match or match.group(1) != TOKEN_ENV_VAR:
            continue
        value = match.group(2).strip().strip("'\"")
        if value:
            return value
    return None


def writeToken(paths: Paths, token: str) -> Path:
    """Write ``token``, replacing any previous one. Returns the file path.

    The file is created with mode 600 from the outset rather than being
    chmod'd afterwards, so it is never briefly world-readable.
    """
    token = token.strip()
    if not token:
        raise ValueError("refusing to store an empty token")

    paths.root.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
    os.chmod(paths.root, DIR_MODE)

    target = paths.env_file
    # Replace, never append: a second token in the same file would be silently
    # ignored by the reader and leave the owner with a stale credential.
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"{TOKEN_ENV_VAR}={token}\n")
    os.chmod(target, FILE_MODE)
    return target


def tokenFileMode(paths: Paths) -> int | None:
    """Permission bits of the token file, or None if it isn't there."""
    try:
        return stat.S_IMODE(paths.env_file.stat().st_mode)
    except FileNotFoundError:
        return None


def directoryMode(paths: Paths) -> int | None:
    try:
        return stat.S_IMODE(paths.root.stat().st_mode)
    except FileNotFoundError:
        return None


def formatMode(mode: int | None) -> str:
    return "unknown" if mode is None else format(mode, "o")


def describePermissions(paths: Paths) -> str:
    """One sentence telling the owner their token is theirs alone.

    Said the same way wherever a token is written, so the reassurance does not
    drift between the two commands that write one.
    """
    return (
        f"Only your user account can read it ({formatMode(tokenFileMode(paths))} in a "
        f"{formatMode(directoryMode(paths))} folder)."
    )


def redact(text: str, *, token: str | None = None) -> str:
    """Remove the token from ``text``.

    Removes the known token when one is supplied, and anything token-shaped
    regardless — the second pass is what protects error strings we did not
    write, such as a Graph error echoing back the credential it rejected.
    """
    if token:
        text = text.replace(token.strip(), REDACTED)
    for shape in _TOKEN_SHAPES:
        text = shape.sub(REDACTED, text)
    return text


def cliEnvironment(token: str, base: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for one Ads CLI invocation.

    Per-invocation and in-memory only. Nothing is written to a shell profile,
    which is what keeps the kit removable without residue.
    """
    env = dict(os.environ if base is None else base)
    env[TOKEN_ENV_VAR] = token
    return env
