# Meta Ads Connector

Connect Claude to Meta Ads in one shot, and give it full management of your ad accounts.

> **Status: in progress.** Research complete and the design is locked. The skill is not built yet.
> See [`docs/research/findings-and-decisions.md`](docs/research/findings-and-decisions.md).

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

## Licence

MIT
