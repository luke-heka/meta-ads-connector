---
name: meta-ads-connect
description: Connect Claude to Meta Ads and manage the user's ad accounts — campaigns, ad sets, ads, creatives with image and video upload, budgets, audiences and reporting. Use when the user mentions Meta ads, Facebook ads, Instagram ads, their ad account, ad spend, or asks to connect, set up, fix or check any of those. Also use before any Meta ads work, to check whether a connection already exists.
---

# Meta Ads

You manage this user's Meta ads. Two official transports are already chosen for
you; do not go looking for others.

## Rule 1 — Probe first. Always.

**Your first action in any Meta ads conversation is `probe`.** Not a question to
the user, not a look at the filesystem, not a guess from earlier in the
conversation. Run it:

```bash
meta-ads-connect probe --json
```

It is a live authenticated call to Meta and takes a couple of seconds. Read
`state` from the JSON and act on it:

| `state` | Exit | What it means | What you do |
| --- | --- | --- | --- |
| `OK` | 0 | Fully connected | **Stop. Do not run setup.** Get on with what the user asked. |
| `MCP_MISSING` | 6 | Connected, MCP server not registered | `register-mcp` only. Nothing else. |
| `NO_AD_ACCOUNTS` | 7 | Token works, no accounts assigned | `repair-assets` only. |
| `TOKEN_REJECTED` | 1 | Meta revoked or rejected the token | Tell the user plainly, offer to re-mint, then `mint-token`. |
| `NO_TOKEN` | 2 | CLI installed, no token | `mint-token` only. **Do not reinstall.** |
| `NOT_INSTALLED` | 3 | Nothing set up | Full setup — see below. |
| `RATE_LIMITED` | 4 | Meta is throttling | Wait, retry. Change nothing. |
| `NETWORK_ERROR` | 5 | Meta unreachable | Check connection, retry. Change nothing. |
| `META_ERROR` | 8 | Unrecognised Meta error | Run `doctor` and read what it says. |

Never reconnect what is already connected. Restarting a finished setup is the
single most-reported failure of every previous version of this, and re-running
the probe is how you avoid it. If the user insists something is broken and the
probe says otherwise, run `doctor` — do not start setup on their say-so.

## Rule 2 — The CLI does everything. The MCP is for two things.

- **Meta's official Ads CLI is primary and does everything.** Campaigns, ad
  sets, ads, creatives including image and video upload from local files,
  budgets, insights and reporting. Reach for it by default, every time.
- **Meta's official Ads MCP server is for exactly two things:** custom
  audiences and lookalikes (the CLI has no audience commands at all), and
  Meta's internal analysis tools — opportunity score, industry benchmarks,
  auction ranking benchmarks — which have no equivalent anywhere else.
- **The raw Graph API is out of scope.** So are all third-party Meta MCP
  servers. If you find yourself about to `curl graph.facebook.com` or install
  something else, stop: the answer is one of the two above.

## Rule 3 — Build CLI commands from `--help`, never from memory or docs.

The CLI's documentation and its shipped binary disagree, confirmed in at least
two places: the docs say `--instagram-actor-id` where the binary wants
`--instagram-user-id`, and the docs describe a `meta auth` subcommand the binary
does not have. Anything you remember about this CLI predates its existence.

**Run the CLI through `meta-ads-connect exec`.** The CLI is installed into an
environment this kit owns, so `meta` is deliberately not on your PATH — that is
what stops it colliding with the user's other Python work, and what makes
uninstalling a single `rm -rf`. `exec` finds the binary, puts the token in the
environment for that one invocation, and redacts the token from the output:

```bash
meta-ads-connect exec -- --help
meta-ads-connect exec -- ads campaign create --help
meta-ads-connect exec -- ads account list
```

Do not run bare `meta`, do not `source ~/.meta-ads/.env` yourself, and do not
put the token on a command line.

So, before composing any non-trivial invocation, read the real flags:

```bash
meta-ads-connect exec -- ads campaign create --help
```

Build the command from what that prints. If a flag you expected is not there,
the binary is right and you are wrong.

## Rule 4 — MCP tool names are unstable. Discover them.

The MCP endpoint is unversioned and cannot be pinned. Its published tool count
went from 29 to roughly 93 with no version change. Do not hardcode tool names or
assume a tool exists because it did last week — list what is actually available
and use that.

## Rule 5 — Confirm before spending money.

Full write access is deliberate. Safety lives here, in how you behave, not in a
crippled token.

- **Create everything paused.** Campaigns, ad sets and ads are created in a
  paused state unless the user has explicitly said to set them live in this
  conversation.
- **Confirm before anything that changes spend or sets something live.** That
  means: setting status to `ACTIVE`, changing a budget, changing a bid strategy
  or bid amount, and changing a schedule. State plainly what will change and
  what it will cost, then wait for a yes.
- **Deletions need an unmistakable instruction.** "Tidy up my campaigns" is not
  one. Ask which, name them back, and wait.
- Reading — insights, reporting, listing, benchmarks — needs no confirmation.
  Do not pester the user about read-only work.

## Rule 6 — Never print the token.

It has spend authority and transcripts get shared. Do not echo it, do not
`cat ~/.meta-ads/.env`, do not include it in a command you show the user, and
do not ask them to paste it to you. The kit moves it from browser to disk
itself, and `exec` is what puts it into an environment. If you ever need to
prove it exists, run `doctor`, which redacts it.

## Setting up from scratch

Only when `probe` returned `NOT_INSTALLED`. Tell the user first that it takes
about five minutes, that they will need to log in to Meta themselves once, and
that everything else is automatic.

```bash
meta-ads-connect install        # resolves a Python, installs the pinned CLI
meta-ads-connect mint-token     # drives the browser; saves the token directly
meta-ads-connect repair-assets  # fixes Business Manager / account assignment
meta-ads-connect register-mcp   # adds Meta's official MCP server
meta-ads-connect probe          # confirm
```

Every one of these is safe to re-run and each tells you what to do next when it
fails. Run only the ones the probe said were missing.

If `mint-token` exits 64, the browser automation extra is not installed. Install
it and run `mint-token` again:

```bash
pip install 'meta-ads-connect[mint]'
playwright install chromium
```

If that cannot be installed, `mint-token` also prints a manual walkthrough — read
it out. It ends with a `store-token` command the user pipes their token into, so
the token still never passes through this conversation. Never ask them to paste
it to you.

`mint-token` exiting 2 means no token was created. Read out whatever it printed:
if the user has no Business Manager it prints how to create one, which takes two
minutes and is the prerequisite for everything else.

`repair-assets` exits 16 when it could only assign some of the ad accounts, or
none. It prints the manual steps — read them out; the user finishes in Business
Settings in under a minute. Exit 15 means they have no Business Manager and 17
means they have no ad account: both are things only they can create, and both
print a walkthrough.

`repair-assets` is worth running whenever a user says an ad account is missing,
even if `probe` returned `OK`: `OK` means at least one account is reachable, and
the repair is what finds the ones that are not.

If `register-mcp` exits 13, Claude Code hit a known redirect_uri bug of its own.
The command prints a walkthrough for creating a bare developer app — read it out
and let the user do those steps themselves. It needs no App Review and no
business verification. Do not try to automate it: it needs a logged-in Meta
session and fails silently under automation.

## When something is wrong

```bash
meta-ads-connect doctor
```

It reports each component separately and names the next action for each. Use it
instead of guessing, and instead of asking the user to describe symptoms.

Known cases worth recognising:

- **Python 3.14** — Meta's CLI has no build for it. `install` picks 3.13 or 3.12
  itself; if neither exists it says so and names what to install.
- **Windows** — no build exists at all. WSL is required, and the kit says so
  rather than failing halfway through.

## What this kit will not do

Raw Graph API calls, third-party Meta MCP servers, and Ads Manager bulk CSV
import are all deliberately out of scope. Do not add them, and do not work
around their absence by installing something else.
