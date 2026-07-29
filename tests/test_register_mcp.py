"""Registration is two-tier: no App ID first, then a hand-walked fallback when
Claude Code's redirect_uri regression bites. The fallback must produce
instructions, never a crash — a client-side bug is not the owner's problem to
debug.
"""

from __future__ import annotations

from typing import Sequence

from meta_ads_connect.commands.register_mcp import runRegisterMcp
from meta_ads_connect.config import MCP_NAME, MCP_URL
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.processes import CommandResult

from .conftest import (
    LOCAL_SCOPE_LINE,
    FakeCommandRunner,
    Recorder,
    incompleteMcp,
    needsLoginMcp,
    registeredMcp,
    unregisteredMcp,
)

REDIRECT_URI_ERROR = "Error: The provided redirect_uris are not registered for this client."


def test_registers_without_an_app_id_in_the_common_case(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    unregisteredMcp(runner)
    runner.respond(["claude", "mcp", "add"], stdout=f"Added HTTP MCP server {MCP_NAME}")

    assert runRegisterMcp(ctx) == Exit.OK
    assert runner.ranCommandContaining("claude", "mcp", "add", "--transport", "http", MCP_NAME, MCP_URL)
    assert not runner.ranCommandContaining("--client-id")
    assert "Registered" in out.text


def test_registers_at_user_scope_so_the_connection_exists_everywhere(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """The `claude mcp add` default is local scope, which strands the server
    in whichever folder setup happened to run in — the original bug."""
    unregisteredMcp(runner)
    runner.respond(["claude", "mcp", "add"], stdout="added")

    runRegisterMcp(ctx)

    assert runner.ranCommandContaining("claude", "mcp", "add", "--scope", "user")


def test_the_app_id_path_also_registers_at_user_scope(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    unregisteredMcp(runner)
    runner.respond(["claude", "mcp", "add"], stdout="added")

    runRegisterMcp(ctx, app_id="1234567890")

    assert runner.ranCommandContaining("claude", "mcp", "add", "--scope", "user")
    assert runner.ranCommandContaining("--client-id", "1234567890")


def test_success_names_the_login_as_the_next_step_and_promises_nothing_else(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    """The session that registered the server cannot load its tools, so the
    success text must name the login step and claim nothing about tools
    being available."""
    unregisteredMcp(runner)
    runner.respond(["claude", "mcp", "add"], stdout="added")

    runRegisterMcp(ctx)

    lowered = out.text.lower()
    assert "log in" in lowered
    assert "meta-ads-connect login" in out.text
    assert "available" not in lowered.replace("available in all your projects", "")
    assert "tools" not in lowered


def test_a_local_scope_registration_is_migrated_to_user_scope(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    """A member who ran an older version of the kit is silently upgraded
    rather than stranded by a bug they never knew about."""
    registeredMcp(runner, scope=LOCAL_SCOPE_LINE)
    runner.respond(["claude", "mcp", "remove"], stdout="removed")

    def nowUserScope(argv: Sequence[str]) -> CommandResult:
        registeredMcp(runner)  # subsequent `get` reads user scope
        return CommandResult(argv=tuple(argv), returncode=0, stdout="added", stderr="")

    runner.sideEffect(["claude", "mcp", "add"], nowUserScope)

    assert runRegisterMcp(ctx) == Exit.OK
    assert runner.ranCommandContaining("claude", "mcp", "remove", "--scope", "local", MCP_NAME)
    assert runner.ranCommandContaining("claude", "mcp", "add", "--scope", "user")
    assert "only for this folder" in out.text
    assert "Moved" in out.text


def test_a_user_scope_registration_is_not_migrated(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """Idempotence: re-running against a healthy user-scope registration
    touches nothing."""
    registeredMcp(runner)

    assert runRegisterMcp(ctx) == Exit.OK
    assert not runner.ranCommandContaining("claude", "mcp", "remove")
    assert not runner.ranCommandContaining("claude", "mcp", "add")


def test_skips_registration_when_it_is_already_registered(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    """Otherwise a re-run leaves the owner with duplicates."""
    registeredMcp(runner)

    assert runRegisterMcp(ctx) == Exit.OK
    assert "already registered" in out.text
    assert not runner.ranCommandContaining("claude", "mcp", "add")


def test_the_redirect_uri_bug_produces_instructions_rather_than_a_crash(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    unregisteredMcp(runner)
    runner.fails(["claude", "mcp", "add"], stderr=REDIRECT_URI_ERROR)

    assert runRegisterMcp(ctx) == Exit.MCP_NEEDS_APP_ID
    assert "developers.facebook.com/apps" in err.text
    assert "--app-id" in err.text


def test_the_fallback_says_the_bug_is_not_the_owners_fault(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    unregisteredMcp(runner)
    runner.fails(["claude", "mcp", "add"], stderr=REDIRECT_URI_ERROR)

    runRegisterMcp(ctx)

    assert "not something you did wrong" in err.text


def test_the_fallback_says_no_app_review_or_verification_is_needed(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    """Otherwise the owner abandons it expecting weeks of process."""
    unregisteredMcp(runner)
    runner.fails(["claude", "mcp", "add"], stderr=REDIRECT_URI_ERROR)

    runRegisterMcp(ctx)

    assert "App Review" in err.text
    assert "business verification" in err.text
    assert "development mode" in err.text


def test_passes_a_supplied_app_id_through(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    unregisteredMcp(runner)
    runner.respond(["claude", "mcp", "add"], stdout="added")

    assert runRegisterMcp(ctx, app_id="1234567890") == Exit.OK
    assert runner.ranCommandContaining("--client-id", "1234567890")


def test_does_not_loop_back_to_the_fallback_when_an_app_id_was_already_given(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    unregisteredMcp(runner)
    runner.fails(["claude", "mcp", "add"], stderr=REDIRECT_URI_ERROR)

    runRegisterMcp(ctx, app_id="1234567890")

    assert "developers.facebook.com/apps" not in err.text
    assert "doctor" in err.text


def test_reports_a_missing_claude_command_with_a_route_that_does_not_need_it(
    ctx: Context, err: Recorder
) -> None:
    """A PATH problem must not end the setup: the next action names a place
    where the command normally exists, not a dead end."""
    assert runRegisterMcp(ctx) == Exit.CLAUDE_CLI_MISSING
    assert "Next:" in err.text
    assert "Claude Code" in err.text
    assert "Add custom connector" not in err.text


def test_reports_an_unrelated_failure_without_pretending_it_is_the_known_bug(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    unregisteredMcp(runner)
    runner.fails(["claude", "mcp", "add"], stderr="Error: network unreachable")

    assert runRegisterMcp(ctx) == Exit.USAGE
    assert "developers.facebook.com/apps" not in err.text
    assert "network unreachable" in err.text


def test_registered_but_awaiting_login_points_at_the_login_not_a_re_add(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    """Registration is done; the remaining step is the user's login. Adding
    the server again would not move them forward."""
    needsLoginMcp(runner)

    assert runRegisterMcp(ctx) == Exit.OK
    assert "log in" in out.text.lower()
    assert not runner.ranCommandContaining("claude", "mcp", "add")


def test_registered_but_broken_asks_for_re_consent_not_re_registration(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    incompleteMcp(runner)

    assert runRegisterMcp(ctx) == Exit.MCP_INCOMPLETE
    assert "log in again" in err.text.lower()
    assert not runner.ranCommandContaining("claude", "mcp", "add")


def test_no_shared_message_speaks_terminal_only_vocabulary_or_over_claims() -> None:
    """The shared actions are shown to desktop-app members too, and to
    sessions whose tool list cannot include the server yet. `/mcp` and
    `/reload-plugins` are terminal vocabulary; availability claims are
    promises the current session cannot keep."""
    from meta_ads_connect import messages

    surfaces = (
        messages.MCP_LOGIN_ACTION,
        messages.MCP_RECONSENT_ACTION,
        messages.CLAUDE_UNREACHABLE_ACTION,
    )
    for text in surfaces:
        assert "/mcp" not in text
        assert "/reload-plugins" not in text
        assert "tools are now available" not in text.lower()
        assert "Cmd+Q" not in text
