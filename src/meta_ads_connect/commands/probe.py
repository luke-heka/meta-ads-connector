"""``probe`` — the live connection check. Always the first action.

This is the actual fix for the most-reported symptom: Claude restarting a setup
the owner already finished. The verdict is a live authenticated call to Meta,
never a marker file, so a token revoked at Meta's end presents as disconnected
rather than being assumed good.

Every outcome names the next action, because a verdict nobody can act on is
just a different way of saying "it is broken".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..components import (
    TOKEN_VERDICTS,
    CliStatus,
    McpState,
    McpStatus,
    TokenCheck,
    TokenState,
    checkToken,
    describeAccounts,
    detectCli,
    detectMcp,
)
from ..config import CLI_VERSION
from ..context import Context
from ..exits import Exit
from ..tokens import readToken


#: What the owner is told for each way a token can fail to answer. The exit
#: code and whether it is fatal live in ``TOKEN_VERDICTS``, shared with
#: ``doctor``; only the wording is chosen here.
_TOKEN_PROSE: dict[TokenState, tuple[str, str]] = {
    TokenState.REJECTED: (
        "Your saved Meta access token is no longer valid — Meta has rejected it.",
        "Run `meta-ads-connect mint-token` to mint and save a fresh one. Nothing else needs redoing.",
    ),
    TokenState.RATE_LIMITED: (
        "Meta is rate limiting this account, so the connection could not be confirmed.",
        "Wait a few minutes and run `meta-ads-connect probe` again. Nothing needs reinstalling.",
    ),
    TokenState.UNREACHABLE: (
        "Meta could not be reached, so the connection could not be confirmed.",
        "Check your internet connection and run `meta-ads-connect probe` again.",
    ),
    TokenState.ERROR: (
        "Meta returned an unexpected error, so the connection could not be confirmed.",
        "Run `meta-ads-connect doctor` for the full detail.",
    ),
}


@dataclass(frozen=True)
class ProbeResult:
    exit_code: Exit
    #: One line the owner can read.
    verdict: str
    #: What to do about it. Always populated, including on success.
    next_action: str
    cli: CliStatus
    mcp: McpStatus | None
    token: TokenCheck | None

    @property
    def connected(self) -> bool:
        return self.exit_code is Exit.OK

    def asDict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "exit_code": int(self.exit_code),
            "state": self.exit_code.name,
            "verdict": self.verdict,
            "next_action": self.next_action,
            "cli": {
                "installed": self.cli.installed,
                "version": self.cli.version,
                "pinned_version": CLI_VERSION,
                "at_pinned_version": self.cli.pinned,
            },
            "mcp": None if self.mcp is None else self.mcp.state.value,
            "ad_accounts": [
                {"id": account.id, "name": account.name}
                for account in (self.token.accounts if self.token else ())
            ],
        }


def probeConnection(ctx: Context) -> ProbeResult:
    """Work out the connection state without printing anything."""
    cli = detectCli(ctx)
    if not cli.installed:
        return ProbeResult(
            exit_code=Exit.NOT_INSTALLED,
            verdict="Meta Ads is not set up on this machine yet.",
            next_action=(
                "Run the full setup: `meta-ads-connect install`, then `meta-ads-connect mint-token`."
            ),
            cli=cli,
            mcp=None,
            token=None,
        )

    token = readToken(ctx.paths)
    if token is None:
        return ProbeResult(
            exit_code=Exit.NO_TOKEN,
            verdict="The Meta Ads CLI is installed, but there is no saved access token.",
            next_action=(
                "Run `meta-ads-connect mint-token`. "
                "The install step is already done — do not repeat it."
            ),
            cli=cli,
            mcp=None,
            token=None,
        )

    # From here on, anything this command writes is scrubbed of the token.
    ctx.secret = token
    check = checkToken(ctx, token)

    if check.state is not TokenState.LIVE:
        verdict, next_action = _TOKEN_PROSE[check.state]
        return ProbeResult(
            exit_code=TOKEN_VERDICTS[check.state].exit_code,
            verdict=verdict,
            next_action=next_action,
            cli=cli,
            mcp=None,
            token=check,
        )

    if not check.accounts:
        return ProbeResult(
            exit_code=Exit.NO_AD_ACCOUNTS,
            verdict="Your token works, but no ad accounts are assigned to it.",
            next_action="Run `meta-ads-connect repair-assets` to assign your ad accounts.",
            cli=cli,
            mcp=None,
            token=check,
        )

    mcp = detectMcp(ctx)
    if mcp.state is McpState.MISSING:
        return ProbeResult(
            exit_code=Exit.MCP_MISSING,
            verdict=(
                f"Connected to {describeAccounts(check.accounts)}, but Meta's Ads MCP server is not registered."
            ),
            next_action=(
                "Run `meta-ads-connect register-mcp` to finish. "
                "Everything else is already set up — do not start over."
            ),
            cli=cli,
            mcp=mcp,
            token=check,
        )

    return ProbeResult(
        exit_code=Exit.OK,
        verdict=f"Already connected to Meta Ads: {describeAccounts(check.accounts)}.",
        next_action="Nothing to do. Do not run setup again.",
        cli=cli,
        mcp=mcp,
        token=check,
    )


def runProbe(ctx: Context, *, as_json: bool = False) -> int:
    result = probeConnection(ctx)
    if as_json:
        ctx.say(json.dumps(result.asDict(), indent=2))
    else:
        ctx.say(result.verdict)
        ctx.say(f"Next: {result.next_action}")
    return int(result.exit_code)

