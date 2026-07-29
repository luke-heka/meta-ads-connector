"""``probe`` — the live connection check. Always the first action.

This is the actual fix for the most-reported symptom: Claude restarting a setup
the owner already finished. The verdict is a live authenticated call to Meta,
never a marker file, so a token revoked at Meta's end presents as disconnected
rather than being assumed good.

Two transports, evaluated independently and collapsed to one verdict only at
the end. The MCP server is the primary transport: a machine with nothing but a
consented MCP connection is fully connected, and no state of the optional CLI
path — absent, tokenless, rejected — may ever veto that or send its owner down
the CLI setup. Nothing-set-up requires *both* transports absent.

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
from ..config import CLI_VERSION, MCP_NAME, MCP_URL
from ..context import Context
from ..exits import Exit
from ..messages import CLAUDE_UNREACHABLE_ACTION, MCP_LOGIN_ACTION, MCP_RECONSENT_ACTION
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
    mcp: McpStatus
    #: The token's live verdict. None when there is no token to check — which,
    #: with the CLI installed, is the ``no_token`` state.
    token: TokenCheck | None

    @property
    def connected(self) -> bool:
        return self.exit_code is Exit.OK

    def cliTransportState(self) -> str:
        if not self.cli.installed:
            return "absent"
        if self.token is None:
            return "no_token"
        if self.token.state is TokenState.LIVE:
            return "live" if self.token.accounts else "no_ad_accounts"
        return {
            TokenState.REJECTED: "token_rejected",
            TokenState.RATE_LIMITED: "rate_limited",
            TokenState.UNREACHABLE: "unreachable",
            TokenState.ERROR: "error",
        }[self.token.state]

    def asDict(self) -> dict[str, Any]:
        cli_state = self.cliTransportState()
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
            "mcp": self.mcp.state.value,
            "ad_accounts": [
                {"id": account.id, "name": account.name}
                for account in (self.token.accounts if self.token else ())
            ],
            "transports": {
                "cli": {"state": cli_state, "usable": cli_state == "live"},
                "mcp": {
                    "state": self.mcp.state.value,
                    "registered": self.mcp.registered,
                    "usable": self.mcp.usable,
                },
            },
        }


def probeConnection(ctx: Context) -> ProbeResult:
    """Work out the connection state without printing anything."""
    mcp = detectMcp(ctx)
    cli = detectCli(ctx)

    # The token is a CLI-path credential. With the CLI absent it is never read,
    # so no CLI-side state — missing, rejected, accountless — can be reached on
    # an MCP-only machine.
    token = readToken(ctx.paths) if cli.installed else None
    check: TokenCheck | None = None
    if token is not None:
        # From here on, anything this command writes is scrubbed of the token.
        ctx.secret = token
        check = checkToken(ctx, token)

    if mcp.state is McpState.CONNECTED:
        return _connectedViaMcp(cli, mcp, check)
    if cli.installed:
        return _cliCascade(cli, mcp, check)
    return _mcpOnlyCascade(cli, mcp)


def _connectedViaMcp(cli: CliStatus, mcp: McpStatus, check: TokenCheck | None) -> ProbeResult:
    """The MCP transport is live, so the machine is connected — whatever state
    the optional CLI path is in. The broken half must not veto the working half."""
    if check is not None and check.state is TokenState.LIVE and check.accounts:
        verdict = (
            f"Already connected to Meta Ads: {describeAccounts(check.accounts)}. "
            "Both transports are live — Meta's MCP server and the Ads CLI."
        )
    else:
        verdict = "Already connected to Meta Ads through Meta's official MCP server."
    return ProbeResult(
        exit_code=Exit.OK,
        verdict=verdict,
        next_action="Nothing to do. Do not run setup again.",
        cli=cli,
        mcp=mcp,
        token=check,
    )


def _cliCascade(cli: CliStatus, mcp: McpStatus, check: TokenCheck | None) -> ProbeResult:
    """The CLI is installed, so its path is in use: today's cascade, unchanged
    for existing CLI users. Only once the CLI half is fully live does the MCP
    half decide the remaining verdict."""
    if check is None:
        return ProbeResult(
            exit_code=Exit.NO_TOKEN,
            verdict="The Meta Ads CLI is installed, but there is no saved access token.",
            next_action=(
                "Run `meta-ads-connect mint-token`. "
                "The install step is already done — do not repeat it."
            ),
            cli=cli,
            mcp=mcp,
            token=None,
        )

    if check.state is not TokenState.LIVE:
        verdict, next_action = _TOKEN_PROSE[check.state]
        return ProbeResult(
            exit_code=TOKEN_VERDICTS[check.state].exit_code,
            verdict=verdict,
            next_action=next_action,
            cli=cli,
            mcp=mcp,
            token=check,
        )

    if not check.accounts:
        return ProbeResult(
            exit_code=Exit.NO_AD_ACCOUNTS,
            verdict="Your token works, but no ad accounts are assigned to it.",
            next_action="Run `meta-ads-connect repair-assets` to assign your ad accounts.",
            cli=cli,
            mcp=mcp,
            token=check,
        )

    reached = f"Connected to {describeAccounts(check.accounts)}"
    if mcp.state is McpState.MISSING:
        return ProbeResult(
            exit_code=Exit.MCP_MISSING,
            verdict=f"{reached}, but Meta's Ads MCP server is not registered.",
            next_action=(
                "Run `meta-ads-connect register-mcp` to finish. "
                "Everything else is already set up — do not start over."
            ),
            cli=cli,
            mcp=mcp,
            token=check,
        )
    if mcp.state is McpState.NEEDS_LOGIN:
        return ProbeResult(
            exit_code=Exit.MCP_NEEDS_LOGIN,
            verdict=(
                f"{reached}. Meta's Ads MCP server is registered but waiting for you to "
                "log in to Meta."
            ),
            next_action=f"{MCP_LOGIN_ACTION} Everything else is already set up — do not start over.",
            cli=cli,
            mcp=mcp,
            token=check,
        )
    if mcp.state is McpState.INCOMPLETE:
        return ProbeResult(
            exit_code=Exit.MCP_INCOMPLETE,
            verdict=(
                f"{reached}. Meta's Ads MCP server is registered but its connection is not "
                "working — the approval may not cover everything the kit needs."
            ),
            next_action=f"{MCP_RECONSENT_ACTION} Everything else is already set up — do not start over.",
            cli=cli,
            mcp=mcp,
            token=check,
        )

    # McpState.UNKNOWN: registration cannot be read or written on this machine,
    # so it must not read as broken — the CLI half is fully live.
    return ProbeResult(
        exit_code=Exit.OK,
        verdict=f"Already connected to Meta Ads: {describeAccounts(check.accounts)}.",
        next_action="Nothing to do. Do not run setup again.",
        cli=cli,
        mcp=mcp,
        token=check,
    )


def _mcpOnlyCascade(cli: CliStatus, mcp: McpStatus) -> ProbeResult:
    """No CLI on this machine. The MCP path is the whole story, and its two
    intermediate states are one user action from working — never a failure."""
    if mcp.state is McpState.NEEDS_LOGIN:
        return ProbeResult(
            exit_code=Exit.MCP_NEEDS_LOGIN,
            verdict="Meta's Ads MCP server is registered — one step left: log in to Meta.",
            next_action=MCP_LOGIN_ACTION,
            cli=cli,
            mcp=mcp,
            token=None,
        )
    if mcp.state is McpState.INCOMPLETE:
        return ProbeResult(
            exit_code=Exit.MCP_INCOMPLETE,
            verdict=(
                "Meta's Ads MCP server is registered and a login happened, but the "
                "connection is not working — the approval may not cover everything the kit needs."
            ),
            next_action=MCP_RECONSENT_ACTION,
            cli=cli,
            mcp=mcp,
            token=None,
        )

    unreachable_hint = ""
    if mcp.state is McpState.UNKNOWN:
        unreachable_hint = f" {CLAUDE_UNREACHABLE_ACTION}"
    return ProbeResult(
        exit_code=Exit.NOT_INSTALLED,
        verdict="Meta Ads is not set up on this machine yet.",
        next_action=(
            "Register Meta's Ads MCP server: run `meta-ads-connect register-mcp`, or if "
            "that command is not available, run "
            f"`claude mcp add --transport http --scope user {MCP_NAME} {MCP_URL}`. "
            "No token and no Python are needed." + unreachable_hint
        ),
        cli=cli,
        mcp=mcp,
        token=None,
    )


def runProbe(ctx: Context, *, as_json: bool = False) -> int:
    result = probeConnection(ctx)
    if as_json:
        ctx.say(json.dumps(result.asDict(), indent=2))
    else:
        ctx.say(result.verdict)
        ctx.say(f"Next: {result.next_action}")
    return int(result.exit_code)
