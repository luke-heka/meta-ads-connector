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

## What this kit does

One skill, `meta-ads-connect`. It:

- Installs and pins Meta's **official Ads CLI**, sorting out the Python version for you.
- Mints a **system user token** that never expires, driving the browser itself — no copying and pasting secrets by hand.
- Sets up your Business Manager and ad account access if you don't already have them.
- Registers Meta's **official Ads MCP server** alongside, for audiences and Meta's internal benchmark data.
- **Checks first.** If you're already connected, it says so and stops.

After that, you just talk to Claude about your ads.

## What you get access to

Everything: campaigns, ad sets, ads, creatives, image and video upload from your own files, budgets, audiences, and reporting — including Meta-internal signals like opportunity score and industry benchmarks that aren't available through the API at all.

No read-only mode, no artificial limits. Claude will confirm with you before anything that changes spend or sets an ad live.

## Requirements

- A Meta ad account (the kit helps you sort out Business Manager if you haven't got that yet)
- Claude Code, in the terminal or inside Claude Desktop
- Python — the kit handles the version for you

## Installing

Clone this repo, copy the skill into Claude, and install the package behind it:

```bash
git clone https://github.com/lukeselr/meta-ads-connector.git
cd meta-ads-connector

mkdir -p ~/.claude/skills
cp -r skills/meta-ads-connect ~/.claude/skills/

pip install .            # add '.[mint]' for browser-driven token minting
```

Then just tell Claude: **"connect my Meta ads"**.

## Doing it by hand

You never need to run these yourself — Claude does — but each one is safe to re-run:

| Command | What it does |
| --- | --- |
| `meta-ads-connect probe` | Live connection check. Always the first thing to run. |
| `meta-ads-connect doctor` | Checks each part separately and says what to fix. |
| `meta-ads-connect install` | Installs Meta's official Ads CLI at a pinned version. |
| `meta-ads-connect mint-token` | Opens a browser, creates a token, saves it straight to disk. |
| `meta-ads-connect store-token` | Stores a token you already have, read from standard input. |
| `meta-ads-connect register-mcp` | Registers Meta's official Ads MCP server. |
| `meta-ads-connect repair-assets` | Fixes a missing Business Manager or an unassigned ad account. |
| `meta-ads-connect exec -- …` | Runs Meta's Ads CLI with your token in place, e.g. `exec -- ads account list`. |

## Where your token lives

`~/.meta-ads/.env`, readable only by your user account, inside a folder only your user
account can open. It is loaded per command — by `exec`, which is the only thing that puts
it into an environment — and **never** written into your shell profile or your operating
system's keychain.

Meta's Ads CLI is installed into `~/.meta-ads/venv` rather than onto your `PATH`, so it
cannot collide with any other Python you use, and nothing outside `~/.meta-ads` is
touched.

To undo everything:

```bash
rm -rf ~/.meta-ads              # removes the token and the installed CLI
claude mcp remove meta-ads      # removes the MCP server
```

To revoke the token at Meta's end — which you should do if you ever think it has leaked —
go to [Business Settings → System users](https://business.facebook.com/settings/system-users),
select the system user, and remove its token.

Claude is instructed never to print the token, and `doctor` redacts it from all output,
including error messages relayed back from Meta.

## Development

```bash
uv venv && uv pip install -e '.[dev]'
.venv/bin/python -m pytest      # 198 tests
.venv/bin/python -m mypy        # strict
```

Tests fake exactly two boundaries — outbound HTTP to Meta, and subprocess execution — and
assert on what each subcommand actually does: its exit code, its output, and the state of
the filesystem afterwards. No test asserts which internal function was called, so a
refactor that keeps behaviour identical cannot break the suite.

## Before release

One full live run-through against a real ad account is still required. It is also the
moment the outstanding research spike resolves:

1. Does MCP consent actually succeed, and what does the consent screen list?
2. Capture a live `tools/list` from the MCP server.
3. Does the Claude Code `redirect_uri` bug still bite in practice?
4. End to end on the CLI: enumerate accounts → create a paused campaign → upload an image
   creative → verify in Ads Manager → clean up.
5. Confirm the browser selectors in `src/meta_ads_connect/minting.py` against live
   Business Settings.

## Keeping it accurate

Meta ships changes to these connectors without version bumps and without a changelog. This
kit pins what it can and is **due a re-check in September 2026**. See
[`docs/research/findings-and-decisions.md`](docs/research/findings-and-decisions.md)
section 9 for what to check and why.

## Licence

MIT
