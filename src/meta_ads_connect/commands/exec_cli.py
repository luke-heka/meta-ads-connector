"""``exec`` — run Meta's Ads CLI with the token in place.

The CLI is installed into an environment the kit owns, which is what keeps it
from colliding with the owner's other Python work — but it also means the
``meta`` binary is not on anyone's PATH. Rather than editing a shell profile
(residue an uninstall would miss) or symlinking into a system directory, the
kit offers one reliable way in:

    meta-ads-connect exec -- ads campaign list

This is also the only place the token is put into an environment, and it is put
there per invocation and in memory. Output is relayed through the same redacting
writer as everything else, so a CLI run in debug mode cannot echo the credential
into the transcript.
"""

from __future__ import annotations

from typing import Sequence

from ..components import detectCli
from ..context import Context
from ..exits import Exit
from ..processes import CommandNotFound
from ..tokens import cliEnvironment, readToken


def runExec(ctx: Context, argv: Sequence[str]) -> int:
    if not argv:
        ctx.warn(
            "Nothing to run.\n"
            "Next: pass the Meta CLI command after `--`, for example:\n"
            "      meta-ads-connect exec -- ads account list"
        )
        return int(Exit.USAGE)

    cli = detectCli(ctx)
    if not cli.installed or cli.path is None:
        ctx.warn("Meta's Ads CLI is not installed, so there is nothing to run.")
        ctx.warn("Next: run `meta-ads-connect install`.")
        return int(Exit.NOT_INSTALLED)

    token = readToken(ctx.paths)
    if token is None:
        ctx.warn("There is no saved Meta access token, so the CLI would be rejected.")
        ctx.warn("Next: run `meta-ads-connect mint-token`.")
        return int(Exit.NO_TOKEN)

    ctx.secret = token

    try:
        result = ctx.runner.run(
            [cli.path, *argv],
            env=cliEnvironment(token),
            timeout=900,
        )
    except CommandNotFound:
        ctx.warn(f"Meta's Ads CLI could not be run at {cli.path}.")
        ctx.warn("Next: run `meta-ads-connect doctor` for a component-by-component check.")
        return int(Exit.NOT_INSTALLED)

    if result.stdout:
        ctx.say(result.stdout.rstrip("\n"))
    if result.stderr:
        ctx.warn(result.stderr.rstrip("\n"))
    return result.returncode
