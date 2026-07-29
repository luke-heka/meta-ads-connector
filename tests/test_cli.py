"""The command-line surface itself: every subcommand reachable, exit codes
passed through unchanged, and the token never accepted as an argument.
"""

from __future__ import annotations

import io

import pytest

from meta_ads_connect.cli import buildParser, run
from meta_ads_connect.config import CLI_VERSION, Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.tokens import readToken, writeToken

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

SUBCOMMANDS = [
    "probe",
    "doctor",
    "install",
    "store-token",
    "mint-token",
    "register-mcp",
    "login",
    "repair-assets",
    "exec",
]


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_every_documented_subcommand_parses(subcommand: str) -> None:
    args = buildParser().parse_args([subcommand])
    assert args.command == subcommand


def test_a_bare_invocation_is_rejected_rather_than_guessing() -> None:
    with pytest.raises(SystemExit):
        buildParser().parse_args([])


def test_probe_exit_code_reaches_the_caller(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths
) -> None:
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    assert run(["probe"], ctx=ctx) == Exit.OK


def test_probe_reports_an_unconfigured_machine_through_the_cli(ctx: Context) -> None:
    assert run(["probe"], ctx=ctx) == Exit.NOT_INSTALLED


def test_store_token_reads_the_token_from_standard_input(ctx: Context, paths: Paths) -> None:
    assert run(["store-token"], ctx=ctx, stdin=io.StringIO(VALID_TOKEN)) == Exit.OK
    assert readToken(paths) == VALID_TOKEN


def test_the_token_cannot_be_passed_as_an_argument() -> None:
    """argv is visible to every process on the machine and lands in shell
    history, so there must be no flag that accepts it."""
    with pytest.raises(SystemExit):
        buildParser().parse_args(["store-token", "--token", VALID_TOKEN])

    help_text = buildParser().format_help()
    assert "--token " not in help_text


def test_probe_json_flag_is_wired_through(
    ctx: Context, runner: FakeCommandRunner, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    installedCli(runner, paths)
    registeredMcp(runner)
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)

    run(["probe", "--json"], ctx=ctx)

    assert out.text.strip().startswith("{")


def test_install_force_flag_is_wired_through(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    installedCli(runner, paths)
    runner.onPath("python3.13", "/opt/homebrew/bin/python3.13")
    runner.respond(["python3.13", "--version"], stdout="Python 3.13.2")
    runner.respond(["-m", "venv"], stdout="")
    runner.respond(["-m", "pip", "install"], stdout="ok")

    run(["install", "--force"], ctx=ctx)

    assert runner.ranCommandContaining("-m", "pip", "install")


def test_register_mcp_app_id_flag_is_wired_through(
    ctx: Context, runner: FakeCommandRunner
) -> None:
    unregisteredMcp(runner)
    runner.respond(["claude", "mcp", "add"], stdout="added")

    run(["register-mcp", "--app-id", "1234567890"], ctx=ctx)

    assert runner.ranCommandContaining("--client-id", "1234567890")


def test_the_version_string_names_the_pinned_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        buildParser().parse_args(["--version"])

    assert CLI_VERSION in capsys.readouterr().out


def test_the_help_text_tells_the_reader_to_start_with_probe() -> None:
    assert "probe" in buildParser().format_help()


def test_the_default_context_writes_under_the_configured_home(isolated_home: object) -> None:
    """The kit writes nowhere but its own directory, so removing it is one
    delete rather than a hunt through shell profiles."""
    from meta_ads_connect.config import defaultPaths

    paths = defaultPaths()

    assert paths.root == isolated_home
    assert paths.env_file.parent == paths.root
    assert paths.venv.parent == paths.root
    assert paths.state_file.parent == paths.root


def test_exec_forwards_the_command_without_the_separator(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    runner.respond(["meta", "ads"], stdout="ok")

    run(["exec", "--", "ads", "account", "list"], ctx=ctx)

    invocation = [call for call in runner.calls if "account" in call][0]
    assert "--" not in invocation
    assert list(invocation[1:]) == ["ads", "account", "list"]
