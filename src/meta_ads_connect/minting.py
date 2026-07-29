"""Browser-driven minting of a system user token.

The whole Playwright surface is deliberately narrowed to one function with one
job: return a token string, or None. Everything downstream of that boundary —
storing it, checking it, repairing account state — is ordinary code the test
suite drives directly. The browser flow itself is covered by the live
run-through rather than by the automated suite, because a fake browser proves
nothing about a real one.

The token is carried from browser to disk in memory. It is never rendered to
the transcript, never echoed, and never asked of the owner by hand. The one
unavoidably human moment is the Meta login, which is announced before the
browser opens.

The selectors below are ported from ``platforms/meta/playwright/03-system-user.spec.ts``
in the ``marketing-agency-workshop`` repo, which has driven this flow against
real Business Managers. They are role- and label-based rather than structural,
because Meta's Business Settings markup changes without notice.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from .config import REQUIRED_SCOPES
from .messages import noBusinessManager

SYSTEM_USERS_URL = "https://business.facebook.com/settings/system-users"

#: Where Meta sends anyone without a Business Manager. A system user lives
#: inside one, so this is the single point in the whole kit where "no Business
#: Manager" is genuinely reachable: it happens before any token exists, which
#: is why no token-driven command can detect it.
BUSINESS_CREATION_URL = "https://business.facebook.com/overview"

#: Meta access tokens all start this way. Checking it is how we avoid storing
#: some other text the page happened to be showing.
TOKEN_PREFIX = "EAA"

#: The owner has to log in and, on Meta's current UI, tick the permission list
#: by hand. Both are slow and human-paced.
HUMAN_STEP_TIMEOUT_MS = 300_000

LOGIN_ANNOUNCEMENT = """A browser window is about to open on Meta's Business Settings page.

Two things to know before it does:

  • You will need to log in to Meta yourself. That is the one part of this that
    cannot be done for you — your password should never pass through anything
    but Meta's own login page.
  • After you log in, leave the window alone. The rest is automatic, and the
    access token will be saved straight to this machine. It will not be shown
    on screen and you will not need to copy anything.

This usually takes two or three minutes."""

MANUAL_FALLBACK = f"""The browser could not complete this on its own — Meta changes these pages
often, and this one has moved.

You can do it by hand in about three minutes, and your token still will not go
through this chat:

  1. If you do not have a Business Manager yet, create one first at
     {BUSINESS_CREATION_URL} — click "Create account" and use your business
     name, your name and your email. Everything below lives inside it.
  2. Go to {SYSTEM_USERS_URL}
  3. Click "Add", name the system user anything you like, give it the Admin
     role, and create it.
  4. Click "Generate new token", choose your app, and tick these permissions:
       {", ".join(REQUIRED_SCOPES)}
  5. Set the expiry to "Never".
  6. Copy the token. Then, without pasting it anywhere else, run:
       pbpaste | meta-ads-connect store-token      (macOS)
       xclip -o | meta-ads-connect store-token     (Linux)"""

#: How Meta's no-Business-Manager state reads. Kept alongside the URL check
#: because Meta has moved this page before and the wording outlasts the path.
_NO_BUSINESS_SIGNS = ("create a business", "create an account", "create account")


class TokenMinter(Protocol):
    """Return a fresh system user token, or None if the flow did not complete."""

    def __call__(
        self, *, announce: Callable[[str], None], headless: bool = False, business_id: str | None = None
    ) -> str | None: ...


class MintingUnavailable(RuntimeError):
    """Playwright is not installed, so no browser can be driven."""


class BusinessManagerMissing(RuntimeError):
    """The owner has no Business Manager, so no system user can exist yet.

    Signalled rather than returned as a plain "it did not work", because the
    two need different things said: this one has a two-minute fix the owner can
    do, where a moved selector needs the manual token walkthrough instead.
    """


def mintSystemUserToken(
    *,
    announce: Callable[[str], None],
    headless: bool = False,
    business_id: str | None = None,
) -> str | None:
    """Drive a browser through Meta's system user token flow.

    Returns the token, or None when the flow did not complete — in which case
    the caller falls back to the manual path, which still works. Raises
    :class:`MintingUnavailable` only when Playwright itself is missing, because
    that is a setup problem with a different fix.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise MintingUnavailable(
            "Minting a token needs the browser automation extra.\n"
            "Next: install it with `pip install 'meta-ads-connect[mint]'` "
            "and then `playwright install chromium`."
        ) from exc

    announce(LOGIN_ANNOUNCEMENT)

    needs_business_manager = False
    with sync_playwright() as playwright:  # pragma: no cover - live browser only
        browser = playwright.chromium.launch(headless=headless)
        try:
            page = browser.new_page()
            page.goto(_startUrl(business_id), wait_until="domcontentloaded")
            try:
                token = driveTokenFlow(page, announce=announce)
            except BusinessManagerMissing:
                token, needs_business_manager = None, True
        finally:
            browser.close()

    if needs_business_manager:
        announce(noBusinessManager(next_command="mint-token"))
    elif token is None:
        announce(MANUAL_FALLBACK)
    return token


def _startUrl(business_id: str | None) -> str:
    return f"{SYSTEM_USERS_URL}?business_id={business_id}" if business_id else SYSTEM_USERS_URL


def driveTokenFlow(page: Any, *, announce: Callable[[str], None]) -> str | None:
    """The Meta-specific clicking, isolated so the rest of the kit never sees it.

    Written to fail by returning None rather than by raising: a failed mint
    should drop the owner into the manual path, not into a stack trace. The one
    exception is a missing Business Manager, which is not a failure of this
    flow but a prerequisite the owner has to create, and so is raised.
    """
    try:
        _waitForLogin(page, announce=announce)
        if needsBusinessManager(url=page.url, page_text=_bodyText(page)):
            # The one prerequisite the kit cannot create, at the one point it
            # is reachable. Raised rather than swallowed so the owner is told
            # to create one, instead of being handed token instructions for a
            # Business Manager that does not exist.
            raise BusinessManagerMissing
        _ensureSystemUser(page)
        _openTokenDialog(page)
        _selectScopes(page, announce=announce)
        token = _readToken(page)
    except BusinessManagerMissing:
        raise
    except Exception:  # noqa: BLE001 - any browser failure means "use the manual path"
        return None

    if not token or not token.startswith(TOKEN_PREFIX):  # pragma: no cover - live browser only
        return None
    return token


def needsBusinessManager(*, url: str, page_text: str) -> bool:
    """Is the browser looking at Meta's "you have no Business Manager" state?

    Meta redirects an owner who has none away from Business Settings and onto
    its creation page, so the URL is the first signal. The wording is a second
    one, kept because Meta has moved this page before and the words outlast the
    path. A page still inside Business Settings is never this state — that
    guard is what stops the ordinary "Add" button reading as an empty account.
    """
    if "/overview" in url or "/creation" in url:
        return True
    if "/settings/" in url:
        return False
    lowered = page_text.lower()
    return any(sign in lowered for sign in _NO_BUSINESS_SIGNS)


def _bodyText(page: Any) -> str:  # pragma: no cover - live browser only
    try:
        text = page.inner_text("body")
    except Exception:  # noqa: BLE001 - a page that will not yield text is not this state
        return ""
    return str(text or "")


# --- Steps -----------------------------------------------------------------
# Every one of these runs only against a live browser, so none are exercised by
# the automated suite. Their contract to the rest of the kit is the single
# function above.


def _waitForLogin(page: Any, *, announce: Callable[[str], None]) -> None:  # pragma: no cover
    if "login" not in page.url and "checkpoint" not in page.url:
        return
    announce("Waiting for you to finish logging in to Meta...")
    page.wait_for_url("**/settings/**", timeout=HUMAN_STEP_TIMEOUT_MS)


def _ensureSystemUser(page: Any) -> None:  # pragma: no cover
    """Create a system user, unless one already exists.

    Re-running setup must not leave a trail of duplicate system users, so an
    existing one is reused.
    """
    generate = page.get_by_role("button", name="Generate new token")
    if generate.count() > 0:
        return

    page.get_by_role("button", name="Add").first.click()
    page.get_by_label("Name").fill("claude-meta-ads")
    page.get_by_label("Role").select_option(label="Admin")
    page.get_by_role("button", name="Create").click()


def _openTokenDialog(page: Any) -> None:  # pragma: no cover
    page.get_by_role("button", name="Generate new token").first.click()


def _selectScopes(page: Any, *, announce: Callable[[str], None]) -> None:  # pragma: no cover
    """Tick the permissions the kit needs.

    Meta has moved this control more than once. Where a checkbox cannot be
    found, the owner is asked to tick it — which is slower but never wrong.
    """
    missed: list[str] = []
    for scope in REQUIRED_SCOPES:
        checkbox = page.get_by_label(scope, exact=False)
        if checkbox.count() == 0:
            missed.append(scope)
            continue
        if not checkbox.first.is_checked():
            checkbox.first.check()

    if missed:
        announce(
            "Please tick these permissions in the browser window, then click "
            f"'Generate token':\n    {', '.join(missed)}"
        )

    page.get_by_role("button", name="Generate token").last.click()


def _readToken(page: Any) -> str | None:  # pragma: no cover
    """Read the token out of the page. Never printed, only returned."""
    display = page.locator("[data-testid='access-token-display']")
    display.first.wait_for(timeout=HUMAN_STEP_TIMEOUT_MS)
    text = display.first.inner_text()
    return text.strip() if text else None
