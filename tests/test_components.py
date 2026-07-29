"""Detection has to be conservative in one specific direction.

Reporting an installed CLI as absent is far more damaging than reporting an
unknown version: it triggers a reinstall of something already present, which is
the exact failure this kit exists to prevent. These tests pin that asymmetry.
"""

from __future__ import annotations

from meta_ads_connect.commands.doctor import _TOKEN_NEXT_ACTIONS
from meta_ads_connect.commands.probe import _TOKEN_PROSE
from meta_ads_connect.components import (
    TOKEN_VERDICTS,
    McpScope,
    McpState,
    TokenState,
    detectCli,
    detectMcp,
)
from meta_ads_connect.config import CLI_VERSION, MCP_NAME, MCP_URL, Paths
from meta_ads_connect.context import Context

from .conftest import (
    LOCAL_SCOPE_LINE,
    FakeCommandRunner,
    incompleteMcp,
    installedCli,
    needsLoginMcp,
    registeredMcp,
)


def test_every_way_a_token_can_fail_is_classified_and_worded_in_both_commands() -> None:
    """``probe`` and ``doctor`` answer about the same token, so a state one of
    them has words for and the other does not is a crash waiting for whoever
    adds the next one."""
    failures = {state for state in TokenState if state is not TokenState.LIVE}

    assert set(TOKEN_VERDICTS) == failures
    assert set(_TOKEN_PROSE) == failures
    assert set(_TOKEN_NEXT_ACTIONS) == failures


def test_a_rate_limit_and_a_dropped_connection_are_never_fatal() -> None:
    """Neither says anything about the setup. Treating them as a broken one is
    how an owner gets told to re-mint a token that works."""
    assert not TOKEN_VERDICTS[TokenState.RATE_LIMITED].blocking
    assert not TOKEN_VERDICTS[TokenState.UNREACHABLE].blocking
    assert TOKEN_VERDICTS[TokenState.REJECTED].blocking


def _binaryOnDisk(paths: Paths) -> None:
    paths.venv_bin.mkdir(parents=True, exist_ok=True)
    paths.cli_binary.write_text("#!/bin/sh\n")
    paths.cli_binary.chmod(0o755)


def test_detects_the_managed_cli_and_its_version(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    installedCli(runner, paths)

    status = detectCli(ctx)

    assert status.installed
    assert status.version == CLI_VERSION
    assert status.pinned
    assert not status.external


def test_a_binary_that_rejects_version_is_still_installed(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    """The shipped binary's flags and its documentation are known to disagree.
    An unrecognised flag must not read as an absent CLI."""
    _binaryOnDisk(paths)
    runner.fails(["meta", "--version"], stderr="Error: No such option: --version")
    runner.respond(["meta", "--help"], stdout="Usage: meta [OPTIONS] COMMAND")

    status = detectCli(ctx)

    assert status.installed
    assert status.version is None
    assert not status.pinned


def test_a_binary_that_runs_nothing_at_all_is_reported_as_absent(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    """A broken install should route to a reinstall, not be papered over."""
    _binaryOnDisk(paths)
    runner.fails(["meta", "--version"], stderr="Segmentation fault")
    runner.fails(["meta", "--help"], stderr="Segmentation fault")

    assert not detectCli(ctx).installed


def test_a_version_string_in_an_unexpected_shape_still_counts_as_installed(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    _binaryOnDisk(paths)
    runner.respond(["meta", "--version"], stdout="meta ads cli (build 2026-06-17)")

    status = detectCli(ctx)

    assert status.installed
    assert status.version == ""


def test_finds_a_cli_the_owner_installed_themselves(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """So a partially-complete setup is finished rather than duplicated."""
    runner.onPath("meta", "/opt/homebrew/bin/meta")
    runner.respond(["meta", "--version"], stdout=f"meta-ads {CLI_VERSION}")

    status = detectCli(ctx)

    assert status.installed
    assert status.external
    assert status.path == "/opt/homebrew/bin/meta"


def test_reports_no_cli_when_there_is_none(ctx: Context) -> None:
    assert not detectCli(ctx).installed


def test_recognises_the_mcp_server_by_the_name_it_is_registered_under(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    registeredMcp(runner)

    assert detectMcp(ctx).state is McpState.CONNECTED


def test_reads_registration_and_scope_from_one_get_call(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """One call answers both questions, so probe and doctor can never
    disagree about what is wrong."""
    registeredMcp(runner)

    status = detectMcp(ctx)

    assert status.state is McpState.CONNECTED
    assert status.scope is McpScope.USER
    assert ("claude", "mcp", "get", MCP_NAME) in runner.calls


def test_reads_a_local_scope_registration_as_local(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """LOCAL is the stranding bug: registered only inside the folder setup
    happened to run in. It must be representable without a new state."""
    registeredMcp(runner, scope=LOCAL_SCOPE_LINE)

    status = detectMcp(ctx)

    assert status.state is McpState.CONNECTED
    assert status.scope is McpScope.LOCAL


def test_recognises_the_mcp_server_by_its_url_under_a_different_name(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """The owner may have registered it under a name of their own; that must
    not read as absent."""
    runner.onPath("claude")
    runner.fails(["claude", "mcp", "get"], stderr='No MCP server named "meta-ads" found.')
    runner.respond(["claude", "mcp", "list"], stdout=f"my-ads: {MCP_URL} - ✔ Connected")

    assert detectMcp(ctx).state is McpState.CONNECTED


def test_reads_the_waiting_for_login_state(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    needsLoginMcp(runner)

    status = detectMcp(ctx)

    assert status.state is McpState.NEEDS_LOGIN
    assert status.registered
    assert not status.usable


def test_reads_a_failing_connection_as_incomplete_not_missing(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """Registered-but-broken must never read as absent — that is the
    reconnect bug all over again."""
    incompleteMcp(runner)

    status = detectMcp(ctx)

    assert status.state is McpState.INCOMPLETE
    assert status.registered


def test_a_registered_server_with_no_health_marker_counts_as_connected(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """Claude Code's wording is not ours to pin. An unrecognised health note
    on a registered server defaults to connected rather than to a repair."""
    runner.onPath("claude")
    runner.respond(
        ["claude", "mcp", "get", MCP_NAME],
        stdout=f"{MCP_NAME}:\n  Scope: User config\n  Type: http\n  URL: {MCP_URL}\n",
    )

    assert detectMcp(ctx).state is McpState.CONNECTED


def test_is_not_fooled_by_an_unrelated_server(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    runner.onPath("claude")
    runner.fails(["claude", "mcp", "get"], stderr='No MCP server named "meta-ads" found.')
    runner.respond(
        ["claude", "mcp", "list"],
        stdout="notion: https://mcp.notion.com/mcp - ✔ Connected",
    )

    assert detectMcp(ctx).state is McpState.MISSING


def test_reports_unknown_rather_than_missing_when_claude_is_absent(ctx: Context) -> None:
    """Missing would send the owner into a repair they cannot complete."""
    assert detectMcp(ctx).state is McpState.UNKNOWN


def test_reports_unknown_when_claude_fails_for_reasons_other_than_absence(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    """Only "No MCP server named" means absent. Any other failure of the
    `claude` CLI is never a verdict about the connection."""
    runner.onPath("claude")
    runner.fails(["claude", "mcp", "get"], stderr="config unreadable")

    assert detectMcp(ctx).state is McpState.UNKNOWN


def test_the_minted_scopes_include_what_repair_assets_actually_needs() -> None:
    """`GET /me/businesses` and `POST /<account>/assigned_users` both require
    business_management. Without it, repair-assets 400s against real Meta and
    only the fakes make it look like it works.
    See docs/adr/0001-business-manager-repair-scope.md."""
    from meta_ads_connect.config import REQUIRED_SCOPES

    assert "business_management" in REQUIRED_SCOPES
    for scope in ("ads_management", "ads_read", "pages_show_list", "leads_retrieval"):
        assert scope in REQUIRED_SCOPES
