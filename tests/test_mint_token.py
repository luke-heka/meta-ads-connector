"""The Playwright flow is not driven here. Its contract is narrowed to one
function that returns a token string or None, and both sides of that boundary
are covered: everything downstream of a returned token, and correct handling
when the flow yields nothing.

The browser flow itself is covered by the live run-through, because a fake
browser proves nothing about a real one.
"""

from __future__ import annotations

import stat
from typing import Callable

from meta_ads_connect.commands.mint_token import runMintToken
from meta_ads_connect.config import Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.minting import MintingUnavailable
from meta_ads_connect.tokens import readToken, writeToken

from .conftest import VALID_TOKEN, Recorder

OLD_TOKEN = "EAAoldtokenvaluethatisalsolongenoughtolooklikearealcredential00"


def _returns(token: str | None) -> Callable[..., str | None]:
    def minter(*, announce: Callable[[str], None], headless: bool = False, business_id: str | None = None) -> str | None:
        return token

    return minter


def test_stores_a_minted_token_without_it_passing_through_the_conversation(
    ctx: Context, paths: Paths, out: Recorder, err: Recorder
) -> None:
    assert runMintToken(ctx, minter=_returns(VALID_TOKEN)) == Exit.OK
    assert readToken(paths) == VALID_TOKEN
    assert VALID_TOKEN not in out.text
    assert VALID_TOKEN not in err.text


def test_the_stored_token_is_readable_only_by_its_owner(ctx: Context, paths: Paths) -> None:
    runMintToken(ctx, minter=_returns(VALID_TOKEN))

    assert stat.S_IMODE(paths.env_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(paths.root.stat().st_mode) == 0o700


def test_replaces_a_previous_token_when_re_minting(ctx: Context, paths: Paths) -> None:
    writeToken(paths, OLD_TOKEN)

    runMintToken(ctx, minter=_returns(VALID_TOKEN))

    assert readToken(paths) == VALID_TOKEN
    assert OLD_TOKEN not in paths.env_file.read_text()


def test_points_at_the_probe_as_the_confirmation_step(ctx: Context, out: Recorder) -> None:
    runMintToken(ctx, minter=_returns(VALID_TOKEN))

    assert "meta-ads-connect probe" in out.text


def test_an_abandoned_flow_saves_nothing_and_says_so(
    ctx: Context, paths: Paths, err: Recorder
) -> None:
    assert runMintToken(ctx, minter=_returns(None)) == Exit.NO_TOKEN
    assert not paths.env_file.exists()
    assert "nothing has been saved" in err.text


def test_an_abandoned_flow_leaves_an_existing_token_alone(
    ctx: Context, paths: Paths
) -> None:
    """A failed re-mint must not destroy a token that still works."""
    writeToken(paths, OLD_TOKEN)

    runMintToken(ctx, minter=_returns(None))

    assert readToken(paths) == OLD_TOKEN


def test_an_empty_string_is_treated_as_no_token(ctx: Context, paths: Paths) -> None:
    assert runMintToken(ctx, minter=_returns("")) == Exit.NO_TOKEN
    assert not paths.env_file.exists()


def test_a_missing_browser_extra_is_reported_with_how_to_install_it(
    ctx: Context, err: Recorder
) -> None:
    def minter(**_: object) -> str | None:
        raise MintingUnavailable(
            "Minting a token needs the browser automation extra.\nNext: pip install ..."
        )

    assert runMintToken(ctx, minter=minter) == Exit.USAGE
    assert "Next:" in err.text


def test_the_owner_is_warned_before_the_browser_opens(ctx: Context, out: Recorder) -> None:
    """The Meta login is the one unavoidably human moment, and being dropped
    into a browser with no warning is how people abandon setup."""
    announcements: list[str] = []

    def minter(*, announce: Callable[[str], None], headless: bool = False, business_id: str | None = None) -> str | None:
        announce("A browser window is about to open.")
        announcements.append("announced")
        return VALID_TOKEN

    runMintToken(ctx, minter=minter)

    assert announcements == ["announced"]
    assert "browser window is about to open" in out.text


def test_passes_the_business_id_through_when_one_is_known(ctx: Context) -> None:
    seen: dict[str, object] = {}

    def minter(*, announce: Callable[[str], None], headless: bool = False, business_id: str | None = None) -> str | None:
        seen["business_id"] = business_id
        seen["headless"] = headless
        return VALID_TOKEN

    runMintToken(ctx, minter=minter, business_id="9900000000", headless=True)

    assert seen == {"business_id": "9900000000", "headless": True}
