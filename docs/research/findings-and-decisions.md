# Meta Ads Connector — Research Findings & Shared Understanding

**Date:** 2026-07-28
**Status:** Design locked. Build not started. One spike outstanding.
**Repo:** `luke-heka/meta-ads-connector` (public)
**Raw agent output:** [`raw-agent-findings.md`](./raw-agent-findings.md) (843 lines, all probe transcripts)

---

## 1. Why this exists

Connecting Claude to Meta Ads fails reliably, for three compounding reasons:

1. **Not in training data.** The official connectors shipped 2026-04-29. Claude does not know they exist and improvises.
2. **The public web is actively wrong.** Dozens of articles instruct `npm install -g @meta/ads-cli`. That package does not exist in npm. The real package is `meta-ads` **on PyPI**. Widely-repeated tool counts ("29 tools") are stale by a factor of three.
3. **Selr's own kits contradict each other.** Multiple internal skills point at three different connectors, one of which is a deprecated third-party fork, and one internal knowledge note asserts the official MCP does not work at all.

The result: Claude reconnects accounts that are already connected, routes to the wrong connector, or dead-ends.

---

## 2. The decisive finding: one API, two official transports

There is exactly **one API** — the Graph / Marketing API. Everything else is a transport over it.

Verified: the CLI depends on `facebook-business` and surfaces raw Graph errors verbatim; the MCP's OAuth metadata points at `graph.facebook.com/v25.0`. Same for both Business SDKs, all third-party MCPs, Composio/Zapier/Pipedream, and the n8n node.

Two corrections to common assumptions:

- **Conversions API is not a separate API.** It is `POST /v25.0/<DATASET_ID>/events` — same host, same token, inbound only. Cannot manage ads.
- **Webhooks are push-only** and there are **no topics for campaign/adset/ad state**. The only ads-relevant topic is `leadgen`. Not a management path.

The only genuinely non-Graph surface is **Ads Manager's bulk CSV import** — real, and the only high-volume bulk-edit path Meta offers, but UI-only with no documented endpoint. Reaching it means browser automation against a logged-in session. Noted for completeness; not used.

Meta's `ads-ai-connectors` documentation section was fully enumerated: **17 pages, exactly 2 products** (Ads CLI: 8 pages, Ads MCP Server: 9). **There is no third official connector.** That question is closed.

---

## 3. The two official surfaces

Docs live at `developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/` — **not** under `/docs/marketing-api/`. An earlier research pass 404'd on the wrong path and wrongly concluded the CLI did not exist.

### 3.1 Official Ads CLI — `meta-ads` on PyPI

- Package licence field: *"Copyright (c) Meta Platforms, Inc. and affiliates."* First-party.
- Verified by **installing it** (`meta-ads==1.1.0`, Python 3.13) and dumping the full `--help` tree. Every claim below is from the running binary, not from docs.
- **No `auth login` subcommand** — only `auth status`. Auth is a system user token in an env var or `.env`. **No browser, ever.** This is what makes it portable and scriptable.
- **Uploads images and videos — confirmed live.** Probed with a deliberately invalid token:

  ```
  $ meta --debug ads creative create --name probe --image ./t.png --page-id 123 ...
  Error: Image upload failed (190): Invalid OAuth access token data.

  $ meta --debug ads creative create --name probe --video ./t.mp4 ...
  Uploading video t.mp4...
  Error: Video upload failed (190): Invalid OAuth access token data.
  ```

  Both reached Meta and failed **only** on token validity. Corroborated by compiled-binary symbols `_upload_image` / `_upload_video` and by Meta's doc: *"Ads CLI uploads media files automatically when you create or update an ad creative."* Upload is **fused into** `creative create`/`update` — there is no standalone upload command.
- **Five commands take you from a local file to a live image or video ad.**

**Known holes:** zero audience commands. Exposes 8 of 89 breakdowns, no `action_breakdowns`.

**Rot risks:**
- **mypyc-compiled** (`meta/*.so`) → **cp312/cp313 wheels only, no sdist.** Python 3.14 install fails outright (hit twice during research). Source cannot be read or patched.
- Releases: 1.0.0 and 1.0.1 both 2026-04-29 (same-day hotfix adding cp313 wheels), **1.1.0 on 2026-06-17, still latest.** Three releases in three months, no 2.x, no breaking changes yet.
- **No public changelog, no public repo.** Change detection = diffing `meta --help`.

### 3.2 Official Ads MCP Server — `https://mcp.facebook.com/ads`

- **~93 tools across 7 categories** (ad-creation category alone has 30). The widely-cited "29 tools" is stale. Counts for two categories are exact rendered-page text; the other five are regex-derived and high-confidence but not exact. **A live `tools/list` has never been captured** — see spike below.
- Meta officially documents Claude Code support, verbatim:
  `claude mcp add --transport http --client-id <META_APP_ID> meta-ads https://mcp.facebook.com/ads`
- **Cannot upload images or videos at all.** `ads_create_creative` is single-image-link only; image/video tools are read-only.
- **Uniquely provides 7 Meta-internal analysis tools with no Graph equivalent** — `ads_get_opportunity_score`, `ads_insights_industry_benchmark`, `ads_insights_auction_ranking_benchmarks`, and others. These cannot be rebuilt on any other transport.
- Covers audiences fully (7 tools, including lookalikes and hashed-PII upload) — the CLI's one real gap.
- **Unversioned and unpinnable.** No version segment, no versioned alias (`/mcp`, `/ads/sse` and others all 404). Currently v25.0 server-side. Docs already stamped "Updated: Jul 14, 2026" — which is how 29 tools silently became ~93. **Zero effort to stay current, zero ability to stay still.** A skill hardcoding tool names can break without warning.

### 3.3 The App ID question — resolved

Meta runs a **`client_name`-allowlisted pseudo-DCR**. `POST /.well-known/register/ads` does not mint a new app; it returns a **pre-provisioned first-party Meta app**, but only to recognised callers. Reproduced three times:

| `client_name` | Result |
|---|---|
| `"Claude"`, `"Claude Desktop"`, `"Claude Code"`, `"claude"` | **200** — `client_id: 4510005499318155`, a Meta-owned app named "ads MCP server" |
| `"ChatGPT"` | 200 — different app `1718457352668935` (one first-party app per partner) |
| `"Anthropic"`, `"Cursor"`, `"x"` | 400 `"Dynamic registration is not available for this client."` |

Match appears to be a case-insensitive substring test on `claude`. Redirect URI validated separately: `https://claude.ai/api/mcp/auth_callback` ✓, `http://localhost:<any port>/callback` ✓, `claude://…` ✗.

An earlier pass posted a generic client name, got the 400, and generalised it to everyone. **That was wrong.**

Corroboration:
- Meta's get-started page: *"Owning a Meta app is not a prerequisite on using the ads MCP server."* The developer-app block is explicitly the optional BYO path. **There is no Claude Desktop section** — only "from Claude Code", "from ChatGPT", "with user access token".
- Anthropic's docs: OAuth Client ID/Secret live under *"Advanced settings"* and are **optional**.

**Claude Code CLI wrinkle — an Anthropic bug, not a Meta requirement.** `anthropics/claude-code#57191` (verified via API): OAuth works on claude.ai and Desktop, fails in Claude Code CLI with *"The provided redirect_uris are not registered for this client."* Closed as duplicate of **#37747 — a Claude Code 2.1.80+ regression where redirect_uris omit the dynamic port.**

→ Protocol does not require an App ID on either surface, but given the live CLI bug, **passing your own App ID is the reliable CLI path**.

---

## 4. Auth reality

Meta's docs, verbatim: *"If your app is only managing your ad account, standard access to the `ads_read` and `ads_management` permissions are sufficient."*

**Dev mode + your own account + full write access = no App Review, no business verification.** The real ceiling is the rate tier: dev tier is 60 points with writes at 3 points each (~20 writes / 5 min) versus 9,000 on Full. Upgrading is **usage-gated** (500 calls/15 days, <15% errors), not a review — it self-clears.

Meta renamed the tiers (old "Standard" → "Limited", old "Advanced" → "Full") and did not harmonise the doc pages, which is why secondary sources are a mess here.

**System user tokens never expire.** 60-day long-lived user tokens are the trap to avoid.

### `is_ads_mcp_enabled` — dropped

A rumoured per-account rollout flag. **Appears nowhere in Meta's docs**; Meta documents no way to check or request it. Zero first-hand reports; all sourced to one SEO content-farm cluster, several of them third-party MCP vendors selling the alternative. The maintainer's separate observation (Claude reporting an account can't have data collected) is a different symptom, most likely originating in one of Selr's own skills rather than in Meta's platform. **Dropped from scope.**

---

## 5. Rejected options

| Option | Why rejected |
|---|---|
| **Raw Graph API** as a required path | Real ceiling advantage (990 node classes, 126 `AdAccount` edges, 220 insights fields, 89 breakdowns, plus `adrule`/`adlabel`/`adreportrun`/`/asyncbatch` which neither official surface exposes) — but nothing it adds is needed to launch or manage ads. Optional extender, not a dependency. **Cut to keep the kit simple.** |
| **pipeboard-co/meta-ads-mcp** | 1,108 stars but a paid SaaS proxy with unclear licence. Ad-spend credentials route through a third party. |
| **gomarble MCP** | Clean, MIT — but strictly read-only. |
| **Zapier / Composio / Pipedream** | Leads and audiences only; no campaign management. |
| **`facebook-pp-cli`** (Selr's own Go CLI) | Unofficial, private scaffold in an 84-CLI experiment repo, self-declared `install: kind: stub`. Meta's first-party CLI supersedes it. |
| **Ads Manager bulk CSV import** | UI-only, no endpoint. Would require browser automation against a live session. |

---

## 6. Existing Selr Meta estate

Nine distinct products found across one org (`selrai-company`) and four personal owners.

| Repo / path | What it is | Disposition |
|---|---|---|
| `luke-heka/meta-ads-connector` | **This kit.** | Build |
| `Mr-heka/meta-ads-mcp-setup` (public) | Current connector skill, official-MCP path, 3 files. Claims "no dev app needed" — accidentally correct, but for the wrong reason. | Supersede |
| a teammate's `meta-ads-mcp-setup` | Zero-divergence fork | Delete or stub |
| `luke-heka/meta-ads-mcp-setup` | Old pipeboard version. **Repo gone**, still in kit index. | Purge from index |
| `Mr-heka/meta-ads-dashboard` (public) | Next.js + Supabase, verdict engine, approval queue. Most substantial Meta product owned. Unindexed. | Finished — not in scope |
| `selrai-company/business-operating-strategy` | BOS `/ads` page, origin of the dashboard, shares `meta-audit-sync.ts` | Live — leave alone |
| a teammate's `marketing-agency-workshop` | Module 3 holds the **Playwright system-user minting code to reuse** (`platforms/meta/playwright/03-system-user.spec.ts`). Wires pipeboard. | Mine for code; rewire later |
| `selrai-company/claude-workshop-kit` | `managed-agents-setup` (pipeboard wiring), `meta-business-suite-connector` (IG/organic, not ads), `paid-ads` (**false claim of direct account access**) | Two small fixes |
| `selrai-company/printing-press-cli-experiments` | `pp-facebook` Go CLI | Dropped |
| Deck'd Out platform | Client lead-ads production | Untouched |

Practitioner "brain" skills, `ad-claims-audit`, and the WorldGym connector (whose `meta_ads_campaign_performance` returns **mock data with the real call commented out**) have no live Meta connection.

**Deprecation blast radius:** nine reference sites, notably three copies of the pipeboard wiring (`connect-meta-ads.sh`, `mcp-bridge.json`, plus a verbatim duplicate of the marketing-agency skill vendored into `pt-industry-pack-workshop`), the contradictory knowledge note, and ~10 kit-index YAMLs.

> **Method caveat:** `gh search code` is badly under-indexed for these orgs — it missed `graph.facebook.com` in a public repo. Its silence proves nothing. Repo-tree walks and local content greps are the reliable signal.

---

## 7. Shared understanding — the locked design

**Repo:** `luke-heka/meta-ads-connector`, public, cloned from GitHub. Audience: Skool community business owners.

**Skill:** one, named `meta-ads-connect`.

**Transports:**
- **Official Ads CLI is primary and does everything** — campaigns, ad sets, ads, creatives, image + video upload from local files, budgets, insights. Pinned `meta-ads==1.1.0`, interpreter pinned to Python 3.13.
- **Official Ads MCP installed alongside**, for the two things the CLI cannot do: audiences, and the seven Meta-internal analysis tools.
- **Raw Graph API is out.** Third-party MCPs out. `pp-facebook` out.

**Precedence rule, written for Claude to read** — CLI for everything; MCP only for audiences and benchmarks; never reconnect what is already connected.

**Auth:** one system user token, scopes `ads_management` + `ads_read` + `pages_show_list` + `leads_retrieval`. Full capability, no scope questionnaire — a business owner has no basis to choose, and a crippled token is pointless. Safety lives in skill behaviour (confirm before anything that changes spend or sets something live), not in reduced permissions.

**Token minting:** Claude drives Playwright. Token copied and pasted **programmatically** — never by hand.

**Token storage:** `~/.meta-ads/.env`, mode 600, exported per-invocation. No shell-profile edits, no OS keychain. OS-agnostic.

**Account state:** the skill detects and repairs — no Business Manager (create one), ad account unassigned (assign it), both present (proceed). Never a blocking question.

**MCP registration, two-tier:** try the no-App-ID path first; on the redirect_uri failure (Anthropic bug #37747), fall back to BYO app. The fallback is a bare dev-mode app — no App Review, no business verification, under 5 minutes — and is **walked through manually, not automated**: it needs a logged-in Meta session and breaks silently under automation.

**Idempotence:** first action is always a live probe. Already connected → exits in seconds. This is the actual fix for the reconnect problem.

**Python:** the skill resolves the interpreter itself. cp312/cp313 only; 3.14 fails outright.

**Build from `--help`, never the docs.** Two confirmed drifts: `--instagram-actor-id` (docs) vs `--instagram-user-id` (binary), and a documented `meta auth` that the shipped binary does not have.

**Testing:** a doctor/verify script (Python version, CLI install, token validity, MCP registration) plus one full live run-through.

**Also in scope today, small:** fix `selrai-internal-kit/knowledge/infrastructure/meta-ads.md` (asserts the official MCP "DOES NOT WORK"), and fix `paid-ads`'s false claim of direct ad-account access. Both actively misroute Claude.

**Parked:** pack rework · wider pipeboard deprecation (`marketing-agency-workshop`, `managed-agents-setup`) · kit-index entries · Meta-ads knowledge layer · the dashboard · Skool announcement wording.

---

## 8. Outstanding — the spike

Everything above that could be established from outside the login wall has been. The remaining unknowns need a real authenticated session:

1. **Does MCP consent actually succeed** on a real Selr ad account, and what does the consent screen list?
2. **Capture a live `tools/list`** — settles the ~93 count and gives exact tool names for the precedence rule.
3. **Does the Claude Code CLI redirect_uri bug (#37747) still bite** on the current version, i.e. is the BYO-app fallback needed in practice or only in theory?
4. **End-to-end CLI run** with a real system user token: enumerate ad accounts → create a paused campaign → upload an image creative → verify in Ads Manager → clean up.

**2-minute manual check for (1):** Claude Desktop → Settings → Connectors → Add custom connector → paste `https://mcp.facebook.com/ads` → Add, leaving Advanced settings empty. Consent screen with ads scopes = no App ID needed. Error *before* the browser opens = client/DCR problem. Error *after* consent = an eligibility gate.

---

## 9. Anti-rot checklist

Most important first.

- Pin `meta-ads==1.1.0` **and** the interpreter to Python 3.13.
- Build all CLI invocations from `meta --help`, not from documentation.
- Treat MCP tool names as unstable — do not hardcode where avoidable.
- Graph API: v19.0–v25.0 all live; v25.0 current; new version every 4–5 months (v26 expected ~Aug–Oct 2026); a version dies two years after its successor and then **silently defaults to the next oldest** — degrading rather than hard-failing, which is worse.
- Re-check the whole picture ~September 2026.

---

## 10. Primary sources

- [Meta announcement — Ads AI Connectors](https://www.facebook.com/business/news/meta-ads-ai-connectors)
- [Ads CLI launch blog (2026-04-29)](https://developers.facebook.com/blog/post/2026/04/29/introducing-ads-cli)
- [Ads MCP Server overview](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-overview)
- [Ads MCP Server get started](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-get-started)
- [Ad creation & management tools](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-tools-ad-creation-and-management)
- [Ads CLI get started](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/get-started)
- [`meta-ads` on PyPI](https://pypi.org/project/meta-ads/)
- `anthropics/claude-code` issues #57191, #37747

> Note on trust: three separate false negatives occurred during this research — "no official CLI exists" (wrong registry + wrong doc path), "29 tools" (stale secondary sources), and "DCR is closed" (generic `client_name` in the probe). In each case an absent lookup was treated as proof of absence. Every "does not exist" claim in this document is backed by a positive probe or an enumerated doc section, not by a failed search.
