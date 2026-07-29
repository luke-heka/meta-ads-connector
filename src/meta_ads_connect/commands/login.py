"""``login`` — complete the Meta OAuth handshake for the MCP server.

``claude mcp login`` requires a controlling terminal: run from an ordinary
subprocess it prints the consent URL, says "Waiting for authorization", then
exits non-zero with "stdin isn't a terminal". Under a pseudo-terminal it
completes normally — the localhost callback does the work and nothing needs
typing. So this command allocates a pty around the child, which is what lets
Claude run the login for the member instead of handing them an instruction.

Success is never taken from the command's own message: the verdict is a fresh
`claude mcp get` read afterwards. Every failure ends in a named next action,
and after two attempts that did not authenticate the answer becomes "stop
retrying, run doctor" rather than a loop.
"""

from __future__ import annotations

import re

from ..components import McpState, detectMcp
from ..config import MCP_NAME
from ..context import Context
from ..exits import Exit
from ..messages import CLAUDE_UNREACHABLE_ACTION
from ..processes import CommandNotFound
from ..state import readState, writeState

#: How Claude Code words "this needs a real terminal", matched loosely because
#: the wording is theirs, not ours.
_NO_TERMINAL_MARKERS = ("isn't a terminal", "is not a terminal", "not a tty")

#: Give the member time to find the browser window and click approve.
_LOGIN_TIMEOUT = 300.0

_CONSENT_COACHING = (
    "Approve everything listed and do not deselect any ad accounts or pages — "
    "a narrowed approval comes back as a broken connection, not a safer one."
)

_MANUAL_COMMAND = f"claude mcp login {MCP_NAME}"

#: Attempts at this rung are bounded. After this many that did not
#: authenticate, the answer is doctor's diagnostic file, not another retry.
_MAX_ATTEMPTS = 2


def runLogin(ctx: Context) -> int:
    status = detectMcp(ctx)

    if status.state is McpState.UNKNOWN:
        ctx.warn(status.detail)
        ctx.warn(f"Next: {CLAUDE_UNREACHABLE_ACTION}")
        return int(Exit.CLAUDE_CLI_MISSING)
    if status.state is McpState.MISSING:
        ctx.warn("Meta's Ads MCP server is not registered yet, so there is nothing to log in to.")
        ctx.warn("Next: run `meta-ads-connect register-mcp`, then `meta-ads-connect login`.")
        return int(Exit.MCP_MISSING)
    if status.state is McpState.CONNECTED:
        _clearAttempts(ctx)
        ctx.say("Already logged in — Claude Code reports the connection as working. Nothing to do.")
        ctx.say("Next: ask Claude to read your ad accounts, which is the real proof it works.")
        return int(Exit.OK)

    # NEEDS_LOGIN or INCOMPLETE: the fix for both is the same approval.
    if ctx.is_windows:
        # The pty route is untested on Windows; a clean handover beats an
        # unhelpful failure.
        return _handOverToMember(ctx)

    ctx.say(
        "Opening Meta's approval screen in your browser — this is the one-time "
        f"login. {_CONSENT_COACHING}"
    )
    try:
        result = ctx.runner.runPty(["claude", "mcp", "login", MCP_NAME], timeout=_LOGIN_TIMEOUT)
    except CommandNotFound:
        ctx.warn("The `claude` command is not on your PATH, so the login cannot be run from here.")
        ctx.warn(f"Next: {CLAUDE_UNREACHABLE_ACTION}")
        return int(Exit.CLAUDE_CLI_MISSING)

    # The command's own success message is not the proof: verify by reading
    # the registration back.
    verified = detectMcp(ctx)
    if verified.state is McpState.CONNECTED:
        _clearAttempts(ctx)
        ctx.say("Logged in. Verified: Claude Code reports the connection as working.")
        ctx.say(
            "Next: ask Claude to read your ad accounts and name them back to you — "
            "the live read is what confirms the connection."
        )
        return int(Exit.OK)

    if _needsRealTerminal(result.output):
        # The raw "stdin isn't a terminal" error never reaches the member.
        return _handOverToMember(ctx)

    return _didNotAuthenticate(ctx, result.output)


def _needsRealTerminal(output: str) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in _NO_TERMINAL_MARKERS)


def _handOverToMember(ctx: Context) -> int:
    """The one-line fallback: the member runs the login in their own terminal,
    which always has the controlling terminal this command may lack."""
    ctx.say("The login needs to run in your own terminal. Paste this one line there:")
    ctx.say("")
    ctx.say(f"    {_MANUAL_COMMAND}")
    ctx.say("")
    ctx.say(f"Your browser will open for a one-time approval. {_CONSENT_COACHING}")
    return int(Exit.MCP_LOGIN_MANUAL)


def _didNotAuthenticate(ctx: Context, output: str) -> int:
    """The login ran and the connection still is not authenticated — the
    approval was abandoned, narrowed, or the browser never appeared."""
    attempts = _recordAttempt(ctx)

    ctx.warn("The login did not finish — the connection is still not authenticated.")
    url = _consentUrl(output)
    if url:
        ctx.warn(
            "If no browser window appeared, open this link yourself and approve there: "
            f"{url}"
        )
    if attempts >= _MAX_ATTEMPTS:
        ctx.warn(
            "That is two attempts that have not finished, so stop retrying this step. "
            "Next: run `meta-ads-connect doctor` — it writes a diagnostic file, safe to "
            "share, and tells you exactly what to paste when asking for help."
        )
        return int(Exit.MCP_LOGIN_FAILED)
    ctx.warn(
        "Next: run `meta-ads-connect login` once more and complete Meta's screen this "
        f"time. {_CONSENT_COACHING}"
    )
    return int(Exit.MCP_LOGIN_FAILED)


def _consentUrl(output: str) -> str | None:
    match = re.search(r"https://\S+", output)
    return match.group(0).rstrip(".,)") if match else None


def _recordAttempt(ctx: Context) -> int:
    attempts = _priorAttempts(ctx) + 1
    writeState(ctx.paths, {"login_attempts": attempts})
    return attempts


def _priorAttempts(ctx: Context) -> int:
    recorded = readState(ctx.paths).get("login_attempts")
    return recorded if isinstance(recorded, int) and recorded > 0 else 0


def _clearAttempts(ctx: Context) -> None:
    if _priorAttempts(ctx):
        writeState(ctx.paths, {"login_attempts": 0})
