"""``doctor`` localises a failure instead of reporting "it is broken".

Two things matter most here: every component reports separately, and the token
never reaches the output — including on the error paths, which is how a
credential would realistically leak.
"""

from __future__ import annotations

from meta_ads_connect.commands.doctor import runDoctor
from meta_ads_connect.config import CLI_VERSION, Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.graph import GraphAuthError, GraphNetworkError, GraphRateLimitError
from meta_ads_connect.tokens import writeToken

from .conftest import (
    AD_ACCOUNTS_PAYLOAD,
    VALID_TOKEN,
    FakeCommandRunner,
    FakeGraphClient,
    Recorder,
    incompleteMcp,
    installedCli,
    needsLoginMcp,
    registeredMcp,
    unregisteredMcp,
)


def _healthy(
    runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths
) -> None:
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)


def test_reports_every_component_as_healthy(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    _healthy(runner, graph, paths)

    assert runDoctor(ctx) == Exit.OK
    for component in (
        "Operating system",
        "Python",
        "Meta Ads CLI",
        "Access token",
        "Token accepted by Meta",
        "Ad accounts",
        "Meta Ads MCP server",
    ):
        assert component in out.text
    assert "✗" not in out.text
    assert "Everything is working" in out.text


def test_names_the_connected_ad_accounts(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    _healthy(runner, graph, paths)

    runDoctor(ctx)

    assert "Selr AI (act_111)" in out.text
    assert "Second Account (act_222)" in out.text


def test_a_missing_cli_is_optional_when_the_mcp_is_connected(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    """The CLI is an optional enhancement. With the MCP transport live, its
    absence must not read as a broken setup."""
    _healthy(runner, graph, paths)
    paths.cli_binary.unlink()

    assert runDoctor(ctx) == Exit.OK
    assert "optional" in out.text
    assert "✗" not in out.text


def test_a_missing_cli_fails_when_the_mcp_is_missing_too(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    unregisteredMcp(runner)

    assert runDoctor(ctx) == Exit.NOT_INSTALLED
    assert "✗ Meta Ads CLI — Not installed." in out.text
    assert "✓ Python" in out.text
    assert "meta-ads-connect install" in out.text


def test_a_missing_token_fails_only_that_component(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    _healthy(runner, graph, paths)
    paths.env_file.unlink()

    assert runDoctor(ctx) == Exit.NO_TOKEN
    assert "✗ Access token" in out.text
    assert "✓ Meta Ads CLI" in out.text
    assert "mint-token" in out.text


def test_a_rejected_token_is_distinguished_from_a_missing_one(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphAuthError("Session has been invalidated", code=190))

    assert runDoctor(ctx) == Exit.TOKEN_REJECTED
    assert "✓ Access token" in out.text
    assert "✗ Token accepted by Meta" in out.text


def test_an_unregistered_mcp_server_fails_only_that_component(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    _healthy(runner, graph, paths)
    unregisteredMcp(runner)

    assert runDoctor(ctx) == Exit.MCP_MISSING
    assert "✗ Meta Ads MCP server" in out.text
    assert "primary" in out.text


def test_a_wrong_cli_version_warns_without_blocking(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    _healthy(runner, graph, paths)
    runner.respond(["meta", "--version"], stdout="meta-ads 1.0.1")

    assert runDoctor(ctx) == Exit.OK
    assert "! Meta Ads CLI" in out.text
    assert CLI_VERSION in out.text
    assert "not blocking" in out.text


def test_loose_permissions_on_the_token_file_are_flagged(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    _healthy(runner, graph, paths)
    paths.env_file.chmod(0o644)

    assert runDoctor(ctx) == Exit.OK
    assert "! Access token" in out.text
    assert "644" in out.text
    assert "store-token" in out.text


def test_rate_limiting_warns_rather_than_condemning_the_token(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphRateLimitError("User request limit reached", code=17))

    assert runDoctor(ctx) == Exit.OK
    assert "! Token accepted by Meta" in out.text


def test_a_network_failure_warns_rather_than_condemning_the_token(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphNetworkError("could not reach graph.facebook.com"))

    assert runDoctor(ctx) == Exit.OK
    assert "! Token accepted by Meta" in out.text


def test_a_token_with_no_ad_accounts_points_at_repair(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})

    assert runDoctor(ctx) == Exit.NO_AD_ACCOUNTS
    assert "repair-assets" in out.text


def test_several_components_can_fail_at_once(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    """CLI and MCP server both missing. Each is listed; the exit code carries
    the first one, so a caller has somewhere to start. The token is a CLI-path
    credential, so with no CLI installed there is no token line to fail."""
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    unregisteredMcp(runner)

    assert runDoctor(ctx) == Exit.NOT_INSTALLED
    assert out.text.count("✗") == 2
    assert "Access token" not in out.text
    assert "need attention" in out.text


def test_an_mcp_only_machine_with_no_python_is_healthy(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    """MCP connected; no CLI, no token, no usable Python anywhere. That
    machine is fully working and must be told so — a language runtime is not
    a prerequisite for talking about your ads."""
    registeredMcp(runner)

    assert runDoctor(ctx) == Exit.OK
    assert "✗" not in out.text
    assert "Everything is working" in out.text
    assert "mint-token" not in out.text


def test_an_mcp_awaiting_login_names_the_login_as_the_next_action(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    needsLoginMcp(runner)

    result = runDoctor(ctx)

    assert "log in" in out.text.lower()
    assert result != Exit.OK


def test_an_incomplete_mcp_grant_asks_for_re_consent(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    """A completed login whose connection does not work is fixed by
    re-consenting, never by reinstalling anything."""
    _healthy(runner, graph, paths)
    incompleteMcp(runner)

    assert runDoctor(ctx) == Exit.MCP_INCOMPLETE
    assert "log in again" in out.text.lower()
    assert "meta-ads-connect install" not in out.text.split("Meta Ads MCP server")[-1]


def test_windows_stops_at_the_platform_rather_than_listing_everything_else(
    ctx: Context, out: Recorder
) -> None:
    ctx.platform = "win32"

    assert runDoctor(ctx) == Exit.UNSUPPORTED_PLATFORM
    assert "WSL" in out.text
    assert "Meta Ads CLI" not in out.text


def test_python_314_is_reported_with_what_to_install(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    runner.onPath("python3", "/opt/homebrew/bin/python3")
    runner.respond(["python3", "--version"], stdout="Python 3.14.5")
    unregisteredMcp(runner)

    assert runDoctor(ctx) == Exit.UNUSABLE_PYTHON
    assert "3.14" in out.text
    assert "3.13" in out.text


def test_the_token_never_appears_in_output_when_everything_is_healthy(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder, err: Recorder
) -> None:
    _healthy(runner, graph, paths)

    runDoctor(ctx)

    assert VALID_TOKEN not in out.text
    assert VALID_TOKEN not in err.text


def test_the_token_never_appears_in_output_when_meta_echoes_it_back(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder, err: Recorder
) -> None:
    """The realistic leak: an error we relay rather than one we wrote."""
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet(
        "/me/adaccounts",
        GraphAuthError(f"Invalid OAuth access token: {VALID_TOKEN}", code=190),
    )

    runDoctor(ctx)

    assert VALID_TOKEN not in out.text
    assert VALID_TOKEN not in err.text
    assert "[redacted]" in out.text


def test_records_when_the_kits_information_is_due_a_re_check(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    _healthy(runner, graph, paths)

    runDoctor(ctx)

    assert "September 2026" in out.text


def test_says_why_a_different_python_was_chosen(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    """On a machine with 3.14 as the default and 3.13 alongside, a bare
    "Python 3.13" leaves the owner unaware a choice was made for them."""
    _healthy(runner, graph, paths)
    runner.onPath("python3", "/opt/homebrew/bin/python3")
    runner.respond(["python3", "--version"], stdout="Python 3.14.5")

    assert runDoctor(ctx) == Exit.OK
    assert "✓ Python" in out.text
    assert "3.14" in out.text
    assert "no build for" in out.text
    assert "leaves the rest alone" in out.text
