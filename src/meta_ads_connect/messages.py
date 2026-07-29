"""Walkthroughs for the things only the owner can do.

A Business Manager is the prerequisite the kit cannot create on the owner's
behalf — it needs their business details, and Meta has no endpoint that would
create one from a token that, by definition, does not exist yet. It is reached
from two directions: the browser flow hits it before any token exists, and
``repair-assets`` hits it afterwards. The walkthrough is written once here so
an owner meets the same instructions whichever way they arrived, and only the
closing step differs, because the command to come back to is not the same one.

The MCP login and re-consent instructions live here for the same reason: probe,
doctor and register-mcp all reach the same two states, and an owner must meet
the same words whichever command they happened to run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import MCP_NAME
from .exits import Exit

if TYPE_CHECKING:
    from .context import Context

#: What to do when the MCP server is registered but the Meta login has never
#: been completed. The action is a login, never a reinstall. The kit drives
#: the login itself; the pasteable line is the fallback for a machine without
#: the helper package.
MCP_LOGIN_ACTION = (
    "Log in to Meta: run `meta-ads-connect login` — your browser opens for a "
    "one-time approval; approve everything listed and do not deselect any ad "
    f"accounts or pages. Without the helper package, paste `claude mcp login {MCP_NAME}` "
    "into a terminal instead. Nothing needs reinstalling."
)

#: What to do when a login happened but the connection does not work — the
#: grant may not cover what the kit needs. One-step re-consent.
MCP_RECONSENT_ACTION = (
    "Log in again and approve everything listed: run `meta-ads-connect login`, and "
    "this time do not deselect any ad accounts or pages on Meta's screen. Without "
    f"the helper package, paste `claude mcp login {MCP_NAME}` into a terminal instead. "
    "Nothing needs reinstalling."
)

#: What to do when the `claude` command cannot be found. Registration and
#: login are written through that command, so the honest move is to route to
#: a place that has it rather than to guess.
CLAUDE_UNREACHABLE_ACTION = (
    "The `claude` command could not be found from here. Open a Claude Code "
    "session — the terminal or the desktop app both work — and ask Claude to "
    "connect your Meta ads from there: its own shell normally has the command. "
    "If it is still not found there, fully quit Claude and open it again — "
    "closing the window may not be enough."
)


def warnClaudeMissing(ctx: "Context", *, prevented: str) -> int:
    """The one way a missing `claude` command is reported, wherever it bites.

    Three subcommands hit this on different verbs; the shape — what was
    prevented, then the route that does not need the command — must not drift
    between them.
    """
    ctx.warn(f"The `claude` command is not on your PATH, so {prevented}.")
    ctx.warn(f"Next: {CLAUDE_UNREACHABLE_ACTION}")
    return int(Exit.CLAUDE_CLI_MISSING)

_NO_BUSINESS_MANAGER = """You do not have a Business Manager yet, and one is needed before an access token
can reach any ad account.

Creating it takes two minutes and is free:

  1. Go to https://business.facebook.com/overview and sign in.
  2. Click "Create account". Use your business name, your name, and your email.
  3. Once it exists, add your ad account to it under Settings → Accounts → Ad accounts.

Next: come back and run `meta-ads-connect {next_command}`."""


def noBusinessManager(*, next_command: str) -> str:
    """The walkthrough, closing on whichever command the owner should re-run."""
    return _NO_BUSINESS_MANAGER.format(next_command=next_command)
