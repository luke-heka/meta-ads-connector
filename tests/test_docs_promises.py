"""The README is what a member reads before installing anything, and the spec
and ADRs are what the next session reads before changing anything. Both kinds of
document make promises about behaviour that lives in prose elsewhere, so drift
between them is invisible until someone is disappointed by it.

These are cheap guards on that drift: the README must describe what the connect
flow actually ends with, and a cross-document reference must point at a file
that exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
TOUR_ADR = ROOT / "docs" / "adr" / "0002-post-connect-capability-tour.md"

DOCUMENTS = [
    ROOT / "README.md",
    ROOT / "CLAUDE.md",
    ROOT / "AGENTS.md",
    ROOT / "setup-prompt.md",
    *sorted((ROOT / "docs").rglob("*.md")),
]


def unwrapProse(text: str) -> str:
    """Markdown here wraps at ~80 columns, so a phrase these documents state
    plainly can still straddle a line break."""
    return " ".join(text.replace("**", "").split())


@pytest.fixture(scope="module")
def readme() -> str:
    return unwrapProse(README_PATH.read_text(encoding="utf-8")).lower()


def test_the_readme_describes_the_capability_tour(readme: str) -> None:
    """A member arrives expecting whatever the README told them. The connect
    flow no longer ends at a green tick, and the README says so."""
    assert "plain english" in readme
    assert "offer" in readme


def test_the_readme_promises_the_first_offer_is_read_only(readme: str) -> None:
    """The safety property is the part worth publishing: nothing the connect
    flow offers of its own accord can spend money."""
    assert "read-only" in readme
    assert "never anything that spends" in readme


def test_the_capability_tour_decision_is_recorded_as_an_adr() -> None:
    """`docs/agents/domain.md` sends the next session to `docs/adr/` before it
    works in an area. A constraint that lives only in SKILL.md prose and its
    tests is a constraint that gets edited away by someone who never saw why."""
    assert TOUR_ADR.exists(), f"the capability tour has no ADR in {TOUR_ADR.parent}"
    adr = unwrapProse(TOUR_ADR.read_text(encoding="utf-8")).lower()
    for claim in ("read-only", "connect time only", "never a tool inventory"):
        assert claim in adr, f"the ADR does not record {claim!r}"


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: str(path.name))
def test_every_relative_link_in_the_docs_resolves(document: Path) -> None:
    """A spec that points at an ADR, or an ADR that points back at its spec, is
    only useful while the path is real."""
    if not document.exists():
        pytest.skip(f"{document.name} is not present")
    for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        resolved = document.parent / target.split("#")[0]
        assert resolved.exists(), f"{document.name}: {label!r} points at missing {target!r}"
