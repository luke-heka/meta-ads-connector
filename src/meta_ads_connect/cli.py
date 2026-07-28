"""Argument parsing and dispatch.

Every subcommand is idempotent and safe to re-run, and each returns an exit
code rather than calling ``sys.exit`` itself, so the whole surface can be
driven by tests in-process.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence, TextIO

from .commands.doctor import runDoctor
from .commands.exec_cli import runExec
from .commands.install import runInstall
from .commands.mint_token import runMintToken
from .commands.probe import runProbe
from .commands.register_mcp import runRegisterMcp
from .commands.repair_assets import runRepairAssets
from .commands.store_token import runStoreToken
from .config import CLI_VERSION, RECHECK_DATE
from .context import Context
from .exits import Exit

DESCRIPTION = (
    "Connect Claude to Meta Ads. Every subcommand is safe to run more than once — "
    "start with `probe`, which tells you whether anything needs doing at all."
)


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meta-ads-connect", description=DESCRIPTION)
    parser.add_argument(
        "--version",
        action="version",
        version=f"meta-ads-connect (pinned to Meta's Ads CLI {CLI_VERSION}; re-check due {RECHECK_DATE})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser(
        "probe", help="Live connection check. Always the first action."
    )
    probe.add_argument("--json", action="store_true", help="Machine-readable output.")

    subparsers.add_parser("doctor", help="Component-by-component diagnosis.")

    install = subparsers.add_parser("install", help="Install Meta's official Ads CLI, pinned.")
    install.add_argument(
        "--force", action="store_true", help="Reinstall even if it is already at the pinned version."
    )

    subparsers.add_parser(
        "store-token", help="Store an access token read from standard input."
    )

    mint = subparsers.add_parser(
        "mint-token", help="Drive a browser to create an access token, and store it."
    )
    mint.add_argument("--headless", action="store_true", help="Run the browser without a window.")
    mint.add_argument("--business-id", help="Start in a specific Business Manager.")

    register = subparsers.add_parser(
        "register-mcp", help="Register Meta's official Ads MCP server with Claude Code."
    )
    register.add_argument(
        "--app-id",
        help="Your own Meta app ID. Only needed if registration without one fails.",
    )

    subparsers.add_parser(
        "repair-assets", help="Fix missing Business Manager or unassigned ad account."
    )

    execute = subparsers.add_parser(
        "exec",
        help="Run Meta's Ads CLI with your token in place, e.g. exec -- ads account list.",
    )
    execute.add_argument(
        "argv",
        nargs=argparse.REMAINDER,
        help="The Meta CLI command to run, after `--`.",
    )

    return parser


def run(argv: Sequence[str] | None = None, *, ctx: Context | None = None, stdin: TextIO | None = None) -> int:
    parser = buildParser()
    args = parser.parse_args(argv)
    context = ctx if ctx is not None else Context()

    if args.command == "probe":
        return runProbe(context, as_json=args.json)
    if args.command == "doctor":
        return runDoctor(context)
    if args.command == "install":
        return runInstall(context, force=args.force)
    if args.command == "store-token":
        return runStoreToken(context, source=stdin if stdin is not None else sys.stdin)
    if args.command == "mint-token":
        return runMintToken(context, headless=args.headless, business_id=args.business_id)
    if args.command == "register-mcp":
        return runRegisterMcp(context, app_id=args.app_id)
    if args.command == "repair-assets":
        return runRepairAssets(context)
    if args.command == "exec":
        # argparse.REMAINDER keeps the `--` separator; the CLI never wants it.
        forwarded = [item for item in args.argv if item != "--"]
        return runExec(context, forwarded)

    parser.error(f"unknown command {args.command}")  # pragma: no cover - argparse rejects first
    return int(Exit.USAGE)


def main() -> int:
    return run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
