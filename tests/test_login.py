"""``login`` completes the OAuth handshake itself, under a pseudo-terminal,
so the member's only job is the approval click. Its own success message is
never the proof — the verdict is a fresh `claude mcp get` read afterwards —
and every failure ends in a named next action, bounded so it can never loop.
"""

from __future__ import annotations

from typing import Sequence

from meta_ads_connect.commands.login import runLogin
from meta_ads_connect.config import MCP_NAME, Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.processes import CommandResult

from .conftest import (
    FakeCommandRunner,
    FakeGraphClient,
    Recorder,
    needsLoginMcp,
    registeredMcp,
    unregisteredMcp,
)

NO_TERMINAL_ERROR = (
    "Waiting for authorization...\n"
    "stdin isn't a terminal, so authentication can't be completed here."
)

CONSENT_URL = "https://www.facebook.com/v25.0/dialog/oauth?client_id=123"


def _loginSucceeds(runner: FakeCommandRunner) -> None:
    """A pty-backed login that authenticates: after it runs, `claude mcp get`
    reads Connected."""

    def authenticated(argv: Sequence[str]) -> CommandResult:
        registeredMcp(runner)
        return CommandResult(
            argv=tuple(argv),
            returncode=0,
            stdout=f"Authenticated with {MCP_NAME}.",
            stderr="",
        )

    runner.sideEffectPty(["claude", "mcp", "login"], authenticated)


def test_a_login_that_authenticates_ends_in_a_verified_connected_state(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    needsLoginMcp(runner)
    _loginSucceeds(runner)

    assert runLogin(ctx) == Exit.OK
    assert ("claude", "mcp", "login", MCP_NAME) in runner.pty_calls
    assert "Verified" in out.text
    assert "ad accounts" in out.text  # the live read is named as the real proof


def test_success_is_read_back_not_taken_from_the_commands_own_message(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """The command can print "Authenticated" and still leave an unauthenticated
    server behind. Only the read-back verdict counts."""
    needsLoginMcp(runner)
    runner.respondPty(
        ["claude", "mcp", "login"], stdout=f"Authenticated with {MCP_NAME}.", returncode=0
    )

    assert runLogin(ctx) == Exit.MCP_LOGIN_FAILED


def test_an_already_connected_server_is_left_alone(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    registeredMcp(runner)

    assert runLogin(ctx) == Exit.OK
    assert runner.pty_calls == []
    assert "Nothing to do" in out.text


def test_an_unregistered_server_routes_to_registration_not_a_login(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    unregisteredMcp(runner)

    assert runLogin(ctx) == Exit.MCP_MISSING
    assert "register-mcp" in err.text
    assert runner.pty_calls == []


def test_a_missing_claude_command_names_a_route_that_does_not_need_it(
    ctx: Context, err: Recorder
) -> None:
    assert runLogin(ctx) == Exit.CLAUDE_CLI_MISSING
    assert "Next:" in err.text


def test_a_login_that_needs_a_real_terminal_hands_over_one_pasteable_line(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    """The raw "stdin isn't a terminal" error never reaches a member; they
    get the single line to paste instead."""
    needsLoginMcp(runner)
    runner.respondPty(["claude", "mcp", "login"], stdout=NO_TERMINAL_ERROR, returncode=1)

    assert runLogin(ctx) == Exit.MCP_LOGIN_MANUAL
    assert f"claude mcp login {MCP_NAME}" in out.text
    assert "stdin isn't a terminal" not in out.text


def test_on_windows_the_pty_is_never_attempted(
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
    err: Recorder,
) -> None:
    ctx = Context(paths=paths, runner=runner, graph=graph, out=out, err=err, platform="win32")
    needsLoginMcp(runner)

    assert runLogin(ctx) == Exit.MCP_LOGIN_MANUAL
    assert runner.pty_calls == []
    assert f"claude mcp login {MCP_NAME}" in out.text


def test_an_abandoned_approval_offers_one_clean_retry_with_coaching(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    needsLoginMcp(runner)
    runner.respondPty(
        ["claude", "mcp", "login"],
        stdout=f"Opening browser: {CONSENT_URL}\nAuthentication timed out.",
        returncode=1,
    )

    assert runLogin(ctx) == Exit.MCP_LOGIN_FAILED
    assert "deselect" in err.text
    assert "meta-ads-connect login" in err.text


def test_a_browser_that_never_opened_gets_the_consent_url_to_open_by_hand(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    needsLoginMcp(runner)
    runner.respondPty(
        ["claude", "mcp", "login"],
        stdout=f"Opening browser: {CONSENT_URL}\nAuthentication timed out.",
        returncode=1,
    )

    runLogin(ctx)

    assert CONSENT_URL in err.text


def test_after_two_failed_attempts_it_stops_retrying_and_hands_over_to_doctor(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    """Bounded: the ladder never loops. The second failure routes to doctor's
    diagnostic file, not to a third attempt."""
    needsLoginMcp(runner)
    runner.respondPty(["claude", "mcp", "login"], stdout="Authentication timed out.", returncode=1)

    assert runLogin(ctx) == Exit.MCP_LOGIN_FAILED
    assert "doctor" not in err.text

    assert runLogin(ctx) == Exit.MCP_LOGIN_FAILED
    assert "stop retrying" in err.text
    assert "doctor" in err.text


def test_a_success_resets_the_attempt_counter(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    """A member who eventually got through starts fresh next time something
    goes wrong, rather than being sent straight to the help desk."""
    needsLoginMcp(runner)
    runner.respondPty(["claude", "mcp", "login"], stdout="Authentication timed out.", returncode=1)
    assert runLogin(ctx) == Exit.MCP_LOGIN_FAILED

    _loginSucceeds(runner)
    assert runLogin(ctx) == Exit.OK

    # Break it again: the count starts over at one, so no handover yet.
    needsLoginMcp(runner)
    runner.respondPty(["claude", "mcp", "login"], stdout="Authentication timed out.", returncode=1)
    assert runLogin(ctx) == Exit.MCP_LOGIN_FAILED
    assert "stop retrying" not in err.text.splitlines()[-1]


def test_no_message_promises_tools_are_available_in_this_session(
    ctx: Context, runner: FakeCommandRunner, out: Recorder, err: Recorder
) -> None:
    """The regression this issue exists to kill: a promise the current
    session cannot keep."""
    needsLoginMcp(runner)
    _loginSucceeds(runner)

    runLogin(ctx)

    combined = (out.text + err.text).lower()
    assert "tools are now available" not in combined
    assert "/mcp" not in combined
    assert "/reload-plugins" not in combined