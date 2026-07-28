"""``mint-token`` — drive the browser and store what comes back.

This exists so the hop from browser to disk happens inside one process. If the
token had to travel through the skill's prose, it would land in the transcript,
which is precisely what the design is trying to avoid.

The minter is injected so the test suite can cover both sides of that boundary
without a browser: a token comes back and everything downstream happens, or
nothing comes back and that is handled cleanly.
"""

from __future__ import annotations

from ..context import Context
from ..exits import Exit
from ..minting import MintingUnavailable, TokenMinter, mintSystemUserToken
from ..tokens import describePermissions, writeToken


def runMintToken(
    ctx: Context,
    *,
    minter: TokenMinter | None = None,
    headless: bool = False,
    business_id: str | None = None,
) -> int:
    mint = minter if minter is not None else mintSystemUserToken

    try:
        token = mint(announce=ctx.say, headless=headless, business_id=business_id)
    except MintingUnavailable as exc:
        ctx.warn(str(exc))
        return int(Exit.USAGE)

    if not token:
        # The announcement already told the owner what to do by hand; the exit
        # code is what stops a caller from treating this as a success.
        ctx.warn("No access token was created, so nothing has been saved.")
        return int(Exit.NO_TOKEN)

    ctx.secret = token
    target = writeToken(ctx.paths, token)

    ctx.say(f"Your Meta access token has been saved to {target}.")
    ctx.say(
        f"{describePermissions(ctx.paths)} It was never displayed and never went "
        "through this conversation."
    )
    ctx.say("Next: run `meta-ads-connect probe` to confirm Meta accepts it.")
    return int(Exit.OK)
