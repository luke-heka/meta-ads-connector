# Issue Tracker

Issues for this repo live in **Linear**, not GitHub Issues.

GitHub Issues on `luke-heka/meta-ads-connector` is **not** the tracker. Don't create,
read, or close issues there. The repo's issue tab belongs to the community, not to
internal work tracking.

## How to read and write issues

Prefer the Linear MCP tools when they're loaded (`mcp__linear__list_issues`,
`mcp__linear__get_issue`, `mcp__linear__save_issue`, `mcp__linear__list_issue_labels`).
They handle auth themselves.

If the MCP isn't available, use the GraphQL API directly. The key lives in a local env
file as `LINEAR_API_KEY` and goes in a **raw `Authorization` header with no `Bearer`
prefix**:

```bash
set -a; source /path/to/your/.env; set +a
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ issue(id:\"ABC-123\") { title description state { name } } }"}'
```

The team ID lives alongside it as `LINEAR_TEAM_ID`.

## Creating issues

- Create the issue **at the start of the work**, not after it's finished.
- Attach it to a project when one obviously fits; otherwise leave the project unset
  rather than inventing one. Never create an initiative from an agent.
- Apply a triage label from `docs/agents/triage-labels.md`.
- No prescribed title or body format — write what a human would actually find useful.

## Linking back to GitHub

There is **no issue sync**. The link between Linear and this repo is one-directional
and lives in the branch name and PR:

- Branch: include the Linear ID, e.g. `abc-123-mint-system-user-token`
- PR title or body: reference the issue ID so Linear picks up the backlink

Maintainers do not create GitHub issues. Don't ask them to.

## PRs as a request surface

**Off.** Externally-opened PRs on the public repo are not automatically part of the
triage queue. If a community PR needs tracking, a maintainer raises the Linear issue.
