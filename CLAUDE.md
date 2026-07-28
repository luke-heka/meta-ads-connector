# Meta Ads Connector

A Claude Code kit that connects Claude to Meta Ads in one shot and gives it full
management of the user's ad accounts. Distributed to the Selr AI Skool community as a
public repo they clone.

Before working on the connector itself, read
[`docs/research/findings-and-decisions.md`](docs/research/findings-and-decisions.md) —
section 7 holds the locked design (official Ads CLI primary, official Ads MCP alongside
for audiences and benchmarks, raw Graph API out).

## Agent skills

### Issue tracker

Linear — Selr AI workspace, **Digital Products** (`DP`) team. GitHub Issues on this repo
is not the tracker. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, each label string equal to its name. See
`docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` and `docs/adr/` at the repo root. See
`docs/agents/domain.md`.
