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

from ..components import McpScope, McpState, detectMcp
from ..config import MCP_NAME, MCP_URL
from ..context import Context
from ..exits import Exit
from ..messages import CLAUDE_UNREACHABLE_ACTION, MCP_LOGIN_ACTION, MCP_RECONSENT_ACTION
from ..processes import CommandNotFound

#: Substrings that identify the Claude Code redirect_uri regression in whatever
#: wording the current version happens to use.
_REDIRECT_URI_MARKERS = ("redirect_uri", "redirect uri", "are not registered for this client")


def runRegisterMcp(ctx: Context, *, app_id: str | None = None) -> int:
    existing = detectMcp(ctx)
    if existing.registered and existing.scope is McpScope.LOCAL:
        return _migrateToUserScope(ctx, app_id=app_id)
    if existing.state is McpState.CONNECTED:
        ctx.say(f"Meta's Ads MCP server is already registered as `{MCP_NAME}`. Nothing to do.")
        return int(Exit.OK)
    if existing.state is McpState.NEEDS_LOGIN:
        ctx.say(
            f"Meta's Ads MCP server is already registered as `{MCP_NAME}` — one step left: "
            "log in to Meta."
        )
        ctx.say(f"Next: {MCP_LOGIN_ACTION}")
        return int(Exit.OK)
    if existing.state is McpState.INCOMPLETE:
        ctx.warn(
            f"Meta's Ads MCP server is already registered as `{MCP_NAME}`, but its "
            "connection is not working — the approval may not cover everything the kit needs."
        )
        ctx.warn(f"Next: {MCP_RECONSENT_ACTION}")
        return int(Exit.MCP_INCOMPLETE)
    if existing.state is McpState.UNKNOWN:
        ctx.warn(existing.detail)
        ctx.warn(f"Next: {CLAUDE_UNREACHABLE_ACTION}")
        return int(Exit.CLAUDE_CLI_MISSING)

    try:
        result = ctx.runner.run(_addArgv(app_id), timeout=180)
    except CommandNotFound:
        ctx.warn("The `claude` command is not on your PATH, so the MCP server cannot be registered.")
        ctx.warn(f"Next: {CLAUDE_UNREACHABLE_ACTION}")
        return int(Exit.CLAUDE_CLI_MISSING)

    if result.ok:
        ctx.say(
            f"Registered Meta's Ads MCP server as `{MCP_NAME}`, available in all "
            "your projects."
        )
        ctx.say(f"Next: {MCP_LOGIN_ACTION}")
        return int(Exit.OK)

    if _isRedirectUriBug(result.output) and not app_id:
        ctx.warn(_manualWalkthrough())
        return int(Exit.MCP_NEEDS_APP_ID)

    ctx.warn("Registering Meta's Ads MCP server failed.")
    ctx.warn(result.output.strip())
    ctx.warn("Next: run `meta-ads-connect doctor` for a component-by-component check.")
    return int(Exit.MCP_NEEDS_APP_ID if _isRedirectUriBug(result.output) else Exit.USAGE)


def _addArgv(app_id: str | None) -> list[str]:
    """The registration argv. `--scope user` is the fix for the stranding bug:
    the `claude mcp add` default is local scope, which registers the server
    only inside the folder setup happened to run in."""
    argv = ["claude", "mcp", "add", "--transport", "http", "--scope", "user"]
    if app_id:
        argv += ["--client-id", app_id]
    return argv + [MCP_NAME, MCP_URL]


def _migrateToUserScope(ctx: Context, *, app_id: str | None) -> int:
    """Silently repair a registration stranded at local scope by an older
    version of this kit: remove it there, re-add at user scope, and say why."""
    ctx.say(
        "Meta's Ads MCP server is registered, but only for this folder — an older "
        "version of this kit did that. Moving it so it works in all your projects."
    )
    try:
        removed = ctx.runner.run(
            ["claude", "mcp", "remove", "--scope", "local", MCP_NAME], timeout=180
        )
        result = ctx.runner.run(_addArgv(app_id), timeout=180) if removed.ok else removed
    except CommandNotFound:
        ctx.warn("The `claude` command is not on your PATH, so the registration cannot be moved.")
        ctx.warn(f"Next: {CLAUDE_UNREACHABLE_ACTION}")
        return int(Exit.CLAUDE_CLI_MISSING)

    if not result.ok:
        ctx.warn("Moving the registration failed.")
        ctx.warn(result.output.strip())
        ctx.warn("Next: run `meta-ads-connect doctor` for a component-by-component check.")
        return int(Exit.USAGE)

    moved = detectMcp(ctx)
    if moved.state is McpState.CONNECTED:
        ctx.say("Moved. The connection is registered for all your projects and working.")
        return int(Exit.OK)
    ctx.say("Moved. The registration now covers all your projects.")
    ctx.say(f"Next: {MCP_LOGIN_ACTION}")
    return int(Exit.OK)


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
