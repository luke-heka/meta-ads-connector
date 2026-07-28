"""``doctor`` — a component-by-component diagnosis.

``probe`` answers one question: are we connected? ``doctor`` answers "what
exactly is wrong", one line per component, so a failure is localised rather
than reported as "it is broken". Every failing line names the next action.

Everything written here goes through :meth:`Context.say`, which redacts the
token — including error text relayed from Meta or from a subprocess, which is
the path a credential would realistically leak by.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..components import TOKEN_VERDICTS, McpState, TokenState, checkToken, detectCli, detectMcp
from ..config import CLI_VERSION, MCP_URL, RECHECK_DATE, SUPPORTED_PYTHONS
from ..context import Context
from ..exits import Exit
from ..interpreter import resolveInterpreter
from ..state import recordedInterpreter
from ..tokens import DIR_MODE, FILE_MODE, directoryMode, formatMode, readToken, tokenFileMode


class Health(Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"

    @property
    def symbol(self) -> str:
        return {"ok": "✓", "warn": "!", "fail": "✗"}[self.value]


@dataclass(frozen=True)
class Check:
    name: str
    health: Health
    detail: str
    next_action: str = ""
    #: What the whole command should exit with if this is the first failure.
    exit_code: Exit = Exit.OK


def runDoctor(ctx: Context) -> int:
    checks = collectChecks(ctx)

    ctx.say("Meta Ads setup check")
    ctx.say("")
    for check in checks:
        ctx.say(f"{check.health.symbol} {check.name} — {check.detail}")
        for index, line in enumerate(check.next_action.splitlines()):
            ctx.say(f"    Next: {line}" if index == 0 else f"          {line}")

    failures = [check for check in checks if check.health is Health.FAIL]
    ctx.say("")
    if failures:
        ctx.say(f"{len(failures)} thing{'s' if len(failures) != 1 else ''} need attention, listed above.")
        return int(failures[0].exit_code)

    warnings = [check for check in checks if check.health is Health.WARN]
    if warnings:
        ctx.say("Everything essential is working. The lines marked ! are worth a look but are not blocking.")
    else:
        ctx.say("Everything is working. You can just talk to Claude about your ads.")
    ctx.say(f"(This kit's information about Meta's connectors is due a re-check in {RECHECK_DATE}.)")
    return int(Exit.OK)


def collectChecks(ctx: Context) -> list[Check]:
    checks = [_platformCheck(ctx)]
    if checks[0].health is Health.FAIL:
        # Nothing below can succeed on a platform with no build at all.
        return checks

    checks.append(_interpreterCheck(ctx))
    cli = _cliCheck(ctx)
    checks.append(cli)

    token = readToken(ctx.paths)
    ctx.secret = token
    checks.append(_tokenFileCheck(ctx, token))

    if token is not None:
        checks.extend(_tokenLiveChecks(ctx, token))

    checks.append(_mcpCheck(ctx))
    return checks


def _platformCheck(ctx: Context) -> Check:
    if ctx.is_windows:
        return Check(
            name="Operating system",
            health=Health.FAIL,
            detail="Windows, which Meta's Ads CLI has no build for.",
            next_action=(
                "Install WSL (Windows Subsystem for Linux), open an Ubuntu terminal, "
                "and run this setup again from there."
            ),
            exit_code=Exit.UNSUPPORTED_PLATFORM,
        )
    return Check(name="Operating system", health=Health.OK, detail=f"{ctx.platform}, supported.")


def _interpreterCheck(ctx: Context) -> Check:
    resolution = resolveInterpreter(ctx.runner, recorded=recordedInterpreter(ctx.paths))
    if resolution.chosen is None:
        wanted = " or ".join(f"{major}.{minor}" for major, minor in SUPPORTED_PYTHONS)
        return Check(
            name="Python",
            health=Health.FAIL,
            detail=resolution.explain(),
            next_action=f"Install Python {wanted}, then run `meta-ads-connect install`.",
            exit_code=Exit.UNUSABLE_PYTHON,
        )
    chosen = resolution.chosen
    unusable = sorted(
        {found.label for found in resolution.considered if not found.supported}
    )
    if unusable:
        # Say why a different interpreter was picked. Otherwise an owner on
        # 3.14 who also happens to have 3.13 sees a bare "Python 3.13" and has
        # no idea the kit made a choice on their behalf.
        return Check(
            name="Python",
            health=Health.OK,
            detail=(
                f"{chosen.label} at {chosen.path}. You also have "
                f"{', '.join(unusable)}, which Meta's Ads CLI has no build for — "
                f"this kit uses {chosen.label} instead and leaves the rest alone."
            ),
        )
    return Check(
        name="Python",
        health=Health.OK,
        detail=f"{chosen.label} at {chosen.path}.",
    )


def _cliCheck(ctx: Context) -> Check:
    cli = detectCli(ctx)
    if not cli.installed:
        return Check(
            name="Meta Ads CLI",
            health=Health.FAIL,
            detail="Not installed.",
            next_action="Run `meta-ads-connect install`.",
            exit_code=Exit.NOT_INSTALLED,
        )
    if cli.pinned:
        location = " (installed outside this kit)" if cli.external else ""
        return Check(name="Meta Ads CLI", health=Health.OK, detail=f"Version {CLI_VERSION}{location}.")
    return Check(
        name="Meta Ads CLI",
        health=Health.WARN,
        detail=f"Version {cli.version or 'unknown'}; this kit is tested against {CLI_VERSION}.",
        next_action="Run `meta-ads-connect install --force` to move to the tested version.",
    )


def _tokenFileCheck(ctx: Context, token: str | None) -> Check:
    if token is None:
        return Check(
            name="Access token",
            health=Health.FAIL,
            detail=f"No token saved at {ctx.paths.env_file}.",
            next_action="Run `meta-ads-connect mint-token`.",
            exit_code=Exit.NO_TOKEN,
        )

    file_mode = tokenFileMode(ctx.paths)
    dir_mode = directoryMode(ctx.paths)
    if file_mode != FILE_MODE or dir_mode != DIR_MODE:
        return Check(
            name="Access token",
            health=Health.WARN,
            detail=(
                f"Saved at {ctx.paths.env_file}, but its permissions are "
                f"{formatMode(file_mode)} in a {formatMode(dir_mode)} folder rather than "
                f"{formatMode(FILE_MODE)} in a {formatMode(DIR_MODE)} folder."
            ),
            next_action="Re-save it with `meta-ads-connect store-token` to fix the permissions.",
        )
    return Check(
        name="Access token",
        health=Health.OK,
        detail=f"Saved at {ctx.paths.env_file}, readable only by you.",
    )


#: The next action for each way a token can fail to answer. Whether each one is
#: fatal, and what it exits with, comes from ``TOKEN_VERDICTS`` — shared with
#: ``probe`` so the two commands cannot disagree about the same token.
_TOKEN_NEXT_ACTIONS: dict[TokenState, str] = {
    TokenState.REJECTED: "Run `meta-ads-connect mint-token` to mint and save a fresh one.",
    TokenState.RATE_LIMITED: "Wait a few minutes and run `meta-ads-connect doctor` again.",
    TokenState.UNREACHABLE: "Check your internet connection and run `meta-ads-connect doctor` again.",
    TokenState.ERROR: "Run `meta-ads-connect probe` again; if it persists, re-mint the token.",
}


def _tokenLiveChecks(ctx: Context, token: str) -> list[Check]:
    check = checkToken(ctx, token)

    if check.state is not TokenState.LIVE:
        verdict = TOKEN_VERDICTS[check.state]
        return [
            Check(
                name="Token accepted by Meta",
                health=Health.FAIL if verdict.blocking else Health.WARN,
                detail=check.detail,
                next_action=_TOKEN_NEXT_ACTIONS[check.state],
                exit_code=verdict.exit_code if verdict.blocking else Exit.OK,
            )
        ]

    accepted = Check(name="Token accepted by Meta", health=Health.OK, detail="Yes, checked just now.")
    if not check.accounts:
        return [
            accepted,
            Check(
                name="Ad accounts",
                health=Health.FAIL,
                detail="The token works, but no ad accounts are assigned to it.",
                next_action="Run `meta-ads-connect repair-assets`.",
                exit_code=Exit.NO_AD_ACCOUNTS,
            ),
        ]
    listed = ", ".join(account.describe() for account in check.accounts)
    return [accepted, Check(name="Ad accounts", health=Health.OK, detail=listed)]


def _mcpCheck(ctx: Context) -> Check:
    mcp = detectMcp(ctx)
    if mcp.state is McpState.REGISTERED:
        return Check(name="Meta Ads MCP server", health=Health.OK, detail=mcp.detail)
    if mcp.state is McpState.MISSING:
        return Check(
            name="Meta Ads MCP server",
            health=Health.FAIL,
            detail=mcp.detail + " Audiences and Meta's benchmark data need it; everything else does not.",
            next_action="Run `meta-ads-connect register-mcp`.",
            exit_code=Exit.MCP_MISSING,
        )
    return Check(
        name="Meta Ads MCP server",
        health=Health.WARN,
        detail=mcp.detail,
        next_action=(
            "If you use Claude in the desktop app, add it there instead: "
            f"Settings → Connectors → Add custom connector → {MCP_URL}"
        ),
    )
