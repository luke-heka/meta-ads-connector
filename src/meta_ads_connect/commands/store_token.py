"""``store-token`` — write a minted token to disk, safely.

The token arrives on stdin, never as a command-line argument: argv is visible
to every process on the machine and lands in shell history. It is written to a
file only the owner can read, and this command prints nothing that contains it.
"""

from __future__ import annotations

from typing import TextIO

from ..config import TOKEN_ENV_VAR
from ..context import Context
from ..exits import Exit
from ..tokens import describePermissions, writeToken


def runStoreToken(ctx: Context, *, source: TextIO) -> int:
    """Read a token from ``source`` and store it. ``source`` is normally stdin."""
    raw = source.read()
    token = raw.strip()
    if not token:
        ctx.warn(
            "No token was supplied.\n"
            f"Next: pipe the token in, for example: echo $TOKEN | meta-ads-connect store-token"
        )
        return int(Exit.USAGE)

    # Set before any output, so an unexpected failure below cannot echo it.
    ctx.secret = token

    if _looksLikeEnvLine(token):
        # Tolerate a whole `META_ACCESS_TOKEN=…` line being pasted in — a very
        # easy mistake to make, and storing it verbatim would break silently.
        token = token.split("=", 1)[1].strip().strip("'\"")
        ctx.secret = token

    target = writeToken(ctx.paths, token)

    ctx.say(f"Saved your Meta access token to {target}.")
    ctx.say(
        f"{describePermissions(ctx.paths)} "
        "Nothing was added to your shell profile and nothing was put in your keychain — "
        f"deleting {ctx.paths.root} removes it completely."
    )
    ctx.say("Next: run `meta-ads-connect probe` to confirm Meta accepts it.")
    return int(Exit.OK)


def _looksLikeEnvLine(value: str) -> bool:
    return value.startswith(TOKEN_ENV_VAR) and "=" in value
