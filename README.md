# Meta Ads Connector

Connect Claude to Meta Ads in one shot, and give it full management of your ad accounts.

> **Status: built, pending a live run-through.** The skill and the package behind it are
> complete and tested. One full run against a real ad account is still required before
> release — see [Before release](#before-release).

---

## The problem

Getting Claude connected to Meta Ads is unreliable, and it isn't your fault:

- Meta's official connectors shipped on **29 April 2026** — after Claude's training data. Claude doesn't know they exist, so it improvises.
- Most guides on the web are **wrong**. They tell you to run `npm install -g @meta/ads-cli`. That package does not exist. The real one is `meta-ads` on **PyPI**.
- Once connected, Claude often tries to connect *again*, because nothing tells it the job is already done.

## Getting started — one prompt

Copy everything in the box below and paste it into Claude Code as one message.
Claude installs the kit for you; there is nothing else to run. Pasting it again
later is also how you update.

```text
Install the Meta Ads connector kit on this machine. Follow these steps exactly, in order, and do nothing beyond them.

1. Check that you are running as Claude Code with access to a terminal and a ~/.claude/skills folder. Claude Code in the terminal and Claude Code inside the desktop app both count — the desktop app has a terminal and skills too. Only stop if you truly have no terminal — for example this is claude.ai in a web browser — and in that case tell me to open Claude Code (terminal or desktop app) and paste this prompt there.
2. Check that git is available. If it is not, stop and tell me the one thing to install (git), with the easiest way to get it on my operating system.
3. Clone https://github.com/luke-heka/meta-ads-connector into ~/meta-ads-connector. If that folder already exists, run git pull inside it instead of cloning a second copy.
4. Create ~/.claude/skills if it does not exist, then copy ~/meta-ads-connector/skills/meta-ads-connect into ~/.claude/skills/, replacing any earlier copy.
5. Optional, and allowed to fail: install the helper package with pip install ~/meta-ads-connector. If this fails for any reason — no Python, a managed environment, anything at all — do not try to fix it. Note that the optional helper did not install, and carry on: the kit works without it.
6. Finish by telling me, in plain language: exactly what you installed and where; that I must start a NEW Claude session before the skill exists; and that in that new session I should type /meta-ads-connect, or just say "connect my Meta ads".

Do not connect to anything, do not open a browser, do not touch my Meta account, and do not create or store any token or credential. Installing and connecting are separate steps — this prompt only installs.
```

Then start a **new** Claude session and type `/meta-ads-connect` — or just say
**"connect my Meta ads"**. You'll log in to Meta in your browser once, approve
access, and you're connected. No access token is stored on your machine, and no
Python is needed.

Claude finishes by naming the ad accounts it can now see, telling you in plain
English what it can do with them, and offering one first thing to look at — a
read-only look, never anything that spends.

The prompt is versioned at [`setup-prompt.md`](setup-prompt.md); the Skool post
and this README both reproduce it from there.

## What this kit does

One skill, `meta-ads-connect`. It:

- Registers Meta's **official Ads MCP server** with Claude — the primary
  connection. You log in to Meta once in your browser; no long-lived credential
  ever sits on your disk.
- **Checks first.** If you're already connected, it says so and stops.
- **Shows you what you just got.** Once the connection is proved, it lists what
  it can now do for your accounts in plain English and offers one read-only
  first look.
- Optionally layers on Meta's **official Ads CLI** for the main thing the MCP
  server can't do: uploading image and video files from your own machine.

After that, you just talk to Claude about your ads.

## What you get access to

Campaigns, ad sets, ads, creatives, budgets, audiences and lookalikes, and
reporting — including Meta-internal signals like opportunity score and industry
benchmarks that aren't available through the API at all. With the optional CLI
added, image and video upload from your own files as well.

No read-only mode, no artificial limits. Claude will confirm with you before
anything that changes spend or sets an ad live.

## Requirements

- A Meta ad account
- Claude Code — the terminal and the desktop app both work.
- That's it. Python is only needed if you later add the optional CLI path.

## The optional CLI path

The main connection needs none of this. Adding the CLI gets you local image and
video upload. It installs Meta's official Ads CLI at a pinned version, mints a
**system user token** that never expires (driving the browser itself — no
copying secrets by hand), and sets up Business Manager access if you don't have
it. It needs Python 3.13 or 3.12; the kit sorts the version out for you.

You never need to run these yourself — Claude does — but each one is safe to re-run:

| Command | What it does |
| --- | --- |
| `meta-ads-connect probe` | Live connection check, one line per transport. Always the first thing to run. |
| `meta-ads-connect doctor` | Checks each part separately and says what to fix. |
| `meta-ads-connect register-mcp` | Registers Meta's official Ads MCP server (the primary connection), for all your projects. |
| `meta-ads-connect login` | Completes the one-time Meta login — opens the browser approval and verifies the result. |
| `meta-ads-connect install` | Installs Meta's official Ads CLI at a pinned version. |
| `meta-ads-connect mint-token` | Opens a browser, creates a token, saves it straight to disk. |
| `meta-ads-connect store-token` | Stores a token you already have, read from standard input. |
| `meta-ads-connect repair-assets` | Fixes a missing Business Manager or an unassigned ad account. |
| `meta-ads-connect exec -- …` | Runs Meta's Ads CLI with your token in place, e.g. `exec -- ads account list`. |

The `probe` JSON includes a `transports` block reporting the MCP server and the
CLI separately, so a working connection is never hidden behind a broken
optional one.

## What lives on your machine, and how to leave

The MCP connection stores no credential of its own — you approve it in your
browser, and you can revoke it at Meta's end at any time under
[facebook.com → Settings & privacy → Business integrations](https://www.facebook.com/settings?tab=business_tools).

If you add the optional CLI path, its token lives at `~/.meta-ads/.env`,
readable only by your user account, inside a folder only your user account can
open. It is loaded per command — by `exec`, which is the only thing that puts
it into an environment — and **never** written into your shell profile or your
operating system's keychain. The CLI itself is installed into
`~/.meta-ads/venv` rather than onto your `PATH`, so it cannot collide with any
other Python you use.

To undo everything:

```bash
claude mcp remove meta-ads      # removes the MCP server — the main connection
rm -rf ~/.meta-ads              # removes the optional CLI path: token and installed CLI
```

And to remove the kit itself:

```bash
rm -rf ~/.claude/skills/meta-ads-connect ~/meta-ads-connector
```

To revoke the CLI token at Meta's end — which you should do if you ever think
it has leaked — go to
[Business Settings → System users](https://business.facebook.com/settings/system-users),
select the system user, and remove its token.

Claude is instructed never to print the token, and `doctor` redacts it from all
output, including error messages relayed back from Meta.

## Development

```bash
uv venv && uv pip install -e '.[dev]'
.venv/bin/python -m pytest      # full suite
.venv/bin/python -m mypy        # strict
```

Tests fake exactly two boundaries — outbound HTTP to Meta, and subprocess execution — and
assert on what each subcommand actually does: its exit code, its output, and the state of
the filesystem afterwards. No test asserts which internal function was called, so a
refactor that keeps behaviour identical cannot break the suite. The load-bearing prose
artifacts are asserted on directly: `SKILL.md` by `tests/test_skill_routing.py`,
`setup-prompt.md` by `tests/test_setup_prompt.py`, and the promises this README and the
docs make about behaviour by `tests/test_docs_promises.py`.

## Before release

One full live run-through against a real ad account is still required. It doubles as the
capability inventory the routing rules depend on:

1. Paste the setup prompt into a clean Claude Code session on a machine with no prior
   setup; confirm the skill exists in the next session. Repeat on a machine with no
   Python at all.
2. Run connect. Does MCP consent succeed, and what does the consent screen list? Does the
   capability tour then fire, name a real ad account, and offer something read-only?
3. Capture a live `tools/list` from the MCP server and commit it with its capture date.
4. Exercise the promised surface end to end through the MCP alone — enumerate accounts,
   create a paused campaign, an ad set and an ad, attach a creative, pull reporting,
   clean up. Note anything that cannot be done.
5. Does the Claude Code `redirect_uri` bug still bite in practice? If so, walk the
   bring-your-own-app fallback as a user would.
6. End to end on the optional CLI: upload an image creative → verify in Ads Manager →
   clean up. Confirm the browser selectors in `src/meta_ads_connect/minting.py` against
   live Business Settings.

## Keeping it accurate

Meta ships changes to these connectors without version bumps and without a changelog. This
kit pins what it can and is **due a re-check in September 2026**. See
[`docs/research/findings-and-decisions.md`](docs/research/findings-and-decisions.md)
section 9 for what to check and why.

## Licence

MIT
