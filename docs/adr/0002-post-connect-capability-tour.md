# 2. The connect flow ends with a capability tour

**Date:** 2026-07-30
**Status:** Accepted
**Context:** `skills/meta-ads-connect/SKILL.md` ("Connecting", step 4),
[`docs/spec/mcp-first-connect.md`](../spec/mcp-first-connect.md)

## Context

The connect flow ended at the live read: Claude names the ad accounts back, the member
learns the connection works, and the conversation stops there. Story 21 is met — "a clear
success message naming the ad accounts now reachable" — and the member still has no idea
what they can now ask for. The whole capability surface the spec fought to reach (stories
32–41: campaigns, ad sets, creatives, budgets, audiences, reporting, Meta's internal
signals) is invisible at the one moment the member is looking straight at it.

Two things make the obvious fix — "list the tools" — wrong here:

- **The tool list is not stable enough to name.** Rule 4 exists because the published tool
  count went from 29 to roughly 93 with no version change. Any inventory written into this
  repo is wrong by next week, and a tour that reads out 93 tool names is not a tour.
- **The first thing offered sets the tone for spend authority.** The kit holds full write
  access deliberately (Rule 5); safety is behavioural. Opening a brand-new connection by
  offering to create or activate something makes the member's first minute the riskiest
  one.

## Decision

**Add a step 4 to the Connecting flow: name the capability areas in plain English, then
offer exactly one read-only first action, grounded in what the live read just returned.**

*Capability areas, never a tool inventory.* The tour describes groups — campaigns and ads,
budgets, audiences, creatives, reporting, benchmarks — and instructs Claude to check each
group against the live tool list before claiming it. This is Rule 4 applied to prose: the groups are stable
even while the tools underneath them churn, and the check is what stops the tour promising
something the live connection cannot do. The creatives group deliberately does not claim
local image and video upload, because on an MCP-only connection that is the CLI's one
known gap.

*Read-only first.* The offer is a performance snapshot, the campaigns currently running,
or an industry benchmark — never anything that creates, changes spend, or sets something
live. Rule 5 already forbids unconfirmed spend; this makes the opening move safe by
construction rather than by confirmation.

*Connect time only.* It fires at the end of a successful connect flow and nowhere else. A
`probe` returning `OK` still means "get on with what the user asked": a member who is
already connected arrived with a task, and a tour would be an interruption. This is the
same instinct as Rule 1's never-reconnect-what-is-connected, applied to the member's
attention rather than to their setup.

*Enforced in prose, pinned by tests.* No Python changes. The constraints live in the
wording, so `tests/test_skill_routing.py` holds them: the tour is inside Connecting and
after step 3, it demands plain English, its three read-only examples are pinned by name,
Rule 1 as a whole contains no tour instruction, the tour stays under a word ceiling, and
hedging vocabulary is forbidden. The step is written as a direct imperative — "not
optional", not "consider" — because soft wording in this file has been observed being
skipped in live use.

## Consequences

- The member's first minute ends in a result rather than a green tick, and the read-only
  opener means it cannot end in an accident.
- The tour's accuracy now depends on Claude actually running the live-tool-list check. A
  model that skips it can still over-promise; the wording makes the check mandatory but
  nothing outside the conversation can verify it happened.
- Pinning the three read-only examples by name means changing the offered actions is a
  test change, deliberately. Swapping one for a write-shaped action fails the suite.
- The word ceiling is roughly the current length plus one bullet. Growing the tour is
  meant to require justification — a tour that grows back into a 93-tool wall is the
  failure this replaced.
- `docs/spec/mcp-first-connect.md` is amended rather than rewritten: its user stories are
  numbered and cross-referenced, so the addition lands as story 67 in an amendment
  section instead of renumbering the 42 stories that follow the Connecting group.
