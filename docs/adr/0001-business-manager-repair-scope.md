# 1. `business_management` scope, and who creates the Business Manager

**Date:** 2026-07-29
**Status:** Accepted, pending confirmation in the live run-through
**Context:** `repair-assets`, [`docs/spec/meta-ads-connect.md`](../spec/meta-ads-connect.md)

## Context

The spec fixes the token's scopes at four — `ads_management`, `ads_read`,
`pages_show_list`, `leads_retrieval` — and separately requires `repair-assets` to
"detect and fix rather than ask": no Business Manager → create one, ad account not
assigned to the system user → assign it, never a blocking question.

Implementing that surfaced a conflict between the two requirements. Every Graph call the
repair needs sits behind a scope the list omits:

| Call | Purpose | Requires |
| --- | --- | --- |
| `GET /me/businesses` | find the Business Manager | `business_management` |
| `GET /<business>/owned_ad_accounts` | find unassigned accounts | `business_management` |
| `POST /<account>/assigned_users` | do the assignment | `business_management` |

With the locked four, `repair-assets` returns HTTP 400 against real Meta on every path.
The fake Graph client in the test suite hides this, because a fake answers whatever it is
told to.

## Decision

**Add `business_management` to the minted scopes.** The list is now five.

The spec's stated reason for fixing the scopes is that "a business owner has no basis on
which to choose" and that "a token missing write scope makes the whole kit pointless".
Neither argues against this scope specifically — both argue against *asking the user*,
which we still do not do. The prior art the minting flow is ported from
(the `marketing-agency-workshop` repo, `03-system-user.spec.ts`) also ticks
`business_management`, so this is what has actually been exercised against real Business
Managers.

**Handle "no Business Manager" in the browser flow, not in `repair-assets`, and walk the
owner through it rather than creating it.** The spec asks for "no Business Manager →
create one". Where that is handled, and whether the kit can create it at all, are two
separate questions.

*Where.* A system user exists *inside* a Business Manager. A system user token therefore
cannot be minted until a Business Manager already exists. By the time `repair-assets`
runs — it reads the stored token — the case is unreachable by construction there. The
place it is genuinely reachable is the browser flow in `minting.py`, before any token
exists, so that is where it is detected: `needsBusinessManager` reads Meta's redirect to
its creation page, and `driveTokenFlow` raises `BusinessManagerMissing` rather than
returning the same "nothing came back" as a moved selector. The two need different things
said, and saying the wrong one sends the owner to generate a token inside a Business
Manager that does not exist.

*Whether.* Creating it is not something the kit can do. There is no Graph endpoint that
creates a Business Manager, and there could not usefully be one: the call would need a
token that, at that moment, cannot exist. It also takes the owner's legal business
details. So both paths print the same walkthrough — one written once in `messages.py`,
closing on whichever command the owner should re-run — and `repair-assets` keeps its
`NEEDS_BUSINESS_MANAGER` exit as the backstop for a token minted elsewhere.

This is a partial implementation of the spec's requirement and is recorded as such: the
prerequisite is detected and explained at the moment it blocks, but it is not created.

## Consequences

- The consent screen lists five permissions rather than four. This is the one place the
  owner sees the difference, and `business_management` is unsurprising next to the rest.
- `repair-assets` works against real Meta rather than only against the fakes.
- Creating a Business Manager remains manual, and story 8 is met by detecting and
  explaining rather than by creating. Confirm during the live run-through that an owner
  with no Business Manager does land on `/overview` or a page whose wording
  `needsBusinessManager` recognises — that detection is the only part of this not proven
  against real Meta.
- `repair-assets` keeping `NEEDS_BUSINESS_MANAGER` is deliberate rather than dead code: a
  token minted outside this kit can reach it.
- If the live run-through shows assignment succeeding without `business_management`,
  narrow the list back to four and delete this ADR's first decision.
