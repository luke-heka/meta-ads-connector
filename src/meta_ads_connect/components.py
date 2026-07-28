"""Detecting the state of each moving part.

``probe`` and ``doctor`` ask the same questions and differ only in what they do
with the answers — probe collapses them to one exit code, doctor prints them
one per line. Both read from here so they can never disagree.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .config import CLI_VERSION, MCP_NAME, MCP_URL
from .context import Context
from .exits import Exit
from .graph import GraphAuthError, GraphError, GraphNetworkError, GraphRateLimitError
from .processes import CommandNotFound

_SEMVER = re.compile(r"\b(\d+\.\d+\.\d+)\b")


def parseVersion(output: str) -> str:
    """The version in ``--version`` output, or "" when there isn't a recognisable one.

    Empty is deliberately not None: it means "it ran, but did not identify
    itself", which must never read as "it is not installed".
    """
    match = _SEMVER.search(output)
    return match.group(1) if match else ""


# --- Ads CLI ---------------------------------------------------------------


@dataclass(frozen=True)
class CliStatus:
    installed: bool
    #: None means "installed, but it did not tell us which version". That is
    #: not the same as absent and must never be treated as such.
    version: str | None
    path: str | None
    #: True when the CLI lives outside the kit's own environment — the owner
    #: installed it themselves. Left alone rather than fought with.
    external: bool = False

    @property
    def pinned(self) -> bool:
        return self.installed and self.version == CLI_VERSION


def detectCli(ctx: Context) -> CliStatus:
    """Is the Ads CLI installed, and at what version?

    The kit's own environment is checked first. A ``meta`` already on PATH is
    accepted as a second choice so a partially-complete setup is finished
    rather than duplicated.
    """
    managed = ctx.paths.cli_binary
    if managed.exists():
        works, version = _probeBinary(ctx, str(managed))
        if works:
            return CliStatus(installed=True, version=version, path=str(managed))

    external = ctx.runner.which("meta")
    if external:
        works, version = _probeBinary(ctx, external)
        if works:
            return CliStatus(installed=True, version=version, path=external, external=True)

    return CliStatus(installed=False, version=None, path=None)


def _probeBinary(ctx: Context, binary: str) -> tuple[bool, str | None]:
    """Does this binary run, and what version does it claim?

    ``--version`` is not something the shipped Ads CLI has been confirmed to
    support — its docs and its binary are known to disagree elsewhere. So a
    failed ``--version`` falls back to ``--help``: a binary that runs is
    installed, even if it will not say which version it is. Concluding
    "not installed" from an unrecognised flag would trigger a reinstall of
    something already present, which is the exact failure this kit exists to
    prevent.
    """
    try:
        result = ctx.runner.run([binary, "--version"], timeout=30)
    except CommandNotFound:
        return (False, None)
    if result.ok:
        return (True, parseVersion(result.output))

    try:
        fallback = ctx.runner.run([binary, "--help"], timeout=30)
    except CommandNotFound:
        return (False, None)
    return (True, None) if fallback.ok else (False, None)


# --- MCP server ------------------------------------------------------------


class McpState(Enum):
    REGISTERED = "registered"
    MISSING = "missing"
    #: The `claude` command is not on PATH, so registration cannot be read or
    #: written. Reported honestly rather than guessed at.
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class McpStatus:
    state: McpState
    detail: str


def detectMcp(ctx: Context) -> McpStatus:
    try:
        result = ctx.runner.run(["claude", "mcp", "list"], timeout=60)
    except CommandNotFound:
        return McpStatus(
            state=McpState.UNKNOWN,
            detail="The `claude` command is not on your PATH, so MCP registration cannot be checked.",
        )
    if not result.ok:
        return McpStatus(
            state=McpState.UNKNOWN,
            detail="Claude Code could not list its MCP servers.",
        )

    listing = result.output
    if MCP_URL in listing or re.search(rf"^\s*{re.escape(MCP_NAME)}\b", listing, re.MULTILINE):
        return McpStatus(state=McpState.REGISTERED, detail=f"Registered as `{MCP_NAME}`.")
    return McpStatus(state=McpState.MISSING, detail="Meta's Ads MCP server is not registered.")


# --- Token, against Meta ---------------------------------------------------


class TokenState(Enum):
    LIVE = "live"
    REJECTED = "rejected"
    RATE_LIMITED = "rate_limited"
    UNREACHABLE = "unreachable"
    #: Meta answered, but with something we could not interpret.
    ERROR = "error"


@dataclass(frozen=True)
class AdAccount:
    id: str
    name: str

    def describe(self) -> str:
        return f"{self.name} ({self.id})" if self.name else self.id


def describeAccounts(accounts: Sequence[AdAccount], *, limit: int = 3) -> str:
    """Name a handful of accounts without turning a message into a wall.

    Shared so an owner with twelve ad accounts is told the same thing in the
    same shape whichever command they happened to run.
    """
    named = ", ".join(account.describe() for account in accounts[:limit])
    if len(accounts) <= limit:
        return named
    return f"{named} and {len(accounts) - limit} more"


@dataclass(frozen=True)
class TokenCheck:
    state: TokenState
    accounts: tuple[AdAccount, ...]
    detail: str


@dataclass(frozen=True)
class TokenVerdict:
    """What a non-live token state means to a caller.

    ``blocking`` separates "your setup is wrong" from "Meta was unhelpful just
    now": a rate limit or a dropped connection says nothing about the setup and
    must never read as a broken one.
    """

    exit_code: Exit
    blocking: bool


#: One table, because ``probe`` and ``doctor`` both classify these four states
#: and a disagreement between them is exactly the bug this prevents — the same
#: revoked token has to be fatal in both, and the same rate limit harmless in
#: both. The prose stays with each command; only the verdict is shared.
TOKEN_VERDICTS: dict[TokenState, TokenVerdict] = {
    TokenState.REJECTED: TokenVerdict(exit_code=Exit.TOKEN_REJECTED, blocking=True),
    TokenState.RATE_LIMITED: TokenVerdict(exit_code=Exit.RATE_LIMITED, blocking=False),
    TokenState.UNREACHABLE: TokenVerdict(exit_code=Exit.NETWORK_ERROR, blocking=False),
    TokenState.ERROR: TokenVerdict(exit_code=Exit.META_ERROR, blocking=True),
}


def checkToken(ctx: Context, token: str) -> TokenCheck:
    """Ask Meta whether this token works, right now.

    A live authenticated call, never a marker file. A token revoked at Meta's
    end has to present as disconnected, and only Meta can say.
    """
    try:
        payload = ctx.graph.get(
            "/me/adaccounts",
            token=token,
            params={"fields": "id,name,account_status", "limit": "100"},
        )
    except GraphAuthError as exc:
        return TokenCheck(
            state=TokenState.REJECTED,
            accounts=(),
            detail=f"Meta rejected the stored token: {exc.message}",
        )
    except GraphRateLimitError as exc:
        return TokenCheck(
            state=TokenState.RATE_LIMITED,
            accounts=(),
            detail=f"Meta is rate limiting this account: {exc.message}",
        )
    except GraphNetworkError as exc:
        return TokenCheck(
            state=TokenState.UNREACHABLE,
            accounts=(),
            detail=f"Could not reach Meta: {exc.message}",
        )
    except GraphError as exc:
        return TokenCheck(
            state=TokenState.ERROR,
            accounts=(),
            detail=f"Meta returned an error: {exc.message}",
        )

    accounts = parseAdAccounts(payload)
    if not accounts:
        # The token authenticated but sees nothing. That is an assignment
        # problem, not a credential problem, and repair-assets is the fix.
        return TokenCheck(
            state=TokenState.LIVE,
            accounts=(),
            detail="The token works, but no ad accounts are assigned to it yet.",
        )
    return TokenCheck(
        state=TokenState.LIVE,
        accounts=accounts,
        detail=f"{len(accounts)} ad account{'s' if len(accounts) != 1 else ''} reachable.",
    )


def parseAdAccounts(payload: Mapping[str, Any]) -> tuple[AdAccount, ...]:
    rows = payload.get("data")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return ()
    accounts: list[AdAccount] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        identifier = row.get("id") or row.get("account_id")
        if not identifier:
            continue
        accounts.append(AdAccount(id=str(identifier), name=str(row.get("name") or "")))
    return tuple(accounts)
