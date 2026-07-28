"""``repair-assets`` — detect and fix the account state a token needs to work.

A freshly minted system user token frequently sees nothing, because the ad
account was never assigned to the system user. That presents to the owner as
"it connected but it doesn't work", which is the least useful failure there is.

The rule here is detect and fix, not ask. The owner is told what was repaired;
they are never handed a blocking question they have no basis to answer. The two
things only they can do — creating a Business Manager, creating an ad account
with their billing details on it — are the exceptions, and both are explained
rather than merely reported.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..components import AdAccount, describeAccounts, parseAdAccounts
from ..context import Context
from ..exits import Exit
from ..graph import GraphAuthError, GraphError
from ..messages import noBusinessManager
from ..tokens import readToken

#: Assigning with MANAGE gives the system user the same authority the owner has
#: over the account. A lesser task would make the write commands fail later, in
#: a way that is much harder to diagnose than this step failing now.
#:
#: Meta wants this as a JSON array in a form field. Built rather than written by
#: hand, so a stray quote cannot turn into a 400 nobody can read.
ASSIGNMENT_TASKS = json.dumps(["MANAGE"])


@dataclass(frozen=True)
class Business:
    id: str
    name: str


def runRepairAssets(ctx: Context) -> int:
    token = readToken(ctx.paths)
    if token is None:
        ctx.warn("There is no saved Meta access token, so there is nothing to repair yet.")
        ctx.warn("Next: run `meta-ads-connect mint-token`.")
        return int(Exit.NO_TOKEN)
    ctx.secret = token

    try:
        reachable = parseAdAccounts(
            ctx.graph.get("/me/adaccounts", token=token, params={"fields": "id,name", "limit": "100"})
        )
    except GraphAuthError as exc:
        ctx.warn(f"Meta rejected the saved token, so nothing can be repaired with it: {exc.message}")
        ctx.warn("Next: run `meta-ads-connect mint-token` for a fresh one.")
        return int(Exit.TOKEN_REJECTED)
    except GraphError as exc:
        ctx.warn(f"Could not ask Meta which ad accounts are reachable: {exc.message}")
        ctx.warn("Next: run `meta-ads-connect probe` in a minute or two.")
        return int(Exit.REPAIR_FAILED)

    # One reachable account is not the same as all of them reachable. Owners
    # with several routinely have one assigned and the rest invisible, and
    # stopping at the first one is how they end up silently locked to it.
    businesses = _listBusinesses(ctx, token)
    if businesses is None:
        # The question could not be asked. If the owner already has working
        # accounts, that is not a failure — an older token without
        # `business_management` lands here and its setup is fine.
        if reachable:
            _sayNothingToRepair(ctx, reachable)
            return int(Exit.OK)
        return int(Exit.REPAIR_FAILED)
    if not businesses:
        if reachable:
            _sayNothingToRepair(ctx, reachable)
            return int(Exit.OK)
        ctx.warn(noBusinessManager(next_command="repair-assets"))
        return int(Exit.NEEDS_BUSINESS_MANAGER)

    owned = _ownedAdAccounts(ctx, token, businesses)
    if not owned:
        if reachable:
            _sayNothingToRepair(ctx, reachable)
            return int(Exit.OK)
        ctx.warn(_noAdAccountMessage(businesses))
        return int(Exit.NEEDS_AD_ACCOUNT)

    seen = {account.id for account in reachable}
    missing = [account for account in owned if account.id not in seen]
    if not missing:
        _sayNothingToRepair(ctx, reachable)
        return int(Exit.OK)

    system_user_id = _systemUserId(ctx, token)
    if system_user_id is None:
        ctx.warn("Could not work out which system user this token belongs to.")
        ctx.warn("Next: run `meta-ads-connect doctor` for a component-by-component check.")
        return int(Exit.REPAIR_FAILED)

    ctx.say(
        f"Found {_describe(missing)} that your access token cannot see yet. Assigning "
        f"{'them' if len(missing) != 1 else 'it'} now."
    )

    assigned: list[AdAccount] = []
    failures: list[tuple[AdAccount, str]] = []
    for account in missing:
        error = _assign(ctx, token, account=account, system_user_id=system_user_id)
        if error is None:
            assigned.append(account)
        else:
            failures.append((account, error))

    for account, reason in failures:
        ctx.warn(f"Could not assign {account.describe()}: {reason}")

    if not assigned:
        ctx.warn(_assignmentFailedMessage())
        return int(Exit.REPAIR_FAILED)

    ctx.say(f"Assigned {_describe(assigned)}.")
    if failures:
        # Some worked. Saying so and pointing at the rest beats a bare failure
        # that makes the owner think none of it took.
        ctx.warn(
            f"{len(failures)} of your ad accounts could not be assigned automatically."
        )
        ctx.warn(_assignmentFailedMessage())
        return int(Exit.REPAIR_FAILED)

    ctx.say("Next: run `meta-ads-connect probe` to confirm.")
    return int(Exit.OK)


# --- Graph reads -----------------------------------------------------------


def _listBusinesses(ctx: Context, token: str) -> list[Business] | None:
    """Businesses this token can see. None means the question could not be asked."""
    try:
        payload = ctx.graph.get("/me/businesses", token=token, params={"fields": "id,name", "limit": "50"})
    except GraphError as exc:
        ctx.warn(f"Could not ask Meta about your Business Manager: {exc.message}")
        ctx.warn("Next: run `meta-ads-connect doctor` for a component-by-component check.")
        return None
    return [
        Business(id=str(row["id"]), name=str(row.get("name") or ""))
        for row in _rows(payload)
        if row.get("id")
    ]


def _systemUserId(ctx: Context, token: str) -> str | None:
    try:
        payload = ctx.graph.get("/me", token=token, params={"fields": "id,name"})
    except GraphError:
        return None
    identifier = payload.get("id")
    return str(identifier) if identifier else None


def _ownedAdAccounts(ctx: Context, token: str, businesses: Sequence[Business]) -> list[AdAccount]:
    found: dict[str, AdAccount] = {}
    for business in businesses:
        for edge in ("owned_ad_accounts", "client_ad_accounts"):
            try:
                payload = ctx.graph.get(
                    f"/{business.id}/{edge}",
                    token=token,
                    params={"fields": "id,name", "limit": "100"},
                )
            except GraphError:
                # A business the token cannot read is not a failure worth
                # stopping for; another one may still hold the ad account.
                continue
            for account in parseAdAccounts(payload):
                found.setdefault(account.id, account)
    return list(found.values())


def _assign(ctx: Context, token: str, *, account: AdAccount, system_user_id: str) -> str | None:
    """Assign one ad account. Returns None on success, or a reason to report."""
    try:
        ctx.graph.post(
            f"/{account.id}/assigned_users",
            token=token,
            data={"user": system_user_id, "tasks": ASSIGNMENT_TASKS},
        )
    except GraphError as exc:
        return exc.message
    return None


def _rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        return []
    return [row for row in data if isinstance(row, Mapping)]


# --- Messages --------------------------------------------------------------


def _sayNothingToRepair(ctx: Context, reachable: Sequence[AdAccount]) -> None:
    ctx.say(f"Nothing to repair — {_describe(reachable)} already reachable.")


def _describe(accounts: Sequence[AdAccount]) -> str:
    plural = "ad accounts are" if len(accounts) != 1 else "ad account is"
    return f"{describeAccounts(accounts)} — {len(accounts)} {plural}"


def _noAdAccountMessage(businesses: Sequence[Business]) -> str:
    named = businesses[0].name or businesses[0].id
    return f"""Your Business Manager ("{named}") does not have an ad account in it yet.

An ad account has to be created by you, because it carries your billing details:

  1. Go to https://business.facebook.com/settings/ad-accounts
  2. Click "Add" → "Create a new ad account", and follow the prompts.
  3. Add a payment method when asked — Meta will not let ads run without one.

Next: come back and run `meta-ads-connect repair-assets` again."""


def _assignmentFailedMessage() -> str:
    return """Your ad account could not be assigned automatically. This usually means the
access token is not allowed to change who has access to the account.

You can do it by hand in under a minute:

  1. Go to https://business.facebook.com/settings/system-users
  2. Click your system user, then "Assign assets".
  3. Choose "Ad accounts", tick your ad account, and pick "Manage campaigns"
     (full control), then save.

Next: come back and run `meta-ads-connect probe` to confirm."""
