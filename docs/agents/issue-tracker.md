# Issue Tracker

Issues for this repo live in **Linear**, not GitHub Issues.

- Workspace: **Selr AI** (slug `selr-ai`)
- Team: **Digital Products** (`DP`)
- Issue IDs look like `DP-123`

GitHub Issues on `lukeselr/meta-ads-connector` is **not** the tracker. Don't create,
read, or close issues there. The repo is public and its issue tab belongs to the
community, not to our internal work tracking.

## How to read and write issues

Prefer the Linear MCP tools when they're loaded (`mcp__linear__list_issues`,
`mcp__linear__get_issue`, `mcp__linear__save_issue`, `mcp__linear__list_issue_labels`).
They handle auth themselves.

If the MCP isn't available, use the GraphQL API directly. The key lives in
`~/selrai/.env` as `LINEAR_API_KEY` and goes in a **raw `Authorization` header with no
`Bearer` prefix**:

```bash
set -a; source ~/selrai/.env; set +a
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ issue(id:\"DP-123\") { title description state { name } } }"}'
```

Team ID for `DP`: see `LINEAR_TEAM_ID` in `~/selrai/.env`

## Creating issues

- Create the issue on team `DP` **at the start of the work**, not after it's finished.
- Attach it to a project when one obviously fits; otherwise leave the project unset
  rather than inventing one. Never create an initiative from an agent.
- Apply a triage label from `docs/agents/triage-labels.md`.
- No prescribed title or body format — write what a human would actually find useful.

## Linking back to GitHub

There is **no issue sync**. The link between Linear and this repo is one-directional
and lives in the branch name and PR:

- Branch: include the Linear ID, e.g. `dp-123-mint-system-user-token`
- PR title or body: reference `DP-123` so Linear picks up the backlink

Humans on this team do not create GitHub issues. Don't ask them to.

## PRs as a request surface

**Off.** Externally-opened PRs on the public repo are not automatically part of the
triage queue. If a community PR needs tracking, a human raises the Linear issue.
