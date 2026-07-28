"""``repair-assets`` detects and fixes rather than asking. The owner is told
what was repaired; they are never handed a blocking question they have no basis
to answer. The two things only they can do are explained, not merely reported.
"""

from __future__ import annotations

from meta_ads_connect.commands.repair_assets import runRepairAssets
from meta_ads_connect.config import Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.graph import GraphAuthError, GraphError
from meta_ads_connect.tokens import writeToken

from .conftest import AD_ACCOUNTS_PAYLOAD, VALID_TOKEN, FakeGraphClient, Recorder

SYSTEM_USER = {"id": "6100000000", "name": "claude-meta-ads"}
ONE_BUSINESS = {"data": [{"id": "9900000000", "name": "Selr AI Pty Ltd"}]}
NO_BUSINESSES: dict[str, list[dict[str, str]]] = {"data": []}
OWNED_ACCOUNTS = {"data": [{"id": "act_111", "name": "Selr AI"}]}


def test_does_nothing_when_the_accounts_are_already_reachable(
    ctx: Context, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)
    graph.onGet("/me/businesses", ONE_BUSINESS)
    graph.onGet("/me", SYSTEM_USER)
    graph.onGet("owned_ad_accounts", AD_ACCOUNTS_PAYLOAD)
    graph.onGet("client_ad_accounts", {"data": []})

    assert runRepairAssets(ctx) == Exit.OK
    assert "Nothing to repair" in out.text
    assert not [request for request in graph.requests if request[0] == "POST"]


def test_assigns_only_the_accounts_that_are_not_reachable_yet(
    ctx: Context, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    """One reachable account is not the same as all of them reachable.

    An owner with several routinely has one assigned and the rest invisible.
    Stopping at the first is how they end up silently locked to it.
    """
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": [{"id": "act_111", "name": "Selr AI"}]})
    graph.onGet("/me/businesses", ONE_BUSINESS)
    graph.onGet("/me", SYSTEM_USER)
    graph.onGet(
        "owned_ad_accounts",
        {"data": [{"id": "act_111", "name": "Selr AI"}, {"id": "act_222", "name": "Second"}]},
    )
    graph.onGet("client_ad_accounts", {"data": []})
    graph.onPost("assigned_users", {"success": True})

    assert runRepairAssets(ctx) == Exit.OK

    posts = [request for request in graph.requests if request[0] == "POST"]
    assert [post[1] for post in posts] == ["/act_222/assigned_users"]
    assert "Second (act_222)" in out.text


def test_leaves_a_working_setup_alone_when_the_businesses_cannot_be_listed(
    ctx: Context, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    """A token minted before `business_management` was requested lands here.

    Its setup works. Reporting a repair failure would send the owner to
    re-mint something that is not broken.
    """
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", AD_ACCOUNTS_PAYLOAD)
    graph.onGet("/me/businesses", GraphError("(#200) Requires business_management", code=200))

    assert runRepairAssets(ctx) == Exit.OK
    assert "Nothing to repair" in out.text


def test_assigns_an_ad_account_the_token_cannot_see_yet(
    ctx: Context, graph: FakeGraphClient, paths: Paths, out: Recorder
) -> None:
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})
    graph.onGet("/me/businesses", ONE_BUSINESS)
    graph.onGet("/me", SYSTEM_USER)
    graph.onGet("owned_ad_accounts", OWNED_ACCOUNTS)
    graph.onGet("client_ad_accounts", {"data": []})
    graph.onPost("assigned_users", {"success": True})

    assert runRepairAssets(ctx) == Exit.OK

    posts = [request for request in graph.requests if request[0] == "POST"]
    assert posts[0][1] == "/act_111/assigned_users"
    assert posts[0][2]["user"] == SYSTEM_USER["id"]
    assert "Assigned" in out.text


def test_grants_full_management_rather_than_a_lesser_role(
    ctx: Context, graph: FakeGraphClient, paths: Paths
) -> None:
    """A lesser task makes the write commands fail later, in a way that is far
    harder to diagnose than this step failing now."""
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})
    graph.onGet("/me/businesses", ONE_BUSINESS)
    graph.onGet("/me", SYSTEM_USER)
    graph.onGet("owned_ad_accounts", OWNED_ACCOUNTS)
    graph.onGet("client_ad_accounts", {"data": []})
    graph.onPost("assigned_users", {"success": True})

    runRepairAssets(ctx)

    posts = [request for request in graph.requests if request[0] == "POST"]
    assert "MANAGE" in posts[0][2]["tasks"]


def test_walks_the_owner_through_creating_a_business_manager(
    ctx: Context, graph: FakeGraphClient, paths: Paths, err: Recorder
) -> None:
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})
    graph.onGet("/me/businesses", NO_BUSINESSES)

    assert runRepairAssets(ctx) == Exit.NEEDS_BUSINESS_MANAGER
    assert "business.facebook.com" in err.text
    assert "Next:" in err.text


def test_explains_a_business_manager_with_no_ad_account_in_it(
    ctx: Context, graph: FakeGraphClient, paths: Paths, err: Recorder
) -> None:
    """Only the owner can create one — it carries their billing details."""
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})
    graph.onGet("/me/businesses", ONE_BUSINESS)
    graph.onGet("/me", SYSTEM_USER)
    graph.onGet("owned_ad_accounts", {"data": []})
    graph.onGet("client_ad_accounts", {"data": []})

    assert runRepairAssets(ctx) == Exit.NEEDS_AD_ACCOUNT
    assert "Selr AI Pty Ltd" in err.text
    assert "payment method" in err.text


def test_a_failed_assignment_becomes_a_manual_walkthrough(
    ctx: Context, graph: FakeGraphClient, paths: Paths, err: Recorder
) -> None:
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})
    graph.onGet("/me/businesses", ONE_BUSINESS)
    graph.onGet("/me", SYSTEM_USER)
    graph.onGet("owned_ad_accounts", OWNED_ACCOUNTS)
    graph.onGet("client_ad_accounts", {"data": []})
    graph.onPost("assigned_users", GraphError("(#200) Requires business_management permission", code=200))

    assert runRepairAssets(ctx) == Exit.REPAIR_FAILED
    assert "system-users" in err.text
    assert "Assign assets" in err.text


def test_reports_a_rejected_token_rather_than_attempting_a_repair(
    ctx: Context, graph: FakeGraphClient, paths: Paths, err: Recorder
) -> None:
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphAuthError("Session invalidated", code=190))

    assert runRepairAssets(ctx) == Exit.TOKEN_REJECTED
    assert "mint-token" in err.text


def test_reports_that_there_is_nothing_to_repair_without_a_token(
    ctx: Context, err: Recorder
) -> None:
    assert runRepairAssets(ctx) == Exit.NO_TOKEN
    assert "mint-token" in err.text


def test_keeps_going_when_one_business_cannot_be_read(
    ctx: Context, graph: FakeGraphClient, paths: Paths
) -> None:
    """Another business may still hold the ad account."""
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})
    graph.onGet(
        "/me/businesses",
        {"data": [{"id": "111", "name": "Locked"}, {"id": "222", "name": "Selr AI"}]},
    )
    graph.onGet("/me", SYSTEM_USER)
    graph.onGet("/111/owned_ad_accounts", GraphError("(#10) Not enough permission", code=10))
    graph.onGet("/111/client_ad_accounts", GraphError("(#10) Not enough permission", code=10))
    graph.onGet("/222/owned_ad_accounts", OWNED_ACCOUNTS)
    graph.onGet("/222/client_ad_accounts", {"data": []})
    graph.onPost("assigned_users", {"success": True})

    assert runRepairAssets(ctx) == Exit.OK


def test_never_prints_the_token(
    ctx: Context, graph: FakeGraphClient, paths: Paths, out: Recorder, err: Recorder
) -> None:
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", GraphAuthError(f"Bad token {VALID_TOKEN}", code=190))

    runRepairAssets(ctx)

    assert VALID_TOKEN not in out.text
    assert VALID_TOKEN not in err.text


def test_partial_success_says_what_worked_before_what_did_not(
    ctx: Context, graph: FakeGraphClient, paths: Paths, out: Recorder, err: Recorder
) -> None:
    """A bare failure after some accounts were assigned makes the owner think
    none of it took."""
    writeToken(paths, VALID_TOKEN)
    graph.onGet("/me/adaccounts", {"data": []})
    graph.onGet("/me/businesses", ONE_BUSINESS)
    graph.onGet("/me", SYSTEM_USER)
    graph.onGet(
        "owned_ad_accounts",
        {"data": [{"id": "act_111", "name": "Works"}, {"id": "act_222", "name": "Fails"}]},
    )
    graph.onGet("client_ad_accounts", {"data": []})

    attempts = {"count": 0}

    def failSecond(path: str, *, token: str, data: object = None) -> dict[str, bool]:
        attempts["count"] += 1
        if attempts["count"] == 2:
            raise GraphError("(#200) Requires business_management permission", code=200)
        return {"success": True}

    graph.post = failSecond  # type: ignore[method-assign]

    assert runRepairAssets(ctx) == Exit.REPAIR_FAILED
    assert "Assigned" in out.text
    assert "Works (act_111)" in out.text
    assert "1 of your ad accounts could not be assigned" in err.text
