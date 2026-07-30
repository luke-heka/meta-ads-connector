"""Pinned constants and filesystem locations.

Everything the kit deliberately holds still lives here: the Ads CLI version, the
interpreter versions it has wheels for, and the Graph API version. See
``docs/research/findings-and-decisions.md`` section 9 for why each one is pinned.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# --- Pins ------------------------------------------------------------------

#: The official Meta Ads CLI on PyPI. Not ``@meta/ads-cli`` on npm, which has
#: never existed in any registry despite what most of the web says.
CLI_PACKAGE = "meta-ads"

#: Pinned so an upstream release cannot break a working setup overnight. There
#: is no public changelog and no public repo, so change detection is manual.
CLI_VERSION = "1.1.0"

#: The binary the CLI installs into its environment.
CLI_BINARY = "meta"

#: Interpreters the Ads CLI ships wheels for, most preferred first. It is
#: mypyc-compiled with no sdist, so an unlisted version fails outright rather
#: than falling back to a source build.
SUPPORTED_PYTHONS: tuple[tuple[int, int], ...] = ((3, 13), (3, 12))

#: Pinned explicitly. An expired Graph version silently defaults to the next
#: oldest rather than erroring, which degrades quietly instead of failing loudly.
GRAPH_API_VERSION = "v25.0"
GRAPH_HOST = "https://graph.facebook.com"

#: Meta's official Ads MCP server. Unversioned and unpinnable — treat its tool
#: names as unstable and discover them at run time.
MCP_URL = "https://mcp.facebook.com/ads"
MCP_NAME = "meta-ads"

#: Fixed, not offered as a choice. A business owner has no basis on which to
#: choose, and a token missing write scope makes the whole kit pointless.
#: Safety is behavioural (confirm before spend), not permissional.
#:
#: ``business_management`` is not in the spec's list of four, and is here
#: because without it ``repair-assets`` cannot do the job the same spec gives
#: it: reading `/me/businesses` and assigning an ad account to the system user
#: both require it. See docs/adr/0001-business-manager-repair-scope.md.
REQUIRED_SCOPES: tuple[str, ...] = (
    "ads_management",
    "ads_read",
    "pages_show_list",
    "leads_retrieval",
    "business_management",
)

#: Whoever owns this kit re-checks the whole picture on this date.
RECHECK_DATE = "September 2026"

#: The environment variable name the Ads CLI reads its token from. Verified
#: against the running 1.1.0 binary — it is unprefixed, and prefixing it
#: ``META_`` reports "Not authenticated" while naming ``ACCESS_TOKEN`` in the
#: error. Most third-party Meta MCP servers do use ``META_ACCESS_TOKEN``, which
#: is where the wrong name came from.
TOKEN_ENV_VAR = "ACCESS_TOKEN"

#: The name this kit wrote before the one above was verified. Accepted when
#: reading a stored token or a pasted line so an early setup keeps working;
#: never written.
LEGACY_TOKEN_ENV_VAR = "META_ACCESS_TOKEN"

#: Overrides the kit's home directory. Used by the test suite; also lets an
#: owner relocate the token file if they want to.
HOME_ENV_VAR = "META_ADS_CONNECT_HOME"


# --- Locations -------------------------------------------------------------


@dataclass(frozen=True)
class Paths:
    """Everywhere the kit writes. Nothing is written outside ``root``.

    No shell profile is edited and nothing goes into an OS keychain, so
    uninstalling is ``rm -rf`` on ``root`` plus one ``claude mcp remove``.
    """

    root: Path

    @property
    def env_file(self) -> Path:
        """The token file. Mode 600, inside a mode 700 directory."""
        return self.root / ".env"

    @property
    def venv(self) -> Path:
        """Isolated environment for the Ads CLI, owned by the kit."""
        return self.root / "venv"

    @property
    def venv_bin(self) -> Path:
        return self.venv / ("Scripts" if os.name == "nt" else "bin")

    @property
    def cli_binary(self) -> Path:
        suffix = ".exe" if os.name == "nt" else ""
        return self.venv_bin / f"{CLI_BINARY}{suffix}"

    @property
    def state_file(self) -> Path:
        """Records the resolved interpreter so later runs need not re-resolve."""
        return self.root / "state.json"

    @property
    def diagnostic_file(self) -> Path:
        """Where ``doctor`` writes its redacted help bundle. Safe to share."""
        return self.root / "diagnostic.txt"


def defaultPaths(environ: dict[str, str] | None = None) -> Paths:
    env = os.environ if environ is None else environ
    override = env.get(HOME_ENV_VAR)
    if override:
        return Paths(root=Path(override))
    return Paths(root=Path(env.get("HOME", str(Path.home()))) / ".meta-ads")
