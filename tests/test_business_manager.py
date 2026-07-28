"""The one place "no Business Manager" is genuinely reachable.

A system user lives inside a Business Manager, so a system user token cannot
exist before one does — which is why no token-driven command can detect the
case, and why ``repair-assets`` only ever meets it via a token that came from
somewhere else. The browser flow meets it for real, before any token exists,
and has to say so rather than dropping the owner into token instructions for a
Business Manager that is not there.

No browser is driven here. The decision — "is this page telling us there is no
Business Manager?" — is a pure function of what the page shows, and that is
what these cover.
"""

from __future__ import annotations

from typing import Any

import pytest

from meta_ads_connect.messages import noBusinessManager
from meta_ads_connect.minting import (
    MANUAL_FALLBACK,
    BusinessManagerMissing,
    driveTokenFlow,
    needsBusinessManager,
)

SETTINGS_URL = "https://business.facebook.com/settings/system-users?business_id=99"
OVERVIEW_URL = "https://business.facebook.com/overview"


class StubPage:
    """The two things the Business Manager check reads off a page."""

    def __init__(self, *, url: str, body: str = "") -> None:
        self.url = url
        self._body = body

    def inner_text(self, selector: str) -> str:
        assert selector == "body"
        return self._body


@pytest.mark.parametrize(
    ("url", "body"),
    [
        (OVERVIEW_URL, ""),
        ("https://business.facebook.com/creation", ""),
        ("https://business.facebook.com/", "Create a business account to get started"),
    ],
)
def test_recognises_the_no_business_manager_state(url: str, body: str) -> None:
    assert needsBusinessManager(url=url, page_text=body)


@pytest.mark.parametrize(
    ("url", "body"),
    [
        (SETTINGS_URL, "Add  Generate new token"),
        # The real Business Settings page has its own "Add" and "Create"
        # buttons. Reading those as an empty account would send an owner who
        # has a Business Manager off to create a second one.
        (SETTINGS_URL, "Create system user"),
    ],
)
def test_does_not_mistake_business_settings_for_an_empty_account(url: str, body: str) -> None:
    assert not needsBusinessManager(url=url, page_text=body)


def test_the_browser_flow_signals_a_missing_business_manager_rather_than_failing_quietly() -> None:
    """A moved selector and a missing prerequisite need different things said,
    so they cannot both present as "the flow returned nothing"."""
    said: list[str] = []

    with pytest.raises(BusinessManagerMissing):
        driveTokenFlow(StubPage(url=OVERVIEW_URL), announce=said.append)


def test_an_ordinary_browser_failure_still_returns_none_rather_than_raising() -> None:
    """Everything except the missing prerequisite drops into the manual path."""

    class Broken:
        url = SETTINGS_URL

        def inner_text(self, selector: str) -> str:
            return ""

        def get_by_role(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("selector has moved")

    assert driveTokenFlow(Broken(), announce=lambda _: None) is None


def test_the_walkthrough_names_the_command_to_come_back_to() -> None:
    """Arriving from minting and arriving from repair-assets are different
    places to be sent back to, and being sent to the wrong one is a loop."""
    assert "meta-ads-connect mint-token" in noBusinessManager(next_command="mint-token")
    assert "meta-ads-connect repair-assets" in noBusinessManager(next_command="repair-assets")


def test_the_walkthrough_says_where_to_create_one_and_that_it_is_free() -> None:
    message = noBusinessManager(next_command="mint-token")

    assert "business.facebook.com/overview" in message
    assert "free" in message


def test_the_manual_token_walkthrough_mentions_creating_a_business_manager_first() -> None:
    """The manual path is where an owner with no Business Manager ends up if
    the browser flow cannot tell. It has to name the prerequisite."""
    assert "Business Manager" in MANUAL_FALLBACK
    assert "business.facebook.com/overview" in MANUAL_FALLBACK
