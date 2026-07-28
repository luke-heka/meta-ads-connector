"""Picking the Python the Ads CLI actually has wheels for.

The CLI is mypyc-compiled with cp312/cp313 wheels and no sdist, so this choice
is the difference between an install that works and one that fails outright.
``install`` records what it settled on; these cover both the recording being
used and it being re-checked rather than trusted.
"""

from __future__ import annotations

import sys

from meta_ads_connect.config import Paths
from meta_ads_connect.interpreter import resolveInterpreter
from meta_ads_connect.state import recordedInterpreter, writeState

from .conftest import FakeCommandRunner

RECORDED_PATH = "/opt/homebrew/opt/python@3.13/bin/python3.13"


def _answers(runner: FakeCommandRunner, path: str, version: str) -> None:
    runner.respond([path, "--version"], stdout=f"Python {version}")


def test_reuses_the_interpreter_a_previous_install_settled_on(
    runner: FakeCommandRunner,
) -> None:
    """The point of recording it. Nothing else is even looked for."""
    _answers(runner, RECORDED_PATH, "3.13.2")

    resolution = resolveInterpreter(runner, recorded=RECORDED_PATH)

    assert resolution.chosen is not None
    assert resolution.chosen.path == RECORDED_PATH
    assert runner.calls == [(RECORDED_PATH, "--version")]


def test_searches_again_when_the_recorded_interpreter_has_gone(
    runner: FakeCommandRunner,
) -> None:
    """An interpreter can be uninstalled between runs, so it is re-checked
    rather than trusted — a recorded path is a candidate, not a fact."""
    runner.onPath("python3.13", "/usr/local/bin/python3.13")
    _answers(runner, "/usr/local/bin/python3.13", "3.13.1")

    resolution = resolveInterpreter(runner, recorded="/gone/python3.13")

    assert resolution.chosen is not None
    assert resolution.chosen.path == "/usr/local/bin/python3.13"


def test_searches_again_when_the_recorded_interpreter_is_no_longer_supported(
    runner: FakeCommandRunner,
) -> None:
    """A recorded 3.13 that has since been upgraded to 3.14 has no wheel any
    more. Reusing it on the strength of the recording would fail the install."""
    _answers(runner, RECORDED_PATH, "3.14.0")
    runner.onPath("python3.12", "/usr/local/bin/python3.12")
    _answers(runner, "/usr/local/bin/python3.12", "3.12.7")

    resolution = resolveInterpreter(runner, recorded=RECORDED_PATH)

    assert resolution.chosen is not None
    assert resolution.chosen.version == (3, 12)


def test_counts_one_interpreter_once_when_two_names_point_at_it(
    runner: FakeCommandRunner,
) -> None:
    """`python3.13` and `python3` are routinely the same binary. Listing it
    twice would tell an owner they have two Pythons when they have one."""
    shared = "/opt/homebrew/bin/python3.13"
    runner.onPath("python3.13", shared)
    runner.onPath("python3", shared)
    _answers(runner, shared, "3.13.2")

    resolution = resolveInterpreter(runner)

    paths_found = [found.path for found in resolution.considered]
    assert paths_found.count(shared) == 1
    assert runner.calls.count((shared, "--version")) == 1


def test_an_unusable_interpreter_is_named_rather_than_reported_as_absent(
    runner: FakeCommandRunner,
) -> None:
    """A business owner cannot act on "no suitable Python found"; they can act
    on "you have 3.14, the Ads CLI needs 3.13"."""
    runner.onPath("python3", "/usr/bin/python3")
    _answers(runner, "/usr/bin/python3", "3.14.0")

    resolution = resolveInterpreter(runner)

    assert resolution.chosen is None
    assert "3.14" in resolution.explain()
    assert "brew install python@3.13" in resolution.explain()


def test_falls_back_to_the_running_interpreter_when_nothing_is_on_path(
    runner: FakeCommandRunner,
) -> None:
    """Covers a virtualenv or a pyenv shim that publishes no suffixed name."""
    resolution = resolveInterpreter(runner)

    assert [found.path for found in resolution.considered] == [sys.executable]


def test_no_recorded_interpreter_before_anything_has_been_installed(paths: Paths) -> None:
    assert recordedInterpreter(paths) is None


def test_the_recorded_interpreter_survives_a_round_trip(paths: Paths) -> None:
    writeState(paths, {"interpreter_path": RECORDED_PATH})

    assert recordedInterpreter(paths) == RECORDED_PATH


def test_a_state_file_holding_nonsense_is_treated_as_no_recording(paths: Paths) -> None:
    """Being wrong about this is cheap to recover from and expensive to crash on."""
    writeState(paths, {"interpreter_path": 12})

    assert recordedInterpreter(paths) is None
