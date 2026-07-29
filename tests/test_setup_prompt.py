"""The setup prompt is the most externally-visible prose in the product: it is
the first thing a Skool member sees and the only distribution mechanism the kit
has. It is prose, so nothing but these assertions protects it — and the README
reproduces it verbatim, so the two copies are held equal here too.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "setup-prompt.md"
README_PATH = ROOT / "README.md"
SKILL_PATH = ROOT / "skills" / "meta-ads-connect" / "SKILL.md"

REPO_URL = "https://github.com/luke-heka/meta-ads-connector"
SKILLS_DIR = "~/.claude/skills"
CLONE_LOCATION = "~/meta-ads-connector"


def extractPromptBlock(markdown: str) -> str:
    """The paste-in prompt is the ```text fenced block."""
    match = re.search(r"```text\n(.*?)\n```", markdown, re.DOTALL)
    assert match, "no ```text fenced prompt block found"
    return match.group(1)


@pytest.fixture(scope="module")
def prompt() -> str:
    return extractPromptBlock(PROMPT_PATH.read_text(encoding="utf-8"))


def test_the_prompt_file_exists_where_the_readme_points() -> None:
    assert PROMPT_PATH.exists(), f"setup-prompt.md is missing from {ROOT}"
    assert "setup-prompt.md" in README_PATH.read_text(encoding="utf-8")


def test_the_readme_reproduces_the_prompt_verbatim(prompt: str) -> None:
    """The Skool post copies from the repo; the README must not drift from the
    source file, or the published text and the shipped behaviour part ways."""
    readme_copy = extractPromptBlock(README_PATH.read_text(encoding="utf-8"))
    assert readme_copy == prompt


def test_it_names_the_correct_repo_and_no_other(prompt: str) -> None:
    """Claude must not be left room to improvise a package name that does not
    exist — the failure that broke every previous guide."""
    assert REPO_URL in prompt
    for url in re.findall(r"https?://github\.com/\S+", prompt):
        assert url.rstrip(".,") == REPO_URL, f"unexpected repo URL {url!r}"


def test_it_clones_to_a_fixed_location_and_updates_in_place(prompt: str) -> None:
    assert CLONE_LOCATION in prompt
    assert "git pull" in prompt


def test_it_handles_a_machine_with_no_git(prompt: str) -> None:
    lowered = prompt.lower()
    assert "git is available" in lowered or "git is installed" in lowered
    assert "install (git)" in lowered or "install git" in lowered


def test_it_installs_into_the_directory_the_harness_actually_reads(prompt: str) -> None:
    assert SKILLS_DIR in prompt


def test_it_names_the_exact_invocation_and_it_matches_the_skill(prompt: str) -> None:
    header = SKILL_PATH.read_text(encoding="utf-8").split("---")[1]
    name_line = [line for line in header.splitlines() if line.startswith("name:")]
    skill_name = name_line[0].split(":", 1)[1].strip()
    assert f"/{skill_name}" in prompt


def test_it_states_that_a_new_session_is_required(prompt: str) -> None:
    assert "new claude session" in prompt.lower()


def test_it_counts_the_desktop_app_as_a_full_install_surface(prompt: str) -> None:
    """Claude Code inside the desktop app has a shell and ~/.claude/skills;
    conflating "desktop" with "no terminal" turned working members away. Only
    genuine claude.ai web chat lacks a terminal."""
    lowered = prompt.lower()
    assert "desktop app both count" in lowered
    assert "web browser" in lowered


def test_it_never_routes_to_the_desktop_connector_settings(prompt: str) -> None:
    """"Settings → Connectors → Add custom connector" is unverified and
    probably wrong for locally-registered servers — removed on purpose."""
    assert "Add custom connector" not in prompt


def test_the_python_package_is_optional_and_failure_is_success(prompt: str) -> None:
    """The decision most likely to erode: a machine with no Python or an
    externally-managed pip must still complete the install."""
    pip_lines = [line for line in prompt.splitlines() if "pip install" in line]
    assert pip_lines, "the optional helper install is missing entirely"
    for line in pip_lines:
        assert "optional" in line.lower(), f"pip install is not marked optional: {line!r}"
    assert "works without it" in prompt


def test_it_never_touches_meta_and_mints_nothing(prompt: str) -> None:
    lowered = prompt.lower()
    assert "mint" not in lowered
    assert "business manager" not in lowered
    assert "system user" not in lowered
    assert "do not connect" in lowered
    assert "do not touch my meta account" in lowered


def test_it_makes_no_claim_of_having_connected_anything(prompt: str) -> None:
    """Installing and connecting are two separate moments; the prompt must say
    so rather than imply the ads are reachable when it finishes."""
    assert "Installing and connecting are separate" in prompt


def test_it_is_short_enough_to_read_before_pasting(prompt: str) -> None:
    """A cautious member should be able to satisfy themselves it is not doing
    anything alarming. A prompt that grows past a screen has failed that."""
    assert len(prompt.split()) < 450
