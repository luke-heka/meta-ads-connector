"""``install`` — put the official Ads CLI on the machine, at a pinned version.

Two things are pinned, and pinning either one alone is insufficient: the
package version, so an upstream release cannot break a working setup overnight,
and the interpreter, because the CLI is mypyc-compiled with cp312/cp313 wheels
and no sdist. It goes into an environment the kit owns, so it cannot collide
with the owner's other Python work.
"""

from __future__ import annotations

from ..components import detectCli, parseVersion
from ..config import CLI_PACKAGE, CLI_VERSION
from ..context import Context
from ..exits import Exit
from ..interpreter import resolveInterpreter
from ..processes import CommandNotFound
from ..state import recordedInterpreter, writeState

WINDOWS_MESSAGE = (
    "Meta's Ads CLI has no Windows build — there is no version of it that can run here.\n"
    "It works fine under WSL (Windows Subsystem for Linux). Install WSL, open an Ubuntu\n"
    "terminal, and run this setup again from there."
)


def runInstall(ctx: Context, *, force: bool = False) -> int:
    if ctx.is_windows:
        ctx.warn(WINDOWS_MESSAGE)
        return int(Exit.UNSUPPORTED_PLATFORM)

    existing = detectCli(ctx)
    if existing.pinned and not existing.external and not force:
        ctx.say(f"Meta's Ads CLI {CLI_VERSION} is already installed. Nothing to do.")
        return int(Exit.OK)
    if existing.external:
        # Someone else's `meta` is good enough to *use*, but installing into
        # the kit's own environment is what keeps the pinned version from
        # being changed out from under us by unrelated Python work.
        ctx.say(
            "You already have Meta's Ads CLI installed elsewhere. Leaving that alone and "
            f"installing this kit's own copy at {CLI_VERSION}, so the two cannot interfere."
        )
    elif existing.installed and not force:
        ctx.say(
            f"Found Meta's Ads CLI at version {existing.version or 'unknown'}; "
            f"this kit is built and tested against {CLI_VERSION}. Reinstalling at that version."
        )

    resolution = resolveInterpreter(ctx.runner, recorded=recordedInterpreter(ctx.paths))
    if resolution.chosen is None:
        ctx.warn(resolution.explain())
        return int(Exit.UNUSABLE_PYTHON)

    interpreter = resolution.chosen
    ctx.say(f"Using {interpreter.label}.")

    created = ctx.runner.run([interpreter.path, "-m", "venv", "--clear", str(ctx.paths.venv)], timeout=300)
    if not created.ok:
        ctx.warn("Could not create the environment for Meta's Ads CLI.")
        ctx.warn(created.output.strip())
        ctx.warn(f"Next: check you can write to {ctx.paths.root}, then run install again.")
        return int(Exit.INSTALL_FAILED)

    venv_python = str(ctx.paths.venv_bin / "python")
    requirement = f"{CLI_PACKAGE}=={CLI_VERSION}"
    ctx.say(f"Installing {requirement}. This usually takes under a minute.")

    installed = ctx.runner.run(
        [venv_python, "-m", "pip", "install", "--disable-pip-version-check", requirement],
        timeout=900,
    )
    if not installed.ok:
        ctx.warn(f"Installing {requirement} failed.")
        ctx.warn(installed.output.strip())
        ctx.warn(_installFailureHint(installed.output))
        return int(Exit.INSTALL_FAILED)

    verified = _verify(ctx)
    if verified is None:
        ctx.warn(
            f"{requirement} installed, but the `meta` command did not run afterwards.\n"
            f"Next: run `meta-ads-connect doctor` for the detail."
        )
        return int(Exit.INSTALL_FAILED)

    writeState(
        ctx.paths,
        {
            "interpreter_path": interpreter.path,
            "interpreter_version": f"{interpreter.version[0]}.{interpreter.version[1]}",
            "cli_version": verified or CLI_VERSION,
            "cli_package": CLI_PACKAGE,
        },
    )
    ctx.say(f"Meta's Ads CLI {verified or CLI_VERSION} is installed.")
    ctx.say("Next: run `meta-ads-connect mint-token` to mint and save an access token.")
    return int(Exit.OK)


def _verify(ctx: Context) -> str | None:
    """Run the freshly installed binary. Returns its version, or None if it failed.

    An empty string means it ran but did not report a recognisable version —
    still a success, because the binary works.
    """
    try:
        result = ctx.runner.run([str(ctx.paths.cli_binary), "--version"], timeout=60)
    except CommandNotFound:
        return None
    if not result.ok:
        return None
    return parseVersion(result.output)


def _installFailureHint(output: str) -> str:
    lowered = output.lower()
    if "no matching distribution" in lowered or "could not find a version" in lowered:
        return (
            "Next: this usually means the Python being used has no build of the Ads CLI. "
            "Install Python 3.13 (brew install python@3.13) and run install again."
        )
    if "permission denied" in lowered:
        return "Next: check the permissions on your home directory, then run install again."
    if "network" in lowered or "timed out" in lowered or "temporary failure" in lowered:
        return "Next: check your internet connection and run install again."
    return "Next: run `meta-ads-connect doctor` for a component-by-component check."
