"""``register-mcp`` — add Meta's official Ads MCP server to Claude Code.

Two tiers, in order.

1. Register with no App ID. Meta runs a ``client_name``-allowlisted pseudo-DCR
   that hands a first-party Meta app to any caller identifying as Claude, so
   this normally just works and asks nothing of the owner.
2. On the redirect_uri failure — a Claude Code regression (anthropics/claude-code
   #37747), not a Meta requirement — fall back to a bring-your-own developer app.

The fallback is walked through by hand on purpose. It needs a logged-in Meta
session and the redirect-URL step is app-settings config that fails silently
under automation, which is worse than not automating it at all.
"""

from __future__ import annotations

from ..components import McpState, detectMcp
from ..config import MCP_NAME, MCP_URL
from ..context import Context
from ..exits import Exit
from ..processes import CommandNotFound

#: Substrings that identify the Claude Code redirect_uri regression in whatever
#: wording the current version happens to use.
_REDIRECT_URI_MARKERS = ("redirect_uri", "redirect uri", "are not registered for this client")


def runRegisterMcp(ctx: Context, *, app_id: str | None = None) -> int:
    existing = detectMcp(ctx)
    if existing.state is McpState.REGISTERED:
        ctx.say(f"Meta's Ads MCP server is already registered as `{MCP_NAME}`. Nothing to do.")
        return int(Exit.OK)
    if existing.state is McpState.UNKNOWN:
        ctx.warn(existing.detail)
        ctx.warn(
            "Next: this step needs the Claude Code command line tool. "
            "If you are using Claude inside the desktop app, add the connector there instead: "
            f"Settings → Connectors → Add custom connector → {MCP_URL}"
        )
        return int(Exit.CLAUDE_CLI_MISSING)

    argv = ["claude", "mcp", "add", "--transport", "http"]
    if app_id:
        argv += ["--client-id", app_id]
    argv += [MCP_NAME, MCP_URL]

    try:
        result = ctx.runner.run(argv, timeout=180)
    except CommandNotFound:
        ctx.warn("The `claude` command is not on your PATH, so the MCP server cannot be registered.")
        return int(Exit.CLAUDE_CLI_MISSING)

    if result.ok:
        ctx.say(f"Registered Meta's Ads MCP server as `{MCP_NAME}`.")
        ctx.say(
            "Next: the first time Claude uses it you will be asked to approve access "
            "in your browser. That is expected."
        )
        return int(Exit.OK)

    if _isRedirectUriBug(result.output) and not app_id:
        ctx.warn(_manualWalkthrough())
        return int(Exit.MCP_NEEDS_APP_ID)

    ctx.warn("Registering Meta's Ads MCP server failed.")
    ctx.warn(result.output.strip())
    ctx.warn("Next: run `meta-ads-connect doctor` for a component-by-component check.")
    return int(Exit.MCP_NEEDS_APP_ID if _isRedirectUriBug(result.output) else Exit.USAGE)


def _isRedirectUriBug(output: str) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in _REDIRECT_URI_MARKERS)


def _manualWalkthrough() -> str:
    """The bring-your-own-app fallback, written for someone who has never seen
    developers.facebook.com. It is deliberately not automated."""
    return f"""Claude Code could not register the connector on its own.

This is a known bug in Claude Code itself, not a problem with your Meta account
and not something you did wrong. The way around it is to point the connector at
your own Meta app. It takes about five minutes, needs no approval from Meta, and
costs nothing.

  1. Go to https://developers.facebook.com/apps and sign in with the same Meta
     account you use for your ads.
  2. Click "Create app". Give it any name — "My Ads Connector" is fine.
  3. When asked what you want the app to do, choose "Other", then "Business".
  4. Once it is created, open "App settings" → "Basic" and copy the App ID.
     It is a long number.
  5. In the left menu, add the "Facebook Login" product. Under its settings,
     find "Valid OAuth Redirect URIs" and add both of these, then save:
         http://localhost:PORT/callback
         https://claude.ai/api/mcp/auth_callback
     Replace PORT with 8080 for now — if registration still fails, Claude will
     tell you the exact port to use.
  6. Come back here and run:
         meta-ads-connect register-mcp --app-id YOUR_APP_ID

Leave the app in development mode. You do not need App Review and you do not
need business verification — those are only for apps that manage other people's
ad accounts. Yours only manages your own."""
