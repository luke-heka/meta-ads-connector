"""The whole design rests on three sentences in SKILL.md: probe first, the MCP
server is the primary transport, and the MCP path stands alone — it never
requires the CLI, the package, a token, or a Python.

Those sentences are prose, so nothing else can protect them. A careless edit
that removes any one of them would not break a single other test — it would
just quietly reintroduce the reconnect bug or the CLI gating this kit exists
to end. Hence this cheap guard on the things that matter most.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from meta_ads_connect.config import CLI_VERSION, MCP_NAME, MCP_URL
from meta_ads_connect.exits import Exit

SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "meta-ads-connect" / "SKILL.md"


@pytest.fixture(scope="module")
def skill() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_the_skill_file_exists_where_the_kit_installs_it() -> None:
    assert SKILL_PATH.exists(), f"SKILL.md is missing from {SKILL_PATH.parent}"


def test_it_has_frontmatter_claude_can_route_on(skill: str) -> None:
    assert skill.startswith("---\n")
    header = skill.split("---")[1]
    assert "name: meta-ads-connect" in header
    assert "description:" in header


def test_the_description_covers_the_words_a_user_would_actually_say(skill: str) -> None:
    header = skill.split("---")[1].lower()
    for phrase in ("meta ads", "facebook ads", "instagram ads", "ad account"):
        assert phrase in header, f"the description does not mention {phrase!r}"


def test_it_instructs_that_the_probe_is_always_the_first_action(skill: str) -> None:
    lowered = skill.lower()
    assert "probe first" in lowered
    assert "first action" in lowered
    assert "meta-ads-connect probe" in skill


def test_it_forbids_reconnecting_something_already_connected(skill: str) -> None:
    lowered = skill.lower()
    assert "never reconnect what is already connected" in lowered
    assert "do not run setup" in lowered


def test_it_states_the_precedence_rule_between_the_two_transports(skill: str) -> None:
    lowered = skill.lower()
    assert "mcp server is primary" in lowered
    assert "primary transport" in lowered
    assert "optional enhancement" in lowered
    assert "audiences" in lowered
    assert "benchmark" in lowered


def test_it_no_longer_routes_ads_work_to_the_cli_by_default(skill: str) -> None:
    """The inversion is the whole point: the old rule said the CLI does
    everything, and any echo of it re-gates the working path behind the
    blocked one."""
    lowered = skill.lower()
    assert "cli is primary" not in lowered
    assert "cli does everything" not in lowered
    assert "the cli does everything" not in lowered


def test_it_states_the_independence_constraint(skill: str) -> None:
    lowered = skill.lower()
    assert "mcp path stands alone" in lowered
    assert "never requires the cli, the python package, a token, or a python" in lowered
    assert "do not offer" in lowered
    assert "mint-token" in lowered.split("do not offer", 1)[1][:200]


def test_it_documents_the_bare_registration_command_as_first_class(skill: str) -> None:
    """The MCP path must be reachable with nothing installed but the skill —
    when `meta-ads-connect` is not on PATH, that is not a verdict."""
    assert f"claude mcp add --transport http {MCP_NAME} {MCP_URL}" in skill
    assert "not on your PATH, that is not a verdict" in skill
    assert "claude mcp list" in skill


def test_the_redirect_uri_fallback_lives_in_the_skill_itself(skill: str) -> None:
    """The user hitting that bug is precisely the user least likely to have a
    working package install, so the walkthrough must not depend on it."""
    assert "developers.facebook.com/apps" in skill
    assert "App Review" in skill
    assert "business verification" in skill
    assert "development mode" in skill
    assert "--client-id" in skill


def test_it_announces_consent_and_forbids_narrowing_the_grant(skill: str) -> None:
    lowered = skill.lower()
    assert "deselect" in lowered
    assert "browser" in lowered
    assert "re-consent" in lowered


def test_it_verifies_the_connection_with_a_live_read_after_consent(skill: str) -> None:
    lowered = skill.lower()
    assert "live read" in lowered


def test_it_names_where_to_revoke_mcp_access(skill: str) -> None:
    unwrapped = " ".join(skill.split())
    assert "Business integrations" in unwrapped


def test_it_puts_the_raw_graph_api_out_of_scope(skill: str) -> None:
    lowered = skill.lower()
    assert "raw graph api is out of scope" in lowered
    assert "third-party" in lowered


def test_it_requires_cli_invocations_to_be_built_from_help(skill: str) -> None:
    """Doc/binary drift is confirmed, so memory and docs are both wrong."""
    lowered = skill.lower()
    assert "--help" in skill
    assert "never from memory or docs" in lowered
    assert "instagram-user-id" in lowered


def test_it_treats_mcp_tool_names_as_unstable(skill: str) -> None:
    lowered = skill.lower()
    assert "unstable" in lowered
    assert "do not hardcode tool names" in lowered


def test_it_requires_confirmation_before_spend_and_before_going_live(skill: str) -> None:
    lowered = skill.lower()
    assert "create everything paused" in lowered
    assert "confirm before anything that changes spend or sets something live" in lowered
    assert "deletions need an unmistakable instruction" in lowered


def test_it_forbids_printing_the_token(skill: str) -> None:
    lowered = skill.lower()
    assert "never print the token" in lowered
    assert "~/.meta-ads/.env" in skill


def test_it_names_every_subcommand_the_package_provides(skill: str) -> None:
    for subcommand in (
        "probe",
        "doctor",
        "install",
        "mint-token",
        "register-mcp",
        "repair-assets",
        "exec",
    ):
        assert f"meta-ads-connect {subcommand}" in skill, f"SKILL.md never mentions {subcommand}"


def test_it_routes_cli_calls_through_exec_rather_than_a_bare_meta(skill: str) -> None:
    """`meta` is deliberately not on PATH — the isolated environment is what
    stops it colliding with the user's other Python work. Telling Claude to run
    it bare would fail with "command not found" on every clean install."""
    assert "meta-ads-connect exec --" in skill
    assert "Do not run bare `meta`" in skill

    for line in skill.splitlines():
        stripped = line.strip()
        if stripped.startswith(("meta ", "$ meta ")):
            raise AssertionError(f"SKILL.md tells Claude to run a bare meta: {stripped!r}")


@pytest.mark.parametrize(
    "state",
    [
        "OK",
        "TOKEN_REJECTED",
        "NO_TOKEN",
        "NOT_INSTALLED",
        "RATE_LIMITED",
        "NETWORK_ERROR",
        "MCP_MISSING",
        "NO_AD_ACCOUNTS",
        "META_ERROR",
        "MCP_NEEDS_LOGIN",
        "MCP_INCOMPLETE",
    ],
)
def test_every_probe_state_tells_claude_what_to_do(skill: str, state: str) -> None:
    """A state the routing table does not cover is a state Claude improvises on."""
    assert state in skill


def test_the_probe_states_in_the_table_match_the_exit_codes_in_the_code(skill: str) -> None:
    for state in (
        "OK",
        "TOKEN_REJECTED",
        "NO_TOKEN",
        "NOT_INSTALLED",
        "MCP_MISSING",
        "MCP_NEEDS_LOGIN",
        "MCP_INCOMPLETE",
    ):
        exit_code = int(Exit[state])
        row = [line for line in skill.splitlines() if line.startswith(f"| `{state}`")]
        assert row, f"no routing table row for {state}"
        assert f"| {exit_code} |" in row[0], f"{state} is documented with the wrong exit code"


def test_it_routes_the_missing_browser_extra_rather_than_leaving_claude_to_guess(
    skill: str,
) -> None:
    """`mint-token` exits 64 when Playwright is not installed, which is the
    default install. An exit code the routing does not cover is a user story
    that dead-ends."""
    assert f"exits {int(Exit.USAGE)}" in skill
    assert "meta-ads-connect[mint]" in skill
    assert "playwright install chromium" in skill


def test_it_never_asks_the_user_to_paste_their_token(skill: str) -> None:
    """A credential with spend authority must not pass through the transcript,
    including on the manual path."""
    assert "Never ask them to paste" in skill


def test_it_says_a_probe_of_ok_does_not_prove_every_account_is_reachable(
    skill: str,
) -> None:
    """`OK` means at least one account is reachable. An owner whose second
    account is invisible is told nothing is wrong unless Claude knows this."""
    assert "even if `probe` returned `OK`" in skill


def test_it_does_not_hardcode_a_stale_cli_version(skill: str) -> None:
    """If a version is quoted at all it has to be the pinned one."""
    for line in skill.splitlines():
        if "meta-ads==" in line:
            assert f"meta-ads=={CLI_VERSION}" in line


def test_it_names_the_official_mcp_endpoint_and_no_other(skill: str) -> None:
    assert "mcp.facebook.com" not in skill or MCP_URL in skill
    for rejected in ("pipeboard", "gomarble"):
        assert rejected not in skill.lower()
