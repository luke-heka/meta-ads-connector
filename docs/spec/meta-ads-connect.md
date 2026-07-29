# Spec — `meta-ads-connect`

Source of truth for the design: [`../research/findings-and-decisions.md`](../research/findings-and-decisions.md)
section 7. Evidence behind every claim: [`../research/raw-agent-findings.md`](../research/raw-agent-findings.md).

## Problem Statement

A business owner wants to manage their Meta ads by talking to Claude. Today that fails,
and the failure is not their fault.

Meta's official connectors shipped on 2026-04-29 — after Claude's training cutoff. Claude
does not know they exist, so it improvises. It reaches for `npm install -g @meta/ads-cli`,
a package that has never existed in any registry, because dozens of blog posts say to.
The real package is `meta-ads` on PyPI. When Claude does stumble onto something that
works, nothing records that fact, so the next time the owner mentions their ads Claude
starts the whole connection dance again — the single most-reported symptom.

Selr's own kits make it worse rather than better. Nine reference sites point at three
different connectors, one of which is a deprecated third-party SaaS proxy, and one
internal knowledge note flatly asserts the official MCP does not work at all.

The owner experiences this as: connecting is a coin flip, and staying connected is
another one.

## Solution

One skill, `meta-ads-connect`, distributed as a public repo the community clones.

The owner says "connect my Meta ads" once. The skill probes for an existing working
connection first and, if it finds one, says so and stops in seconds. Otherwise it
installs Meta's official Ads CLI on a Python it picks itself, drives a browser to mint a
system user token that never expires, copies that token programmatically without the
owner ever handling it, repairs their Business Manager and ad account assignment if
those are missing, and registers Meta's official Ads MCP server alongside.

After that the owner just talks about their ads. Full management — campaigns, ad sets,
ads, creatives with image and video upload from local files, budgets, audiences,
reporting. No read-only mode and no artificial scope limits; safety lives in the skill
confirming before anything that changes spend or sets an ad live, not in a crippled
token.

## User Stories

### Connecting for the first time

1. As a business owner, I want to say "connect my Meta ads" in plain English, so that I do not have to know what a CLI, an MCP server, or a system user token is.
2. As a business owner, I want the skill to tell me up front roughly how long this will take and what it will ask of me, so that I know whether to start now.
3. As a business owner, I want Claude to pick and install the right Python for me, so that a version mismatch is never my problem.
4. As a business owner, I want the official Ads CLI installed at a known-good version, so that an upstream release cannot break my setup overnight.
5. As a business owner, I want Claude to drive the browser for the token, so that I do not have to find my way through Business Settings.
6. As a business owner, I want my token copied and pasted programmatically, so that I never have a credential with spend authority sitting on my clipboard or in a chat log.
7. As a business owner, I want to be told plainly at the one moment I must log in myself, so that I am not left staring at a stalled browser.
8. As a business owner with no Business Manager, I want the skill to create one, so that a missing prerequisite does not end the session.
9. As a business owner whose ad account is not assigned to a system user, I want the skill to assign it, so that the token it just minted actually works.
10. As a business owner with several ad accounts, I want all of them reachable, so that I am not silently locked to whichever one happened to be first.
11. As a business owner, I want a clear success message naming the accounts now connected, so that I know it worked and against what.

### Not reconnecting

12. As a business owner who is already connected, I want Claude to notice within seconds and stop, so that asking about my ads never restarts a setup I already finished.
13. As a business owner, I want that check to be a live call to Meta rather than a local marker file, so that a token revoked at Meta's end is detected rather than assumed good.
14. As a business owner whose token has been revoked, I want the skill to tell me exactly that and offer to re-mint, so that I am not told a vague "something went wrong".
15. As a business owner, I want a partially-complete setup (CLI present, MCP missing) to be finished rather than restarted, so that the skill repairs instead of redoing.
16. As Claude, I want an unambiguous instruction that the probe is always the first action, so that I cannot be talked into skipping it.

### Using it day to day

17. As a business owner, I want to create a campaign, ad set, and ad by describing them, so that I do not touch Ads Manager.
18. As a business owner, I want to upload an image from my own machine and turn it into a live ad, so that my creative does not have to already exist inside Meta.
19. As a business owner, I want the same for a video file, so that video ads are not a separate manual process.
20. As a business owner, I want to change budgets and bid strategies conversationally, so that routine adjustments are quick.
21. As a business owner, I want to pause and resume campaigns, ad sets, and ads, so that I can react without opening a browser.
22. As a business owner, I want to pull performance reporting with the fields I care about, so that I can judge what is working.
23. As a business owner, I want to build and update custom audiences and lookalikes, so that targeting is not a gap I have to work around elsewhere.
24. As a business owner, I want Meta's own opportunity score and industry benchmarks, so that I can see how I compare without buying a third-party tool.
25. As a business owner, I want everything created paused by default, so that a misunderstanding cannot start spending money.
26. As a business owner, I want explicit confirmation before anything that changes spend or sets something live, so that I stay in control of the money.
27. As a business owner, I want deletions to require me to say so unmistakably, so that a loose instruction cannot destroy work.

### Routing correctly

28. As Claude, I want one written rule saying the CLI does everything, so that I stop deliberating over which transport to use.
29. As Claude, I want the MCP named as the path for audiences and Meta-internal benchmarks only, so that I do not reach for it where the CLI already works.
30. As Claude, I want the raw Graph API stated as out of scope, so that I do not silently invent a third integration.
31. As Claude, I want to build every CLI invocation from `meta --help` rather than from Meta's docs, so that known doc/binary drift does not produce a failing command.
32. As Claude, I want MCP tool names treated as unstable and discovered at run time, so that Meta silently growing the tool list does not break me.

### Diagnosing

33. As a business owner, I want a "check my Meta setup" command, so that I can find out what is wrong without describing symptoms.
34. As a business owner, I want that check to report each component separately, so that the failure is localised rather than "it is broken".
35. As a business owner, I want every failure to name the next action, so that a diagnosis is always actionable.
36. As a business owner on Python 3.14, I want to be told the CLI has no wheel for it and that the skill will use a different interpreter, so that a hard install failure becomes a handled case.
37. As a business owner on Windows, I want to be told plainly that WSL is required, so that I do not spend an hour on something with no wheel.
38. As a business owner, I want the doctor to redact my token in all output, so that running a diagnostic is never how it leaks.

### Registering the MCP

39. As a business owner, I want the no-App-ID registration path tried first, so that the common case needs nothing from me.
40. As a business owner hitting the known Claude Code redirect_uri bug, I want to be walked through creating a bare developer app, so that a client-side bug does not become a dead end.
41. As a business owner, I want that fallback walked through manually rather than automated, so that it does not fail silently against a logged-in Meta session.
42. As a business owner, I want to be told the fallback is a development-mode app needing no App Review and no business verification, so that I do not abandon it expecting weeks of process.
43. As a business owner already having the MCP registered, I want registration skipped, so that I do not end up with duplicates.

### Trusting it

44. As a business owner, I want my token stored in a file only I can read, so that other accounts on the machine cannot take it.
45. As a business owner, I want no edits to my shell profile and nothing in my OS keychain, so that the skill leaves no residue I did not ask for.
46. As a business owner, I want the same setup to work on macOS and Linux, so that the kit is not silently macOS-only.
47. As a business owner, I want to know how to revoke and where the token lives, so that I can undo this entirely.
48. As a business owner, I want the skill to never print my token, so that transcripts I share are safe.
49. As a maintainer, I want a written date to re-check the whole picture, so that the kit's accuracy has an owner and an expiry.

## Implementation Decisions

### Shape

One skill, `meta-ads-connect`, plus one Python package behind it. `SKILL.md` is thin
prose: routing rules, safety rules, and instructions to shell into the package. It holds
no logic worth testing and reimplements nothing the package does.

The package exposes a single console entry point with subcommands:

| Subcommand | Responsibility |
| --- | --- |
| `probe` | Live connection check. Always the first action. Exit code carries the verdict. |
| `doctor` | Full component-by-component diagnosis, human-readable, token redacted. |
| `install` | Resolve interpreter, install the pinned CLI into an isolated environment. |
| `store-token` | Write a minted token to disk with correct permissions. |
| `register-mcp` | Register the MCP with Claude Code; detect the already-registered case. |
| `repair-assets` | Detect and fix missing Business Manager / unassigned ad account. |

Every subcommand is idempotent and safe to re-run.

### Transports

- **Official Ads CLI is primary and does everything** — campaigns, ad sets, ads,
  creatives including local image and video upload, budgets, insights. Pinned to
  `meta-ads==1.1.0`.
- **Official Ads MCP server is registered alongside**, used only for the two things the
  CLI genuinely cannot do: custom audiences (the CLI has zero audience commands) and the
  seven Meta-internal analysis tools that have no Graph equivalent.
- **Raw Graph API is out of scope.** Third-party MCPs are out. Selr's own `pp-facebook`
  Go CLI is out.

The precedence rule is written into `SKILL.md` in the imperative, addressed to Claude:
CLI for everything; MCP for audiences and benchmarks only; never reconnect what is
already connected.

### Interpreter and install

The Ads CLI is mypyc-compiled and ships cp312/cp313 wheels with no sdist. Python 3.14
fails outright — this was hit twice during research, it is not hypothetical.

`install` resolves an interpreter itself rather than assuming the ambient one: prefer
3.13, accept 3.12, reject everything else with a message naming what it found. It
installs into an isolated environment owned by the skill so it cannot collide with the
owner's other Python work, and records the resolved interpreter path so later
invocations do not re-resolve. On Windows it reports that no wheel exists and WSL is
required, rather than attempting and failing.

### Auth

One system user token. Scopes: `ads_management`, `ads_read`, `pages_show_list`,
`leads_retrieval`. Fixed, not offered as a choice — a business owner has no basis on
which to choose, and a token missing write scope makes the whole kit pointless. Safety
is behavioural, not permissional.

System user tokens do not expire. Sixty-day long-lived user tokens are the trap and are
never used.

Minting is Playwright-driven, reusing the approach already proven in
the `marketing-agency-workshop` repo, module 3. The token is transferred from browser
to disk programmatically. It is never rendered to the transcript, never echoed, and
never asked of the owner by hand. The one unavoidably human moment is the Meta login
itself, which is announced clearly before the browser opens.

### Token storage

`~/.meta-ads/.env`, file mode 600, directory mode 700. Exported per invocation into the
CLI's environment, never persisted into a shell profile and never placed in an OS
keychain. This keeps the kit OS-agnostic and leaves nothing behind that an uninstall
would miss.

### Idempotence

`probe` is the contract. It makes a live authenticated call listing ad accounts. A
marker file is not acceptable evidence — a token revoked at Meta's end must present as
disconnected. The probe distinguishes, and the exit code encodes, four states:

- fully connected
- token present but rejected by Meta
- CLI installed but no token
- nothing installed

Partial states drive repair of the missing piece only. This probe is the actual fix for
the reconnect complaint, so it is the highest-value thing in the spec to get right.

### Account state repair

Detect and fix rather than ask. No Business Manager → create one. Ad account not
assigned to the system user → assign it. Both present → proceed. The owner is told what
was repaired, but is never presented with a blocking question they lack the context to
answer.

### MCP registration

Two-tier, in order:

1. Register with no App ID. Meta operates a `client_name`-allowlisted pseudo-DCR that
   hands back a first-party Meta app to any caller identifying as Claude, so this
   normally just works.
2. On the redirect_uri failure (an Anthropic Claude Code regression, not a Meta
   requirement), fall back to a bring-your-own developer app.

The fallback is **walked through manually, never automated** — it needs a logged-in Meta
session and the redirect-URL step is app-settings config that breaks silently under
automation. The walkthrough states that this is a development-mode app requiring no App
Review and no business verification, and takes under five minutes.

Already-registered is detected and skipped.

### Anti-rot

- Pin the package version **and** the interpreter. Pinning only one is insufficient.
- Build every CLI invocation from `meta --help`, never from Meta's documentation. Two
  drifts are already confirmed: `--instagram-actor-id` in the docs versus
  `--instagram-user-id` in the binary, and a documented `meta auth` subcommand the
  shipped binary does not have.
- Treat MCP tool names as unstable and avoid hardcoding them. The published tool count
  went from 29 to roughly 93 without any version bump, because the endpoint is
  unversioned and unpinnable.
- Where a Graph version must appear, pin it explicitly. An expired version silently
  defaults to the next oldest rather than erroring, which degrades quietly instead of
  failing loudly.
- Record a re-check date of September 2026 in the repo.

## Testing Decisions

### What a good test looks like here

Tests drive the package's subcommands and assert on their observable results — exit
code, stdout, and the state of the filesystem afterwards. They do not assert on which
internal function was called or in what order. A refactor that keeps the subcommands
behaving identically must not break a single test.

Two boundaries are faked, and only these two:

- **Outbound HTTP to Meta**, so tests can present a valid token, a revoked token, a
  rate-limited response, and a network failure deterministically and without credentials.
- **Subprocess execution**, so tests can simulate the Ads CLI being absent, present at
  the wrong version, present and healthy, and failing to install.

Playwright browser automation is not driven in the automated suite. Its contract is
narrowed to a single function — "return a token string" — and tests cover both sides of
that boundary: everything downstream of a returned token, and correct handling when the
flow yields nothing. The browser flow itself is covered by the live run-through below.

### Coverage

- **`probe`** — the highest-value target. All four states, plus rate-limited and network
  failure. Each must produce a distinct exit code and a message naming the next action.
- **`doctor`** — every component healthy; each component failing in isolation; several
  failing at once. Assert the token never appears in output under any of them,
  including error paths.
- **`install`** — 3.13 present; only 3.12 present; only 3.14 present; no suitable
  interpreter; already installed at the pinned version; installed at a different version.
- **`store-token`** — file and directory modes are exactly 600 and 700; existing file is
  replaced not appended; the token is absent from stdout.
- **`register-mcp`** — clean registration; already registered; the redirect_uri failure
  producing the manual-fallback instructions rather than a crash.
- **`repair-assets`** — no Business Manager; unassigned ad account; both already correct;
  repair itself failing.
- **Routing** — `SKILL.md` is asserted to contain the precedence rule and the
  probe-first instruction, so a careless edit that removes either fails the build. This
  is a cheap guard on the two sentences the whole design rests on.

### Prior art

None in this repo — it is greenfield. The suite establishes the convention: pytest,
tests grouped by subcommand, fakes rather than mocks-with-assertions-on-calls.

### Manual verification

Automated tests cannot prove the connection works, only that the code paths behave. One
full live run-through against a real Selr ad account is required before release, and is
the moment the outstanding spike resolves: does MCP consent actually succeed and what
does the consent screen list; capture a live `tools/list`; does the Claude Code
redirect_uri bug still bite in practice; and an end-to-end CLI run — enumerate accounts,
create a paused campaign, upload an image creative, verify in Ads Manager, clean up.

## Out of Scope

- **Raw Graph API access.** A real capability ceiling advantage, but nothing it adds is
  needed to launch or manage ads. Cut deliberately to keep the kit simple.
- **Third-party MCP servers** — pipeboard (SaaS proxy in the credential path),
  gomarble (read-only), and the rest.
- **Ads Manager bulk CSV import.** UI-only with no documented endpoint; would mean
  browser automation against a live session.
- **`is_ads_mcp_enabled`.** Investigated and dropped — it appears nowhere in Meta's docs
  and traces to a single SEO content-farm cluster, several of whose members sell a
  competing product.
- **Windows native support.** No wheel exists. WSL is reported as the requirement.
- **Reworking the wider pack estate** — the pipeboard deprecation across
  `marketing-agency-workshop` and `managed-agents-setup`, kit-index entries, the Meta-ads
  knowledge layer, and the dashboard. All parked.
- **The Skool announcement.** Separate piece of work.

Two small fixes sit outside this spec but block correct routing and should ship
alongside it: an internal knowledge note wrongly asserts the official MCP does not work,
and the `paid-ads` skill falsely claims direct ad-account access. Both actively misroute
Claude today.

## Further Notes

The audience is Skool community business owners, not developers. Every message the skill
emits is written for someone who does not know what an MCP server is and should not have
to find out.

The single hardest-won lesson from the research is worth restating for whoever implements
this: three separate false conclusions were reached and corrected during it — "no
official CLI exists" (wrong registry and wrong doc path), "29 tools" (stale secondary
sources), and "DCR is closed" (a generic `client_name` in the probe). In each case an
absent lookup was treated as proof of absence. When something appears not to exist during
implementation, probe positively before concluding it.
