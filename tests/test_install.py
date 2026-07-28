"""``install`` pins two things — the package version and the interpreter — and
has to explain itself when neither can be satisfied. Python 3.14 failing is a
handled case, not a hypothetical: it was hit twice during research.
"""

from __future__ import annotations

import json
import sys

import pytest

from meta_ads_connect.commands.install import runInstall
from meta_ads_connect.config import CLI_VERSION, Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit

from .conftest import FakeCommandRunner, Recorder, installedCli


def _pythonOnPath(runner: FakeCommandRunner, version: str) -> None:
    major_minor = ".".join(version.split(".")[:2])
    program = f"python{major_minor}"
    runner.onPath(program, f"/opt/homebrew/bin/{program}")
    runner.respond([program, "--version"], stdout=f"Python {version}")


def _installSucceeds(runner: FakeCommandRunner) -> None:
    runner.respond(["-m", "venv"], stdout="")
    runner.respond(["-m", "pip", "install"], stdout=f"Successfully installed meta-ads-{CLI_VERSION}")
    runner.respond(["meta", "--version"], stdout=f"meta-ads {CLI_VERSION}")


def test_installs_the_pinned_version_on_python_313(
    ctx: Context, runner: FakeCommandRunner, paths: Paths, out: Recorder
) -> None:
    _pythonOnPath(runner, "3.13.2")
    _installSucceeds(runner)

    assert runInstall(ctx) == Exit.OK
    assert runner.ranCommandContaining("-m", "pip", "install", f"meta-ads=={CLI_VERSION}")
    assert "Python 3.13" in out.text


def test_accepts_python_312_when_313_is_absent(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    _pythonOnPath(runner, "3.12.7")
    _installSucceeds(runner)

    assert runInstall(ctx) == Exit.OK
    assert "Python 3.12" in out.text


def test_prefers_313_when_both_are_present(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    _pythonOnPath(runner, "3.12.7")
    _pythonOnPath(runner, "3.13.2")
    _installSucceeds(runner)

    runInstall(ctx)

    assert "Python 3.13" in out.text
    assert runner.ranCommandContaining("python3.13", "-m", "venv")


def test_refuses_python_314_and_names_what_it_found(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    """The Ads CLI is compiled with no source fallback, so 3.14 cannot be made
    to work. Saying so beats letting pip fail with a wall of red."""
    runner.onPath("python3", "/opt/homebrew/bin/python3")
    runner.respond(["python3", "--version"], stdout="Python 3.14.5")

    assert runInstall(ctx) == Exit.UNUSABLE_PYTHON
    assert "3.14" in err.text
    assert "3.13" in err.text
    assert "brew install python@3.13" in err.text


def test_reports_no_python_at_all_actionably(
    ctx: Context, err: Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only reachable from an interpreter that does not know its own path, but
    the message still has to tell the owner what to install."""
    monkeypatch.setattr(sys, "executable", "")

    assert runInstall(ctx) == Exit.UNUSABLE_PYTHON
    assert "No Python was found" in err.text
    assert "3.13" in err.text


def test_skips_the_work_when_already_at_the_pinned_version(
    ctx: Context, runner: FakeCommandRunner, paths: Paths, out: Recorder
) -> None:
    installedCli(runner, paths)

    assert runInstall(ctx) == Exit.OK
    assert "already installed" in out.text
    assert not runner.ranCommandContaining("-m", "pip", "install")


def test_reinstalls_when_a_different_version_is_present(
    ctx: Context, runner: FakeCommandRunner, paths: Paths, out: Recorder
) -> None:
    installedCli(runner, paths, version="1.0.0")
    _pythonOnPath(runner, "3.13.2")
    runner.respond(["-m", "venv"], stdout="")
    runner.respond(["-m", "pip", "install"], stdout="ok")

    assert runInstall(ctx) == Exit.OK
    assert "1.0.0" in out.text
    assert runner.ranCommandContaining("-m", "pip", "install", f"meta-ads=={CLI_VERSION}")


def test_force_reinstalls_even_at_the_pinned_version(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    installedCli(runner, paths)
    _pythonOnPath(runner, "3.13.2")
    _installSucceeds(runner)

    assert runInstall(ctx, force=True) == Exit.OK
    assert runner.ranCommandContaining("-m", "pip", "install")


def test_reports_a_failed_pip_install_with_a_next_action(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    _pythonOnPath(runner, "3.13.2")
    runner.respond(["-m", "venv"], stdout="")
    runner.fails(
        ["-m", "pip", "install"],
        stderr="ERROR: Could not find a version that satisfies the requirement meta-ads==1.1.0",
    )

    assert runInstall(ctx) == Exit.INSTALL_FAILED
    assert "Next:" in err.text
    assert "3.13" in err.text


def test_reports_a_failed_environment_creation(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    _pythonOnPath(runner, "3.13.2")
    runner.fails(["-m", "venv"], stderr="PermissionError: [Errno 13] Permission denied")

    assert runInstall(ctx) == Exit.INSTALL_FAILED
    assert "Next:" in err.text


def test_reports_an_install_that_leaves_a_binary_that_does_not_run(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    _pythonOnPath(runner, "3.13.2")
    runner.respond(["-m", "venv"], stdout="")
    runner.respond(["-m", "pip", "install"], stdout="Successfully installed")
    runner.fails(["meta", "--version"], stderr="Segmentation fault")

    assert runInstall(ctx) == Exit.INSTALL_FAILED
    assert "doctor" in err.text


def test_tells_windows_users_to_use_wsl_instead_of_trying(
    ctx: Context, runner: FakeCommandRunner, err: Recorder
) -> None:
    ctx.platform = "win32"

    assert runInstall(ctx) == Exit.UNSUPPORTED_PLATFORM
    assert "WSL" in err.text
    assert runner.calls == []


def test_records_the_resolved_interpreter_so_later_runs_need_not_re_resolve(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    _pythonOnPath(runner, "3.13.2")
    _installSucceeds(runner)

    runInstall(ctx)

    state = json.loads(paths.state_file.read_text())
    assert state["interpreter_version"] == "3.13"
    assert state["interpreter_path"].endswith("python3.13")
    assert state["cli_version"] == CLI_VERSION


def test_installs_into_an_environment_the_kit_owns(
    ctx: Context, runner: FakeCommandRunner, paths: Paths
) -> None:
    """So it cannot collide with the owner's other Python work."""
    _pythonOnPath(runner, "3.13.2")
    _installSucceeds(runner)

    runInstall(ctx)

    venv_calls = [call for call in runner.calls if "venv" in call]
    assert any(str(paths.venv) in call for call in venv_calls)


def test_installs_its_own_copy_even_when_the_owner_already_has_one(
    ctx: Context, runner: FakeCommandRunner, out: Recorder
) -> None:
    """An external CLI is fine to use, but the kit still wants its own pinned
    copy — otherwise unrelated Python work can change the version underneath it."""
    runner.onPath("meta", "/opt/homebrew/bin/meta")
    runner.respond(["meta", "--version"], stdout=f"meta-ads {CLI_VERSION}")
    _pythonOnPath(runner, "3.13.2")
    runner.respond(["-m", "venv"], stdout="")
    runner.respond(["-m", "pip", "install"], stdout="ok")

    assert runInstall(ctx) == Exit.OK
    assert runner.ranCommandContaining("-m", "pip", "install", f"meta-ads=={CLI_VERSION}")
    assert "Leaving that alone" in out.text
