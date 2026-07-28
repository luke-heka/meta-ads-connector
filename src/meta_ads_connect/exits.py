"""Exit codes.

Every subcommand's verdict is carried by its exit code so a caller — Claude,
a shell script, a CI job — can branch without parsing prose. Codes are stable;
adding a state means adding a number, never renumbering an existing one.
"""

from __future__ import annotations

from enum import IntEnum


class Exit(IntEnum):
    """Shared exit codes. 0 always means "nothing to do"."""

    OK = 0

    # --- probe: the connection verdict ------------------------------------
    #: A token is stored but Meta rejected it. Re-mint.
    TOKEN_REJECTED = 1
    #: The Ads CLI is installed but there is no usable token on disk.
    NO_TOKEN = 2
    #: Nothing is installed. Full setup needed.
    NOT_INSTALLED = 3
    #: Meta is throttling. Says nothing about the setup — wait and retry.
    RATE_LIMITED = 4
    #: Meta was never reached. Also says nothing about the setup.
    NETWORK_ERROR = 5
    #: CLI and token are live; only the MCP server is missing. Repair that
    #: piece alone rather than restarting the whole setup.
    MCP_MISSING = 6
    #: The token authenticated but sees no ad accounts. An assignment problem,
    #: not a credential problem.
    NO_AD_ACCOUNTS = 7
    #: Meta answered with something we could not interpret. Says nothing about
    #: the setup either way.
    META_ERROR = 8

    # --- setup subcommands ------------------------------------------------
    #: No interpreter with an Ads CLI wheel, or the install itself failed.
    UNUSABLE_PYTHON = 10
    INSTALL_FAILED = 11
    #: Windows without WSL. There is no wheel; attempting it wastes an hour.
    UNSUPPORTED_PLATFORM = 12
    #: MCP registration hit the Claude Code redirect_uri regression. The
    #: bring-your-own-app walkthrough was printed.
    MCP_NEEDS_APP_ID = 13
    #: register-mcp could not find the `claude` command.
    CLAUDE_CLI_MISSING = 14
    #: repair-assets found no Business Manager to work with.
    NEEDS_BUSINESS_MANAGER = 15
    #: A repair was attempted against Meta and failed.
    REPAIR_FAILED = 16
    #: A Business Manager exists but owns no ad account. Only the owner can
    #: create one, because it carries their billing details.
    NEEDS_AD_ACCOUNT = 17

    #: Bad arguments or an unexpected internal failure.
    USAGE = 64
