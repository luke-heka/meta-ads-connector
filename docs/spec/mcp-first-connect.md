# Spec — MCP-first connect: one paste-in prompt, then `/meta-ads-connect`

Supersedes the MCP-registration sections of
[`meta-ads-connect.md`](meta-ads-connect.md), which specced the MCP as step four of a
five-step CLI setup. Everything else in that spec still stands.

Ads CLI token acquisition is tracked separately. Nothing here depends on it resolving.

## Problem Statement

A Skool member wants to manage their Meta ads by talking to Claude. Two separate things
stop them, and neither is their fault.

**They cannot get the kit.** The only documented way in is a README that asks them to open
a terminal, clone a repo, `mkdir -p ~/.claude/skills`, `cp -r` a directory, and run
`pip install .` — four commands, in a shell, before Claude is involved at all. The audience
for this kit is business owners. A meaningful share of them will not complete step one, and
the ones who do will get a different result depending on whether their `pip` is
externally-managed, whether they have a Python at all, and whether `~/.claude/skills`
already exists. The distribution mechanism is the product's actual first failure point, and
right now there isn't one.

**Even once they have it, the working path is unreachable.** The kit's first action in any
Meta ads conversation is `probe`, and `probe` asks "is Meta's Ads CLI installed?" before it
asks anything else. If the answer is no it returns `NOT_INSTALLED` and tells the user to run
`install` then `mint-token` — without ever looking at whether the MCP server is registered
and working. So a user whose MCP connection is live and healthy is told they are not set up.

That ordering is upside down, because of the two transports only one of them currently
works:

- The **CLI path** needs a minted system user token. Token acquisition is unresolved and
  turns out to be a much larger problem than it looked — device checks, approval gates and
  Business Settings automation that fails silently.
- The **MCP path** needs no token at all. It authenticates through Claude Code's own OAuth
  flow the first time it is used. No system user, no Business Settings, no minting, none of
  the gates blocking CLI token acquisition.

The net effect is that the path that works is gated behind three steps of the path that
doesn't. The user experiences this as: the kit tells me to do something that fails, and
never offers me the thing that would have worked.

There is a third problem sitting underneath both. `SKILL.md` Rule 2 asserts the MCP is for
exactly two things — custom audiences and Meta's internal analysis tools — with the CLI
doing everything else. **That claim was written when the MCP published 29 tools. It now
publishes roughly 93, with no version bump.** Nobody has checked what those tools cover. If
they include campaign, ad set, ad and creative management, then MCP-only is not a degraded
fallback, it is close to the whole product — and the routing rule the entire skill rests on
is telling Claude the opposite.

## Solution

Two artifacts, one interface.

**1. A setup prompt.** A block of plain text published in the Skool community. The member
copies it and pastes it into Claude. Claude clones the public repo, installs the skill into
`~/.claude/skills/`, tells them what happened and tells them to start a new session. That is
the whole job of the prompt — it is an installer for the skill, nothing more. It touches
Meta not at all.

**2. The skill.** In their next session the member types `/meta-ads-connect` (or just says
"connect my Meta ads"). The skill registers Meta's official Ads MCP server, the member logs
in to Meta in their browser once and approves the full permission set, and they are
connected. No token is minted. No Business Settings. No Python required. From that point on
they talk about their ads and the skill drives the MCP's full tool surface.

The CLI path is not deleted — it is demoted. It becomes an optional enhancement that can be
layered on afterwards for anyone who wants it, and it is held to one hard constraint: **it
may not gate, block, or degrade the MCP path.** A machine with no Python, no Ads CLI and no
token must still reach a fully working connection and must be told, accurately, that it is
connected.

Stated as the member experiences it: *copy one prompt, restart Claude, run one command, log
in to Meta. Done.*

## User Stories

### Getting the kit — the setup prompt

1. As a Skool member, I want to copy one block of text and paste it into Claude, so that installing the kit requires nothing I have to understand.
2. As a Skool member, I want the prompt to work when pasted into a fresh Claude session with no prior context, so that it does not depend on anything I happened to say beforehand.
3. As a Skool member, I want the prompt to tell Claude exactly which repo to clone, so that Claude cannot improvise a package name that does not exist.
4. As a Skool member, I want the clone to land in a fixed, predictable location, so that I can find it later and so that re-running the prompt updates rather than duplicates.
5. As a Skool member, I want the skill copied into the place Claude actually looks for skills, so that it is available without me knowing what a skill directory is.
6. As a Skool member, I want to be told plainly at the end that I must start a new Claude session before the skill exists, so that I do not immediately try to use it and conclude it is broken.
7. As a Skool member, I want to be told the exact thing to type in that next session, so that there is no gap between install finishing and me being able to use it.
8. As a Skool member who already has the kit, I want re-pasting the prompt to update it in place, so that "how do I get the latest version" has the same answer as "how do I install it".
9. As a Skool member whose machine has no `git`, I want to be told that specifically and given the one thing to install, so that I am not left with a generic failure.
10. As a Skool member, I want the prompt to succeed on a machine where `pip install` is impossible — no Python, or an externally-managed environment — so that the most common blocker on a non-developer machine is not a blocker at all.
11. As a Skool member using Claude Desktop rather than Claude Code, I want the prompt to recognise that and route me to the Desktop custom-connector path instead, so that I am not silently installing a skill into a directory nothing reads.
12. As a Skool member, I want the prompt to make no claim about connecting to Meta, so that I understand installing and connecting are two separate moments.
13. As the maintainer, I want the prompt to live in the repo as a versioned file, so that the text in the Skool post and the text in the repo cannot drift apart.
14. As the maintainer, I want the prompt short enough to read before pasting, so that a cautious member can satisfy themselves it is not doing anything alarming.

### Connecting — the first run of the skill

15. As a business owner, I want to type `/meta-ads-connect` and have it connect me, so that there is exactly one thing to remember.
16. As a business owner, I want the same result from saying "connect my Meta ads" in plain English, so that the slash command is a shortcut and not a requirement.
17. As a business owner, I want to be told up front that this takes about a minute and that I will log in to Meta once, so that I know what is about to happen.
18. As a business owner, I want the MCP server registered without me creating anything at Meta, so that the common case asks nothing of me beyond logging in.
19. As a business owner, I want the browser consent step announced before it opens, so that a browser window appearing is expected rather than alarming.
20. As a business owner, I want no access token minted anywhere in this flow, so that there is no long-lived credential with spend authority sitting on my disk.
21. As a business owner, I want a clear success message naming the ad accounts now reachable, so that I know it worked and against what.
22. As a business owner, I want to be able to run the connect step twice without harm, so that being unsure whether it finished is not a problem.
23. As a business owner, I want connection to work on a machine with no Python at all, so that a language runtime is not a prerequisite for talking about my ads.
24. As a business owner, I want connection to work with Meta's Ads CLI absent, so that the unresolved token problem never reaches me.

### Scopes and consent

25. As a business owner, I want the connector to request the full set of permissions the MCP supports, so that I do not discover a missing capability three weeks later mid-task.
26. As a business owner, I want to be told, before the consent screen appears, what I am about to approve and why, so that I am consenting rather than clicking through.
27. As a business owner, I want to be told explicitly not to deselect ad accounts or pages on the consent screen, so that I do not accidentally narrow my own grant.
28. As a business owner, I want the skill to verify after consent that the grant is actually complete, so that a narrowed approval is caught at connect time rather than at use time.
29. As a business owner whose grant came back narrower than needed, I want to be told exactly what is missing and offered a one-step re-consent, so that fixing it does not mean starting over.
30. As a business owner, I want to be told where to revoke this access at Meta's end, so that I can undo it entirely without asking anyone.
31. As Claude, I want the required capability set written down, so that "is this connection complete" is a check and not a judgement call.

### Doing the work — full MCP capability

32. As a business owner, I want to create a campaign by describing it, so that I do not open Ads Manager.
33. As a business owner, I want to create ad sets with targeting, budget and schedule conversationally, so that setup is one conversation rather than six screens.
34. As a business owner, I want to create ads and creatives, so that the whole build happens in one place.
35. As a business owner, I want to pause, resume and adjust budgets on anything already running, so that day-to-day management does not need a browser.
36. As a business owner, I want performance reporting with the fields I care about, so that I can judge what is working.
37. As a business owner, I want custom audiences and lookalikes, so that targeting is not a gap I work around elsewhere.
38. As a business owner, I want Meta's own opportunity score and industry benchmarks, so that I get signals that exist nowhere else.
39. As a business owner, I want anything the MCP can do to be something the skill can do, so that the kit's ceiling is the connector's ceiling and not an arbitrary subset.
40. As a business owner, I want to be told plainly when something I asked for is genuinely not available through this connection, so that I get a straight answer instead of a silent workaround.
41. As Claude, I want an accurate written statement of what the MCP covers, so that I stop routing work to a CLI that may not be installed.
42. As Claude, I want to discover the live tool list at run time rather than trusting a hardcoded one, so that Meta growing the surface without a version bump does not break me.
43. As Claude, I want everything created paused unless told otherwise, so that a misunderstanding cannot start spending money.
44. As Claude, I want to confirm before anything that changes spend or sets something live, so that safety lives in behaviour rather than in a crippled grant.
45. As Claude, I want deletions to require an unmistakable instruction, so that a loose phrase cannot destroy work.

### Standing alone — independence from the CLI path

46. As a business owner with only the MCP connected, I want the skill's connection check to report me as connected, so that I am never told to set up something I have already set up.
47. As a business owner with only the MCP connected, I want the skill to never suggest `install` or `mint-token`, so that I am not sent down a path that is currently blocked.
48. As a business owner with only the MCP connected, I want every ads task routed to the MCP, so that the skill does not stall reaching for a binary that is not there.
49. As a business owner with both transports set up, I want both reported and used, so that adding the CLI later is additive rather than disruptive.
50. As a business owner with only the CLI set up, I want that to keep working exactly as it does today, so that this change costs existing users nothing.
51. As a business owner with neither, I want to be pointed at the MCP path first, so that the default route is the one that works.
52. As Claude, I want one connection check that reports each transport separately, so that "connected" is never an all-or-nothing verdict that hides a working half.
53. As Claude, I want a distinct state for "MCP registered but not yet consented", so that I prompt for the login rather than declaring failure.
54. As Claude, I want a distinct state for "consented but the grant is incomplete", so that I fix the grant rather than reinstalling anything.
55. As a maintainer, I want a test that fails if a CLI-absent machine is ever again reported as not set up, so that this regression cannot come back quietly.

### When it goes wrong

56. As a business owner hitting the Claude Code `redirect_uri` bug, I want to be walked through creating my own bare Meta app, so that a client-side bug is not a dead end.
57. As a business owner in that situation, I want the walkthrough available without the Python package installed, so that the fallback does not depend on the thing I may not have.
58. As a business owner in that situation, I want to be told it is a bug in Claude Code and not something I did, so that I do not go looking for a problem with my Meta account.
59. As a business owner in that situation, I want to be told the app stays in development mode and needs no App Review and no business verification, so that I do not abandon it expecting a weeks-long process.
60. As a business owner whose `claude` command is not on PATH, I want to be told that specifically and given the Desktop connector route, so that the failure names its own fix.
61. As a business owner, I want every failure message to name the next action, so that a diagnosis I cannot act on is never the end of the conversation.
62. As a business owner, I want a "check my Meta setup" that reports each part separately, so that I can find out what is wrong without describing symptoms.

### Trust

63. As a business owner, I want to know exactly what the setup prompt did to my machine, so that I can undo it.
64. As a business owner, I want undoing the whole thing to be two commands, so that leaving is as easy as arriving.
65. As a business owner, I want nothing written to my shell profile and nothing in my OS keychain, so that the kit leaves no residue.
66. As a maintainer, I want the setup prompt and the skill's routing table covered by tests, so that the two documents the product rests on cannot be edited into incorrectness.

## Implementation Decisions

### Do the capability inventory first — it is blocking

Before any routing prose is rewritten, list what the MCP actually exposes. Register the
server, complete consent against a real Selr ad account, capture a live `tools/list`, and map
the result against what the kit promises in the README and `SKILL.md`.

Everything downstream depends on the answer:

- If the tool set covers campaign, ad set, ad and creative management, the MCP is the whole
  product and the CLI is an enhancement.
- If it does not, the gaps are named explicitly in `SKILL.md` as the only things that need
  the CLI, and the README's capability claims are corrected to match.

Record the captured tool list in the repo with the date it was captured, since the endpoint
is unversioned and this will drift. Do not write the routing rules from the 29-tool
assumption, and do not write them from the 93 number either — neither has been verified
against a live connection.

### The setup prompt is a versioned repo artifact

The prompt lives in the repo as its own file and is reproduced verbatim in the README. The
Skool post copies from the repo. This is the only way the published text and the shipped
behaviour stay in step.

What the prompt instructs Claude to do, in order:

1. Confirm this is Claude Code with a skills directory. If it is Claude Desktop, stop and
   give the custom-connector route instead — installing a skill there is a no-op.
2. Clone the public repo to a fixed location under the user's home directory. If it is
   already there, pull instead of cloning.
3. Copy the skill directory into the user's skills directory, replacing any previous copy.
4. Report what was installed and where.
5. State clearly that a **new session** is required, and give the exact invocation to use in
   it.

What the prompt must **not** do: mint anything, touch Meta, or make the Python package a
requirement for success. If installing the package fails for any reason — no Python, an
externally-managed environment, no network — that is reported as an optional extra that did
not install, and the install is still declared a success. The skill works without it.

Re-running the prompt is the update path, so every step is idempotent.

### The MCP path has no hard dependency on the Python package

This is the central structural decision and the one that makes the two paths genuinely
independent.

Registering the MCP server is a single `claude mcp add` invocation. It needs no token, no
Graph call, no interpreter and no venv. So the skill must be able to connect a user with
nothing installed but the skill itself.

Concretely:

- `SKILL.md` documents the bare registration command as a first-class path, not a curiosity,
  and is written so Claude reaches for it when `meta-ads-connect` is not on PATH.
- The package's `register-mcp` remains the preferred route when the package is present,
  because it detects the already-registered case and owns the `redirect_uri` fallback
  walkthrough. It is a convenience wrapper, not a gate.
- The `redirect_uri` fallback walkthrough must exist in a form reachable without the package
  — the user hitting that bug is precisely the user least likely to have a working install.
  It goes in the skill's own files, with the package's copy remaining as the printed
  version.

### The connection check becomes transport-aware

The current check is a single linear cascade rooted in "is the CLI installed", and every
early return reports the MCP as unknown. That is the defect.

The new model: two independent transports, each with its own state, collapsed to one verdict
only at the end.

- **Connected** means *at least one transport is live and usable*. An MCP-only machine is
  connected, and must be told so in the same words a fully-set-up machine is.
- **Nothing set up** requires *both* transports absent. It must be impossible to reach that
  verdict while the MCP is registered and working.
- The machine-readable output grows a per-transport breakdown alongside the existing
  top-level fields, so a caller can see which half is live without inferring it.
- The CLI half of the cascade — no token, token rejected, no ad accounts — only ever
  produces a blocking verdict when the CLI is the transport in use. On an MCP-only machine
  those states are not reachable, because there is no token to be missing.

Two states are new and both are MCP-side:

- **Registered but not consented** — the server is added, the OAuth flow has not been
  completed. The action is "log in", not "reinstall".
- **Consented but incomplete** — the flow completed but the resulting grant does not cover
  what the kit needs. The action is re-consent, not reinstall.

Exit codes are extended, never renumbered. Existing codes keep their numbers and their
meanings; `NOT_INSTALLED` keeps its number but its next-action changes to point at MCP
registration rather than at `install` and `mint-token`.

### Scopes: request everything, verify the grant

The member consents once, through Meta's OAuth screen, to whatever the official connector
requests. The kit's job is not to choose scopes — it is to make sure the member does not
accidentally grant less than the kit needs.

- Before opening consent, the skill states what is about to be approved in plain language
  and tells the member not to deselect ad accounts or pages on the screen.
- After consent, the connection is verified against a live read — the accounts the
  connection can actually see — rather than trusting the flow's own success signal.
- A grant that verifies as narrower than required produces the "consented but incomplete"
  state, names what is missing, and offers re-consent as a single step.
- If the connector's requested scope set is configurable at registration time, request the
  full set. The capability inventory establishes whether it is.

Safety remains behavioural — create paused, confirm before spend, deletions need an
unmistakable instruction — not permissional. A narrowed grant is a broken connection, not a
safety feature.

### `SKILL.md` is rewritten around the MCP

The routing rules invert. The specifics depend on the capability inventory, but the shape is
fixed:

- **Probe first** survives unchanged. It is the fix for the most-reported symptom and
  nothing here weakens it.
- **Rule 2 inverts.** The MCP is the primary transport and the default route for ads work.
  The CLI is named as an optional enhancement, with the inventory's gap list — if any — as
  the only work that requires it.
- **A new rule states the independence constraint outright**: the MCP path never requires
  the CLI, the package, a token, or a Python. Claude must not offer `install`, `mint-token`
  or `repair-assets` to a user whose MCP connection is live, because those steps solve
  problems that user does not have and are currently blocked besides.
- The routing table gains rows for the two new states and updates the next-action for
  "nothing set up".
- Rule 4 (tool names are unstable, discover them at run time) survives and gains weight,
  since the MCP is now the primary surface.
- Rules 5 (confirm before spend) and 6 (never print the token) survive unchanged.
- Every claim about what the CLI does that the inventory contradicts is corrected.

### The CLI path is demoted, not removed

Existing CLI users lose nothing. `install`, `mint-token`, `store-token`, `repair-assets` and
`exec` all keep working exactly as they do. What changes is that none of them sits on the
critical path to a working connection, and none of them can produce a verdict that
contradicts a healthy MCP connection.

The README is restructured to lead with the paste-in prompt and the MCP path, with the CLI
presented as an optional extra for people who want it.

### Idempotence

Unchanged as a principle and extended to the new surface. Re-running the setup prompt
updates. Re-running connect on a connected machine reports connected and stops. Re-running
registration when the server is already registered is a no-op with a clear message. None of
these are error cases.

## Testing Decisions

### What a good test looks like here

Unchanged from the existing suite, and the reason to reuse it: tests drive the package's
subcommands and assert on observable results — exit code, stdout, and the state of the
filesystem afterwards. No test asserts which internal function ran or in what order. A
refactor that keeps the subcommands behaving identically must not break a single test.

Two boundaries stay faked, and only these two: outbound HTTP to Meta, and subprocess
execution. Everything new here is reachable through the subprocess fake, because MCP
registration, MCP listing and consent status are all mediated by the `claude` command.

### Seams

**No new seams.** Both already exist.

**Seam 1 — the subcommand seam.** `run(argv, ctx=…)` in-process with a faked runner and
faked Graph client. This is the highest seam in the codebase and it already covers every
subcommand. All new behaviour is asserted here.

**Seam 2 — the doc-assertion seam.** `tests/test_skill_routing.py` asserts the load-bearing
prose in `SKILL.md`. The setup prompt joins it as a second asserted document. This seam
exists precisely because prose has no other guard, and the setup prompt is now the most
externally-visible prose in the product.

### Coverage

**Transport independence — the highest-value target, because it is the regression this spec
exists to kill.**

- MCP registered and consented, CLI entirely absent, no token, no venv → reports connected,
  exit 0, and the output mentions neither `install` nor `mint-token`.
- Same machine, but the MCP is registered and not yet consented → the "log in" state, not a
  failure and not a reinstall instruction.
- Same machine, consent completed but the grant verifies as incomplete → the re-consent
  state.
- Neither transport present → nothing-set-up, with a next-action pointing at MCP
  registration.
- CLI live and MCP missing → unchanged from today's behaviour.
- Both live → connected, with both transports reported.
- CLI installed with a rejected token but the MCP live and consented → connected. The
  broken half must not veto the working half.
- A negative assertion, permanently: no code path can report nothing-set-up while the MCP is
  registered and consented.

**Registration.**

- Clean registration; already registered (no duplicate, clear message); the `redirect_uri`
  failure producing the fallback walkthrough rather than a crash; registration with a
  supplied App ID; the `claude` command absent, producing the Desktop route.

**Machine-readable output.**

- The per-transport breakdown is present and correct in each of the states above, and the
  existing top-level fields keep their current shape.

**The setup prompt.**

- The file exists where the README and the Skool post point.
- It names the correct repo URL and no other.
- It names the skills directory the harness actually reads.
- It names the exact invocation the member types next session, and that invocation matches
  the skill's declared name.
- It states that a new session is required.
- It contains no token minting, no Business Manager step, and no claim to have connected
  anything to Meta.
- The Python package install is presented as optional — asserted, because this is the
  decision most likely to erode.
- The README's reproduced copy matches the source file.

**Routing.**

- All existing `SKILL.md` assertions are updated rather than deleted, so the guard stays
  intact through the rewrite.
- Every state the connection check can return has a row in the routing table, with the exit
  code the code actually returns. This test already exists and must be extended to the new
  states rather than replaced.
- `SKILL.md` states the independence constraint, asserted directly.
- `SKILL.md` does not tell Claude to route ads work to the CLI by default. Asserted as a
  negative, because the current file does exactly that and the inversion is the whole point.

**Regression guards on existing behaviour.**

- The full existing suite passes unchanged except where a spec'd behaviour changed. Any test
  that had to change is a deliberate decision, not collateral.

### Prior art

The existing suite is the prior art in full: pytest, grouped by subcommand, fakes rather
than mocks with call assertions, and `test_skill_routing.py` as the model for asserting on
shipped prose.

### Manual verification

Automated tests cannot prove a connection works, only that the code paths behave. Required
before release, and it doubles as the capability inventory:

1. Paste the setup prompt into a clean Claude Code session on a machine with no prior setup.
   Confirm the skill is present in the next session and the invocation works.
2. Run connect. Confirm consent succeeds and record exactly what the consent screen lists.
3. Capture a live `tools/list` and commit it with its capture date.
4. Exercise the promised surface end to end through the MCP alone — enumerate accounts,
   create a paused campaign, an ad set and an ad, attach a creative, pull reporting, then
   clean up. Note anything that cannot be done.
5. Confirm whether the Claude Code `redirect_uri` bug still bites, and if it does, walk the
   fallback as a user would.
6. Repeat step 1 on a machine with no Python available at all.

## Out of Scope

- **Resolving Ads CLI token acquisition.** That is tracked separately and is deliberately independent. This
  spec must not wait on it and must not assume it.
- **Removing the CLI path.** Demoted, not deleted. Existing users keep everything.
- **Raw Graph API access, third-party MCP servers, and Ads Manager bulk CSV import.** All
  remain out of scope for the same reasons as the original spec.
- **Windows native support.** WSL remains the stated requirement. Note that the MCP path may
  well work natively on Windows since it needs no wheel — worth confirming during manual
  verification, but not a deliverable here.
- **Automating the bring-your-own-app fallback.** It needs a logged-in Meta session and fails
  silently under automation. It stays a walkthrough.
- **The Skool post itself** — the announcement copy, where it is pinned, how it is
  maintained. This spec delivers the prompt text; publishing it is separate.
- **Reworking the wider pack estate** — the pipeboard deprecation, kit-index entries, the
  Meta-ads knowledge layer. Still parked.

## Further Notes

The audience is business owners, not developers. Every message the prompt and the skill emit
is written for someone who does not know what an MCP server is and should never have to find
out. That standard applies hardest to the setup prompt, which is the first thing they see and
the only thing they see before deciding whether this kit is worth the effort.

Two failure modes are worth naming for whoever implements this, because both have already
happened once in this project:

**Treating an absent lookup as proof of absence.** The research reached three false
conclusions this way — "no official CLI exists", "29 tools", "DCR is closed" — and each was
corrected only by probing positively. The capability inventory is exactly the kind of task
where this recurs. Probe, do not infer.

**Letting the CLI's assumptions leak back in.** The current probe cascade was not written to
block the MCP path; it blocks it as a side effect of asking its questions in the order the
CLI needed. That is how this class of coupling arrives — not by decision, but by ordering.
The negative assertions in the coverage list exist specifically to catch it happening again.
