"""``probe`` is the highest-value target in the kit: it is the fix for the
reconnect problem. Every state it can report is covered here, and every one
must produce a distinct exit code and a message naming the next action.
"""

from __future__ import annotations

import json

import pytest

from meta_ads_connect.commands.probe import runProbe
from meta_ads_connect.config import Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.graph import GraphAuthError, GraphError, GraphNetworkError, GraphRateLimitError
from meta_ads_connect.tokens import writeToken

from .conftest import (
    AD_ACCOUNTS_PAYLOAD,
    VALID_TOKEN,
    FakeCommandRunner,
    FakeGraphClient,
    Recorder,
    installedCli,
    registeredMcp,
    unregisteredMcp,
)


def test_reports_nothing_installed_when_the_cli_is_absent(ctx: Context, out: Recorder) -> None:
    assert runProbe(ctx) == Exit.NOT_INSTALLED
    assert "not set up" in out.text
    assert "install" in out.text


def test_reports_no_token_when_the_cli_is_installed_but_unconfigured(
    ctx: Context, runner: FakeCommandRunner, paths: Paths, out: Recorder
) -> None:
    installedCli(runner, paths)

    assert runProbe(ctx) == Exit.NO_TOKEN
    assert "no saved access token" in out.text
    assert "mint-token" in out.text


def test_no_token_says_not_to_repeat_the_install(
    ctx: Context, runner: FakeCommandRunner, paths: Paths, out: Recorder
) -> None:
    installedCli(runner, paths)

    runProbe(ctx)

    assert "do not repeat it" in out.text.lower()


def test_reports_a_revoked_token_as_rejected_rather_than_connected(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    graph.onGet(
        "/me/adaccounts",
        GraphAuthError("Error validating access token: the session has been invalidated.", code=190),
    )

    assert runProbe(ctx) == Exit.TOKEN_REJECTED
    assert "no longer valid" in out.text
    assert "mint-token" in out.text


def test_reports_rate_limiting_separately_from_a_bad_token(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphRateLimitError("User request limit reached", code=17))

    assert runProbe(ctx) == Exit.RATE_LIMITED
    assert "rate limiting" in out.text
    assert "Nothing needs reinstalling" in out.text


def test_reports_a_network_failure_without_blaming_the_token(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphNetworkError("could not reach graph.facebook.com"))

    assert runProbe(ctx) == Exit.NETWORK_ERROR
    assert "could not be confirmed" in out.text
    assert "token" not in out.text.split("Next:")[0].lower()


def test_reports_an_unrecognised_meta_error_as_its_own_state(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphError("Unknown edge", code=100))

    assert runProbe(ctx) == Exit.META_ERROR
    assert "doctor" in out.text


def test_reports_an_authenticated_token_with_no_assigned_accounts(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})

    assert runProbe(ctx) == Exit.NO_AD_ACCOUNTS
    assert "repair-assets" in out.text


def test_reports_a_missing_mcp_server_as_a_repair_not_a_restart(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    unregisteredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    assert runProbe(ctx) == Exit.MCP_MISSING
    assert "register-mcp" in out.text
    assert "do not start over" in out.text.lower()


def test_reports_a_healthy_setup_as_connected_and_names_the_accounts(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    assert runProbe(ctx) == Exit.OK
    assert "Already connected" in out.text
    assert "Selr AI (act_111)" in out.text
    assert "Nothing to do" in out.text


def test_treats_an_unreadable_mcp_registration_as_connected_rather_than_broken(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
) -> None:
    """No `claude` on PATH means registration cannot be read *or* written.

    Reporting that as a failure would send the owner into a repair they have no
    way to complete.
    """
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    assert runProbe(ctx) == Exit.OK


def test_every_probe_state_has_a_distinct_exit_code() -> None:
    states = [
        Exit.OK,
        Exit.TOKEN_REJECTED,
        Exit.NO_TOKEN,
        Exit.NOT_INSTALLED,
        Exit.RATE_LIMITED,
        Exit.NETWORK_ERROR,
        Exit.MCP_MISSING,
        Exit.NO_AD_ACCOUNTS,
        Exit.META_ERROR,
    ]
    assert len({int(state) for state in states}) == len(states)


@pytest.mark.parametrize(
    "scenario",
    ["not_installed", "no_token", "rejected", "connected"],
)
def test_every_outcome_names_a_next_action(
    scenario: str,
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    if scenario != "not_installed":
        installedCli(runner, paths)
    if scenario in {"rejected", "connected"}:
        writeToken(paths, VALID_TOKEN)
    if scenario == "rejected":
        graph.onGet("/me/adaccounts", GraphAuthError("invalid", code=190))
    if scenario == "connected":
        registeredMcp(runner)
        graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    runProbe(ctx)

    next_line = [line for line in out.text.splitlines() if line.startswith("Next:")]
    assert next_line, out.text
    assert len(next_line[0]) > len("Next: ")


def test_asks_meta_rather_than_trusting_the_file_on_disk(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
) -> None:
    """A marker file is not acceptable evidence of a connection."""
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    runProbe(ctx)

    assert graph.pathsRequested() == ["/me/adaccounts"]


def test_never_prints_the_token(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
    err: Recorder,
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphAuthError(f"Invalid token {VALID_TOKEN}", code=190))

    runProbe(ctx)

    assert VALID_TOKEN not in out.text
    assert VALID_TOKEN not in err.text


def test_json_output_carries_the_state_machine_readably(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    assert runProbe(ctx, as_json=True) == Exit.OK

    payload = json.loads(out.text)
    assert payload["connected"] is True
    assert payload["state"] == "OK"
    assert payload["mcp"] == "registered"
    assert payload["cli"]["at_pinned_version"] is True
    assert [account["id"] for account in payload["ad_accounts"]] == ["act_111", "act_222"]


def test_json_output_reports_a_partial_setup_without_claiming_connection(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths)
    unregisteredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    runProbe(ctx, as_json=True)

    payload = json.loads(out.text)
    assert payload["connected"] is False
    assert payload["state"] == "MCP_MISSING"
    assert payload["mcp"] == "missing"


def test_notices_a_cli_installed_at_the_wrong_version(
    ctx: Context,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    paths: Paths,
    out: Recorder,
) -> None:
    installedCli(runner, paths, version="1.0.0")
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    runProbe(ctx, as_json=True)

    payload = json.loads(out.text)
    assert payload["cli"]["version"] == "1.0.0"
    assert payload["cli"]["at_pinned_version"] is False
