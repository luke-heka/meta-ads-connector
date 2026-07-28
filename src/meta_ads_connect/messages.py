"""Walkthroughs for the things only the owner can do.

A Business Manager is the prerequisite the kit cannot create on the owner's
behalf — it needs their business details, and Meta has no endpoint that would
create one from a token that, by definition, does not exist yet. It is reached
from two directions: the browser flow hits it before any token exists, and
``repair-assets`` hits it afterwards. The walkthrough is written once here so
an owner meets the same instructions whichever way they arrived, and only the
closing step differs, because the command to come back to is not the same one.
"""

from __future__ import annotations

_NO_BUSINESS_MANAGER = """You do not have a Business Manager yet, and one is needed before an access token
can reach any ad account.

Creating it takes two minutes and is free:

  1. Go to https://business.facebook.com/overview and sign in.
  2. Click "Create account". Use your business name, your name, and your email.
  3. Once it exists, add your ad account to it under Settings → Accounts → Ad accounts.

Next: come back and run `meta-ads-connect {next_command}`."""


def noBusinessManager(*, next_command: str) -> str:
    """The walkthrough, closing on whichever command the owner should re-run."""
    return _NO_BUSINESS_MANAGER.format(next_command=next_command)
