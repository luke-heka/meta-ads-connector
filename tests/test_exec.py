"""``exec`` is how the Ads CLI is reachable at all.

It is installed into an environment the kit owns, so `meta` is deliberately not
on anyone's PATH — no shell profile is edited and nothing is symlinked into a
system directory. That makes `exec` the single supported way in, and the only
place the token is ever put into an environment.
"""

from __future__ import annotations

from meta_ads_connect.commands.exec_cli import runExec
from meta_ads_connect.config import TOKEN_ENV_VAR, Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.tokens import writeToken

from .conftest import VALID_TOKEN, FakeCommandRunner, Recorder, installedCli


def test_runs_the_managed_binary_rather_than_a_bare_meta(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    runner.respond(["meta", "ads", "account", "list"], stdout="act_111")

    assert runExec(ctx, ["ads", "account", "list"]) == Exit.OK

    invocation = [call for call in runner.calls if "list" in call][0]
    assert invocation[0] == str(paths.cli_binary)


def test_puts_the_token_in_the_environment_for_that_one_invocation(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    """Per invocation and in memory — never a shell profile, never a keychain.

    The variable name is written out literally rather than imported from config.
    Asserting `environment[TOKEN_ENV_VAR]` would pass for any value of that
    constant, including a wrong one — which is exactly how the `META_ACCESS_TOKEN`
    slip survived a green suite.
    """
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    runner.respond(["meta", "ads"], stdout="ok")

    runExec(ctx, ["ads", "account", "list"])

    environment = runner.environments[-1]
    assert environment["ACCESS_TOKEN"] == VALID_TOKEN
    assert "META_ACCESS_TOKEN" not in environment


def test_relays_what_the_cli_printed(
    ctx: Context, runner: FakeCommandRunner, paths: Paths, out: Recorder
) -> None:
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    runner.respond(["meta", "ads"], stdout="act_111  Selr AI")

    runExec(ctx, ["ads", "account", "list"])

    assert "act_111  Selr AI" in out.text


def test_passes_the_cli_exit_code_straight_through(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    """Claude has to be able to tell a failed campaign create from a successful one."""
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    runner.fails(["meta", "ads"], stderr="Error: Invalid budget", returncode=2)

    assert runExec(ctx, ["ads", "campaign", "create"]) == 2


def test_redacts_the_token_from_whatever_the_cli_prints(
    ctx: Context, runner: FakeCommandRunner, paths: Paths, out: Recorder, err: Recorder
) -> None:
    """A CLI run in debug mode echoing the credential must not reach the transcript."""
    installedCli(runner, paths)
    writeToken(paths, VALID_TOKEN)
    runner.respond(
        ["meta", "--debug"],
        stdout=f"GET /me/adaccounts?access_token={VALID_TOKEN}",
        stderr=f"auth header: Bearer {VALID_TOKEN}",
    )

    runExec(ctx, ["--debug", "ads", "account", "list"])

    assert VALID_TOKEN not in out.text
    assert VALID_TOKEN not in err.text
    assert "[redacted]" in out.text


def test_refuses_when_the_cli_is_not_installed(ctx: Context, err: Recorder) -> None:
    assert runExec(ctx, ["ads", "account", "list"]) == Exit.NOT_INSTALLED
    assert "meta-ads-connect install" in err.text


def test_refuses_when_there_is_no_token_rather_than_letting_meta_reject_it(
    ctx: Context, runner: FakeCommandRunner, paths: Paths, err: Recorder
) -> None:
    installedCli(runner, paths)

    assert runExec(ctx, ["ads", "account", "list"]) == Exit.NO_TOKEN
    assert "mint-token" in err.text


def test_an_empty_command_explains_the_syntax(ctx: Context, err: Recorder) -> None:
    assert runExec(ctx, []) == Exit.USAGE
    assert "exec -- ads account list" in err.text


def test_uses_a_cli_the_owner_installed_themselves_when_there_is_no_managed_one(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    runner.onPath("meta", "/opt/homebrew/bin/meta")
    runner.respond(["meta", "--version"], stdout="meta-ads 1.1.0")
    writeToken(paths, VALID_TOKEN)
    runner.respond(["meta", "ads"], stdout="ok")

    assert runExec(ctx, ["ads", "account", "list"]) == Exit.OK
