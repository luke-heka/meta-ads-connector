# Connecting Claude to Meta Ads with full read + write

Research date: 2026-07-28. Question: single best way to give Claude (Code CLI and/or Desktop) full management of Meta ad accounts (campaigns, ad sets, ads, creatives, budgets, audiences, insights) with no artificial restrictions.

Evidence standard used here: primary sources and live protocol probes wherever possible. A large volume of "Meta Ads MCP" content on the open web is SEO affiliate blogspam that echoes itself, so anything sourced only from those is explicitly flagged UNVERIFIED below.

---

## Headline answer

**Primary recommendation: the official Meta Ads MCP server at `https://mcp.facebook.com/ads`, added to Claude as a Custom Connector, with your own Business OAuth login.**

**Runner-up (and the thing to actually build today if the official server is not yet enabled on the account): your own thin skill over the raw Graph API using a Business Manager System User token.**

The deciding reason: the official endpoint is the only path that is both first-party (no third party in the data path, no SaaS tier gating writes) and free of the Meta app-review/rate-tier tax. Everything else is either read-only, a paid proxy, or requires you to run the developer-app gauntlet yourself. Its one real risk is a phased rollout flag, which is why the runner-up is a self-owned fallback rather than another vendor.

---

## 1. Official Meta MCP server — CONFIRMED REAL (verified by direct probe)

This is the most important finding and it is verified at the protocol level, not from blogs.

```
POST https://mcp.facebook.com/ads   (MCP initialize)
-> HTTP/2 401
   www-authenticate: Bearer resource_metadata="https://mcp.facebook.com/.well-known/oauth-protected-resource/ads",
     scope="ads_management ads_read catalog_management business_management
            pages_show_list instagram_basic ads_mcp_management"
   x-fb-request-id / x-fb-trace-id / x-fb-rev present  (genuinely Meta-served)
```

And the RFC 9728 protected-resource document resolves:

```json
{
  "resource": "https://mcp.facebook.com/ads",
  "authorization_servers": ["https://mcp.facebook.com/ads"],
  "scopes_supported": ["ads_management","ads_read","catalog_management",
    "business_management","pages_show_list","instagram_basic","ads_mcp_management"],
  "bearer_methods_supported": ["header"]
}
```

What this proves, first-hand:

- The endpoint exists, is live as of today, and is served by Meta infrastructure.
- It is a standards-compliant OAuth-protected MCP resource, so Claude's Custom Connector flow can drive its authorization automatically.
- **`ads_management` is in the advertised scope set.** That is Meta's write scope. `ads_read` alone would be read-only. So the official server is genuinely read+write by design, not a reporting toy.
- `catalog_management` and `business_management` are also in scope, so catalog and business-asset operations are in range.
- `ads_mcp_management` is a scope that exists nowhere in the classic Graph permission list — it appears to be MCP-specific and is consistent with the reported per-account enablement gate.

Verdict on write capability: **full write, first-party.** Auth complexity: **lowest of every option** — a browser OAuth consent, no developer app, no app review, no token file. Reliability: Meta-hosted, but see the gate below. One-shot agent automatability: high for the config step, but the OAuth consent itself is necessarily human (a browser login), which is correct and should not be automated around.

### What is NOT verified about it

- **Launch date, tool count, and the "29 tools" figure.** Every source asserting "launched 29 April 2026, 29 tools across five categories" is an SEO blog. I could not find the announcement on `developers.facebook.com` or `about.fb.com`, and `https://developers.facebook.com/docs/marketing-api/ai-connectors/` returns 404. Treat the tool count as unverified. The scope list above is the only hard evidence of capability breadth, and it is strong evidence.
- **The claimed official CLI `npm install -g @meta/ads-cli` does not exist.** I queried the npm registry directly: `@meta/ads-cli` returns `{"error":"Not found"}`, as do `@facebook/ads-cli` and `@meta-ads/cli`. The packages that do exist under similar names are third-party: `meta-ads-open-cli` (Bin-Huang), `facebook-ads-cli` (adkit-so), `meta-ads-cli` (self-described "Unofficial"). **The widely repeated "Meta shipped an official CLI" claim is, on the evidence available, false or at least not shipped under that name.** This is a clear case of blogspam propagating an unchecked detail, and it is a good reason to distrust the rest of the numbers in those same articles.
- **The per-account rollout gate.** Multiple third-party sources report an `is_ads_mcp_enabled` per-ad-account flag that returns `false` for most accounts, described as a phased rollout controlled solely by Meta with no user-facing toggle. This is consistent with the undocumented `ads_mcp_management` scope, but it is UNVERIFIED against Meta docs and I could not test it without account credentials. **This is the single biggest open risk in the recommendation, and the reason a fallback matters.**

Action to resolve: attempt the connector install on the real account. Success or an `is_ads_mcp_enabled: false` style failure resolves the question in about five minutes, and no amount of further desk research substitutes for it.

---

## 2. Anthropic's Connectors directory — no first-party Meta Ads connector

There is no Anthropic-published Meta Ads connector. What is listed in the directory is third-party and mostly analytics-shaped:

| Listing | Publisher | Shape |
|---|---|---|
| Supermetrics | third party | 200+ data sources incl. Facebook Ads. Directory badge says **Read**, but the page copy claims you can "create or update ad campaigns". Contradictory — do not rely on writes without testing. |
| Motion | third party | creative analytics, read only |
| Windsor.ai, Coupler.io | third party | reporting/data blending, read only |
| Adspirer Ads Agent | third party | listed as a plugin; unverified |

The directory is 17 pages and only page 1 was enumerated, so a narrower listing further in cannot be ruled out.

**The load-bearing fact from this section is not the directory, it is the mechanism:** Claude on web/Desktop supports adding an arbitrary remote MCP server URL as a **Custom Connector**, with OAuth, on Free through Enterprise (Free is capped at one custom connector; on Team/Enterprise only Owners may add them, and members then authenticate individually). The server must be reachable from Anthropic's public IPs. This is exactly how the official Meta endpoint gets wired in, and it means the curated directory is irrelevant to the recommendation.

---

## 3. Third-party / community MCP servers (hard data via `gh api`, 2026-07-28)

| Repo | Stars | Last push | License | Language | Write? |
|---|---:|---|---|---|---|
| pipeboard-co/meta-ads-mcp | 1,108 | 2026-07-23 | NOASSERTION | Python | Yes, but hosted SaaS |
| gomarble-ai/facebook-ads-mcp-server | 347 | 2026-07-20 | MIT | Python | **No — read only** |
| brijr/meta-mcp | 190 | 2026-05-28 | none detected | TypeScript | Likely, unconfirmed |
| amekala/ads-mcp | 75 | 2026-07-16 | none | Jupyter | multi-platform, unassessed |
| mikusnuz/meta-ads-mcp | 59 | 2026-04-12 | MIT | TypeScript | claims 135 tools, low traction |
| serkanhaslak/meta-mcp | 7 | 2026-04-09 | none | TypeScript | claims 77 tools |
| attainmentlabs/meta-ads-mcp | 3 | 2026-06-17 | MIT | Python | low traction |
| bertramdev/MetaAdsMCP | 0 | 2026-03-27 | Apache-2.0 | Python | low traction |

None archived. Broader `gh search repos` sweeps on "meta ads mcp" and "facebook ads mcp" surfaced nothing above 100 stars that is not already listed (next highest ~51 stars).

Detail on the three that matter:

**pipeboard-co/meta-ads-mcp** — the traction leader and the one most likely to be recommended by a casual search. Full CRUD is real (`create_campaign` with objective/budget/bid strategy, ad set / ad / creative management, budget updates), with sensible safety defaults (new campaigns default to `PAUSED`, confirmation on writes). But it is fundamentally **a hosted SaaS wrapper**: default auth is Pipeboard's own OAuth issuing a Pipeboard API token, the default install is their remote MCP URL, there is a free-plan-then-paid-tiers model, and self-hosting is explicitly labelled "Advanced Technical Users Only" and discouraged. **Your ad account credentials and all campaign traffic flow through a third party**, and the licence is unclassifiable (`NOASSERTION`) so the terms are not even clear. Whether write specifically sits behind a paid tier is unverified. Against a brief that says "no artificial restrictions", a discouraged self-host path and an undocumented pricing gate are exactly the artificial restrictions to avoid.

**gomarble-ai/facebook-ads-mcp-server** — clean, MIT, fully local (your own token via `--fb-token`, Meta calls go straight from your machine to Meta with no vendor proxy), well maintained. **But it is strictly read-only.** Its entire tool table is lookups, insights, activity history, pagination. Excellent reporting server; disqualified by the brief.

**brijr/meta-mcp** — bring-your-own-everything and genuinely unrestricted in spirit (your Meta app, your Cloudflare account, your JWT issuer). Tool families cover campaign, ad set, creative, and audience management (39 tools) but the README does not enumerate signatures, so field-level write confirmation would need a source read. Install is "deploy your own Cloudflare Worker with D1 and KV bindings" — heaviest setup of the three, no licence file, and 2 months since last push. A reasonable base to fork, a poor thing to adopt as-is.

---

## 4. Aggregators

- **Zapier** — three separate Facebook MCP surfaces, all narrow. Lead Ads is a single "New Lead" trigger (read only). Pages is content posting, no ads at all. Custom Audiences can add/remove emails (audience membership write only). **No campaign or budget management.** Disqualified.
- **Composio (Metaads toolkit)** — genuinely write-capable: create campaign, ad set, ad, creative, audience against the Marketing API. You supply your own Meta OAuth app credentials and Composio manages token storage and refresh. Broader surface than Zapier. Pricing tier unverified. This is the strongest aggregator option, but it still inserts a third party into the credential path and you still need your own Meta app, so it combines the downsides of both other approaches.
- **Klavis AI** — a Meta Ads server exists and is described as enabling campaign management, but no tool list was verifiable. UNVERIFIED.
- **Pipedream, Paragon** — no Meta Ads campaign-management surface found. Not confirmed absent, just not found.

---

## 5. Official Meta CLI and the Business SDKs

- **No official Meta Marketing API CLI exists** under any name I could find on npm (see section 1). There is no `fb` binary from Meta. The third-party CLIs (`meta-ads-open-cli`, `adkit-so/facebook-ads-cli`, `@adkit/cli`) are small, young projects.
- **The Business SDKs are real and are the solid ground here**: `facebook_business` (Python) and `facebook-nodejs-business-sdk` are Meta-maintained, version-tracked against the Marketing API, and cover the full object model. As a base for a thin skill they remove all the request-signing and pagination tedium. They are, however, verbose and heavily class-based; for an agent-driven skill, raw Graph calls via `httpx` are often clearer and easier for a model to compose than the SDK's builder objects.

---

## 6. Raw Graph API + System User token — the "write your own thin skill" option

This is the runner-up and the fallback, and it is more attractive than it first sounds because a skill is just a markdown file plus a token. There is no server to run, no vendor, no MCP process, no rate limit but Meta's own, and no tool-surface ceiling — the whole Marketing API is reachable, including anything an MCP server's fixed tool list would have omitted. In Claude Code this is arguably a *better* fit than MCP: `curl`/`httpx` against `graph.facebook.com/v23.0/...` composes freely, whereas an MCP server can only do what its authors enumerated.

The cost is the auth setup, which is a one-time human path through Business Manager (detailed below), and the fact that you own correctness — nothing stops a malformed write, so the skill should encode guardrails (create paused, confirm before budget changes, never delete without explicit instruction).

---

## 7. THE AUTH QUESTION: what does a self-serve owner actually need in 2026?

This is the part most third-party write-ups get wrong, and the two Meta docs involved genuinely conflict in terminology. Here is the reconciled position with sources.

### Does `ads_management` require App Review? **No — not for your own ad accounts.**

From Meta's Marketing API authorization doc (https://developers.facebook.com/docs/marketing-api/overview/authorization), verbatim:

> "If your app is managing other people's ad accounts, you need advanced access to the `ads_read` and/or `ads_management` permissions."

> "If your app is only managing your ad account, standard access to the `ads_read` and `ads_management` permissions are sufficient."

Standard access is granted automatically. **So: a Meta app you own, in development mode, calling against an ad account you own, with `ads_management`, requires no App Review and no business verification to perform writes.** That directly answers the sub-question — dev mode plus own account IS sufficient for read and write.

### The real constraint is not review, it is the rate tier

From https://developers.facebook.com/docs/marketing-api/overview/rate-limiting — note that Meta has **renamed the tiers**, which is the source of nearly all the confusion in secondary sources:

- old "Standard Access" is now **Limited Access** (the development tier)
- old "Advanced Access" is now **Full Access**

| Tier | Max score | Decay | Block | Notes |
|---|---:|---|---|---|
| Limited (dev) | 60 points | 300s | 300s | read = 1 pt, write = 3 pts |
| Full | 9,000 points | 300s | 60s | same scoring |

Business-use-case quota for `ads_management`: **300/hour on the dev tier vs 100,000/hour on Full**, plus 40 points per active ad in both.

A 60-point budget with writes costing 3 points each is roughly **20 write calls per 5-minute window**. That is fine for a human-paced agent session tweaking budgets and launching a campaign. It is not fine for a bulk build of dozens of ad sets and creatives in one go, which will hit the wall and get blocked for 5 minutes.

Upgrading to Full is **not an App Review of your permissions** — it is a tier upgrade request, gated on usage:

- 500+ Marketing API calls in the last 15 days
- error rate under 15% across the last 500 calls
- then request the upgrade in the App Review dashboard

So the path is self-clearing: use it normally for a couple of weeks, then upgrade. Plan for the dev-tier ceiling in the interim.

**Terminology conflict, flagged:** the authorization doc still says "standard access ... sufficient", while the rate-limiting doc says "Standard Access is now called Limited Access". These are consistent once you separate *permission* access levels from *rate* tiers, but the docs have not been harmonised and secondary sources routinely conflate them. Read every "standard access" claim about Meta ads with this ambiguity in mind.

### Token expiry reality

- **User access token (short-lived):** ~1–2 hours. Useless for automation.
- **Long-lived user token:** ~60 days, obtained by exchanging a short-lived token. Meta documents that apps with Marketing API standard access receive long-lived tokens that do not expire purely on time, but they remain invalidatable by password change, permission revocation, or security events. **Do not build on this** — the 60-day behaviour is the safe assumption.
- **System User token:** Meta's own wording is that it **does not expire**, "so it can be used in long-running scripts or services that need to access the Marketing API". Revocable manually. **This is the correct choice for any persistent Claude skill or automation.** No refresh logic, no 60-day breakage.

Caveat: the system-user doc page I fetched (https://developers.facebook.com/docs/marketing-api/system-users) does not itself state the expiry behaviour; the non-expiry statement comes from Meta's access-token documentation and is widely corroborated. It is well established but worth confirming on the token debugger once minted (a system user token shows `Expires: Never`).

### Concrete steps: System User token with full read+write

One-time, roughly 15 minutes, mostly clicking. An agent can prepare and verify but **cannot complete this unattended** — it requires a logged-in Business Manager session and deliberate human consent, which is appropriate for a credential granting spend authority.

1. **Create a Meta app.** https://developers.facebook.com/apps — type "Business". Leave it in Development mode; per the authorization doc that is sufficient for your own accounts. Note the App ID and App Secret.
2. **Open Business Settings.** https://business.facebook.com/settings — confirm the ad account you want to manage is owned by this Business (not just shared to your personal profile). If it is not, claim or transfer it first; a system user cannot be assigned an asset the Business does not own.
3. **Add the app to the Business.** Business Settings → Accounts → Apps → Add → enter the App ID.
4. **Create the System User.** Business Settings → Users → System Users → Add. Choose **Admin** system user for unrestricted management. Docs: https://developers.facebook.com/docs/marketing-api/system-users
5. **Assign assets to the system user.** Select it → Add Assets → Ad Accounts → pick the account → enable **Manage campaigns** (full control, not "View performance" which is read-only). Repeat for Pages and Product Catalogs if you need page-backed creatives or catalog ads. Asset-permission guide: https://developers.facebook.com/docs/marketing-api/business-asset-management
6. **Generate the token.** On the system user → Generate New Token → select your app → tick **`ads_management`**, **`ads_read`**, **`business_management`**, plus `catalog_management` and `pages_read_engagement`/`pages_manage_ads` if relevant. Copy it immediately; it is shown once.
7. **Verify.** Paste into https://developers.facebook.com/tools/debug/accesstoken/ and confirm `Expires: Never` and that the scopes list includes `ads_management`. Then a live smoke test:
   ```
   curl -s "https://graph.facebook.com/v23.0/me/adaccounts?fields=name,account_status,currency&access_token=$FB_TOKEN"
   ```
   A write smoke test that is safe to run: create a campaign with `status=PAUSED`, confirm the ID comes back, then delete it.
8. **Store it properly.** Per workspace policy: macOS keychain, or a gitignored `.env` inside the repo it was provisioned for. Never commit, never paste into chat.

Reference for API version currency: https://developers.facebook.com/docs/graph-api/changelog — pin an explicit version in the skill rather than defaulting, since Meta deprecates versions on a ~2-year cycle and an unpinned skill will break silently.

---

## 8. Scored comparison

| Option | Write | Auth burden | Third party in path | Tool ceiling | Verdict |
|---|---|---|---|---|---|
| **Official Meta MCP** | Full (`ads_management` scope confirmed) | Lowest: browser OAuth only | None | Fixed tool list; count unverified | **Primary**, if enabled on the account |
| **Raw Graph API skill + System User token** | Full, entire API | Medium: one-time 15-min BM setup | None | **None — whole API** | **Runner-up / fallback**, and best for Claude Code |
| Composio Metaads | Full | Medium: own Meta app + Composio | Yes (credential custody) | Curated but broad | Only if you want managed token refresh |
| pipeboard-co MCP | Full | Low | **Yes — SaaS proxy, paid tiers, unclear licence** | Fixed | Rejected on "no artificial restrictions" |
| brijr/meta-mcp | Likely | High: deploy Cloudflare Worker + own app | None | Fixed, 39 tools | Fork candidate only |
| gomarble MCP | **None** | Low | None | Read only | Great reporting, fails the brief |
| Zapier MCP | Leads/audiences only | Low | Yes | Very narrow | Rejected |
| Supermetrics (directory) | Contradictory claims | Low | Yes | Reporting-shaped | Rejected pending test |
| Business SDKs | Full | Same as raw Graph | None | None | Good base library, not a connector |

---

## 9. Recommendation

**Do this, in order:**

1. **Try the official connector first.** In Claude Desktop/web, Settings → Connectors → Add custom connector → `https://mcp.facebook.com/ads`, complete the Meta Business OAuth, granting `ads_management`. Five minutes, zero setup cost, and it either works or it does not. If it works, it is unambiguously the best answer: first-party, no proxy, no app, no review, no token to rotate.
2. **In parallel, mint the System User token anyway** (section 7). It costs 15 minutes once, it never expires, and it is the foundation for everything else — the Claude Code skill, any n8n work, any future automation. It is not wasted effort even if the official MCP works, because Claude Code composing raw Graph calls has no tool-surface ceiling, which matters for bulk builds and for anything the official server's fixed tool list omits.
3. **If `is_ads_mcp_enabled` blocks you**, the thin skill becomes the primary and there is no meaningful loss. Do not fall back to Pipeboard or another SaaS proxy just to get a connector — you would be paying a vendor and handing over ad-spend credentials to work around a rollout flag, when you can call the same API directly with a token you own.

**The split that actually makes sense**: official MCP in Claude Desktop for conversational analysis and light changes; own skill over Graph API in Claude Code for deterministic bulk work. That mirrors the MCP-for-analysis / CLI-for-execution division the secondary sources describe, except the execution half is something you own rather than a CLI Meta does not appear to have shipped.

---

## 10. Open items and staleness flags

- **UNVERIFIED — the `is_ads_mcp_enabled` rollout gate.** Third-party sources only. Resolvable in minutes by attempting the install. This is the highest-value unknown.
- **UNVERIFIED — the official MCP's tool list.** No primary doc found; `developers.facebook.com/docs/marketing-api/ai-connectors/` 404s. The "29 tools" figure is blog-sourced. Enumerate `tools/list` after authenticating to get the truth.
- **LIKELY FALSE — the "official Meta CLI" (`@meta/ads-cli`).** Registry-checked, does not exist. Widely repeated regardless.
- **UNVERIFIED — the 2026-04-29 launch date** and Meta's own announcement page.
- **CONFLICT — Meta's access-tier terminology** across the authorization and rate-limiting docs (section 7). Reconciled above, but treat any third-party claim about "standard access" sceptically.
- **UNVERIFIED — Supermetrics' write capability** (directory badge says Read, page copy says create/update campaigns).
- **UNVERIFIED — Pipeboard's licence terms** (`NOASSERTION`) and whether write sits behind a paid tier.
- **NOT ENUMERATED** — Anthropic's connector directory beyond page 1 of 17.
- **NOT VERIFIED** — whether the target ad account is Business-owned (prerequisite for step 2/5 of the auth path). Check before starting.

---
---

# CORRECTED + HIGH-FIDELITY PASS — 2026-07-28

**This section supersedes sections 1, 5, 8 and 9 above where they conflict.** Two claims in the earlier pass were WRONG and are corrected here with primary sources:

1. **"No official Meta Ads CLI exists" — FALSE.** It exists, it is `meta-ads` on **PyPI** (not npm), and it is the single most capable option for Claude Code. The earlier npm-registry check was correct as far as it went (`@meta/ads-cli` genuinely does not exist) but the conclusion drawn from it was wrong. Meta shipped a **Python** CLI.
2. **"29 tools" — FALSE/STALE.** The official MCP server documents **~93 tools** across 7 categories. The "29" figure comes from SEO blogs describing the April 2026 launch state.

The earlier 404 happened because the docs live at `developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/`, **not** `/docs/marketing-api/`.

## What was actually fetched this pass

Primary sources, all retrieved 2026-07-28:

- Live protocol probes against `https://mcp.facebook.com/ads` (curl): initialize, `tools/list`, `GET`, `/.well-known/oauth-protected-resource/ads`, `/.well-known/oauth-authorization-server/ads`, `/.well-known/register/ads`
- `https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/{ads-mcp-server-overview, ads-mcp-server-get-started, ads-mcp-server-tools-*}` — all 7 tool pages (via Playwright; curl is bot-blocked with HTTP 400, and WebFetch truncates these pages)
- `.../ads-ai-connectors/ads-cli/{ads-cli-overview, command-reference, setup/get-started, setup/configuration, insights, tutorials-and-recipes}`
- `https://www.facebook.com/business/news/meta-ads-ai-connectors` (launch announcement)
- `https://developers.facebook.com/blog/post/2026/04/29/introducing-ads-cli` — **the page that proves the CLI is Python**: "Ads CLI requires Python 3.12+ and pip/uv"
- PyPI JSON API for `meta-ads`, `meta-ads-cli`, `facebook-business`; npm registry for `@meta/ads-cli`, `@facebook/ads-cli`, `meta-ads-cli`, `facebook-nodejs-business-sdk`
- **The official CLI installed and executed locally** (`uv venv --python 3.13`, `meta-ads==1.1.0`) and its entire `--help` tree dumped. Every CLI claim below is from the running binary, not docs.

---

## A) OFFICIAL META MCP SERVER — REAL TOOL LIST

**Server URL:** `https://mcp.facebook.com/ads`. Docs last updated **Jul 14, 2026**.

### Auth — two methods, both documented

- **OAuth** via Facebook Login for Business (browser consent).
- **User access token** as `Authorization: Bearer <TOKEN>` — Meta documents this explicitly for "programmatic setups", with a literal `curl ... tools/list` example.

Protocol facts confirmed by probe:
- `authorization_endpoint`: `https://www.facebook.com/v25.0/dialog/oauth`, `token_endpoint`: `https://graph.facebook.com/v25.0/oauth/access_token`, PKCE S256, `token_endpoint_auth_methods_supported: ["none"]`.
- Scopes: `ads_management ads_read catalog_management business_management pages_show_list instagram_basic ads_mcp_management`.
- **Dynamic client registration is CLOSED**: `POST /.well-known/register/ads` returns `{"error":"invalid_client_metadata","error_description":"Dynamic registration is not available for this client."}`. **You must supply your own Meta App ID as the OAuth client_id.** This contradicts the widely repeated "no developer app needed" claim for the developer path. Meta's own get-started page says owning an app is not a prerequisite only if you use the no-app Business-Help-Centre route.

### Meta's documented Claude Code command (verbatim, primary source)

```
claude mcp add --transport http --client-id <META_APP_ID> meta-ads https://mcp.facebook.com/ads
```

This is on Meta's get-started page. **Remote HTTP MCP is officially supported in Claude Code CLI**, not Desktop-only.

### The real tool inventory — ~93 tools, 7 categories

**Ad creation and management (30).** Meta's note: "Write tools create entities in a paused state; your AI client asks for confirmation before activation."

| Tool | R/W |
|---|---|
| `ads_get_ad_accounts` | R |
| `ads_get_ad_account_pages` | R |
| `ads_get_pages_for_business` | R |
| `ads_get_user_pages` | R |
| `ads_get_field_context` | R |
| `ads_create_campaign` | **W** |
| `ads_create_ad_set` | **W** |
| `ads_create_ad` | **W** |
| `ads_update_entity` | **W** (campaign/adset/ad — this is the budget-change tool) |
| `ads_activate_entity` | **W** (paused → active) |
| `ads_create_creative` | **W** — *single-image link ad creative only* |
| `ads_get_creatives` | R |
| `ads_get_creative_ads` | R |
| `ads_get_ad_images` | R |
| `ads_get_ad_videos` | R |
| `ads_get_ad_preview` | R (renders placement preview) |
| `ads_get_ad_entities` | R |
| `ads_library_search` | R (public Ad Library) |
| `ads_get_ig_accounts` | R |
| `ads_get_ig_media` | R |
| `ads_boost_ig_post` | **W** |
| `ads_get_ad_account_custom_audiences` | R |
| `ads_get_custom_audience` | R |
| `ads_get_custom_audience_adsets` | R |
| `ads_create_custom_audience` | **W** (customer file, website, lookalike, app, engagement, offline) |
| `ads_update_custom_audience` | **W** |
| `ads_update_custom_audience_users` | **W** (hashed PII upload) |
| `ads_delete_custom_audience` | **W** |

**Comprehensive reporting (7):** `ads_get_ad_entities` (R, the primary reporting tool — "filtering, breakdowns, sorting, and date ranges"), `ads_get_opportunity_score`, `ads_insights_advertiser_context`, `ads_insights_anomaly_signal`, `ads_insights_auction_ranking_benchmarks`, `ads_insights_industry_benchmark`, `ads_insights_performance_trend` — all R.

**Catalog creation and management (34):** `ads_catalog_create`, `_update_catalog`, `_get_catalogs`, `_get_details`, `_get_diagnostics`, `_get_dynamic_ads_health`, `_get_data_sources`, `_get_product_details`, `_product_create`, `_update_product`, `_delete_product`, `_get_product_product_sets`, `_search_product`, `_create_product_set`, `_update_product_set`, `_get_product_sets`, `_get_product_set_details`, `_get_product_set_products`, `_product_set_delete`, `_create_product_feed`, `_update_product_feed`, `_get_product_feed_details`, `_create_product_feed_upload_session`, `_get_product_feed_upload_sessions`, `_product_feed_delete`, `_create_feed_rule`, `_get_feed_rules`, `_product_feed_delete_rule`, `_event_source_get`, `_event_source_get_catalogs`, `_event_source_get_health`, `_event_source_get_recommendations`, `_event_source_connect`, `_event_source_disconnect`. Full CRUD.

**Signals and datasets (13):** `ads_get_datasets`, `ads_get_dataset_details`, `ads_get_dataset_stats`, `ads_get_dataset_quality`, `ads_pixel_event_{read,create,update,delete}`, `ads_pixel_parameter_{read,create,update,delete}`, `ads_get_customconversions`.

**A/B tests and lift studies (7):** `ads_experiment_list_tests`, `_check_eligibility`, `_abtest_create_test`, `_abtest_get_test`, `_abtest_update_test`, `_lift_create_test`, `_lift_get_test`.

**Help and troubleshooting (2):** `ads_get_errors`, `ads_get_help_article`.

**Activity logs (1):** `ads_account_get_activity_logs`.

*(Category pages were scraped by same-origin fetch + regex on `ads_[a-z_]+`; a constant ~32-token nav/sidebar set common to all pages was subtracted. The 30-tool ad-management list and the 7-tool reporting list are from rendered page text and are exact. The other five counts are high-confidence but derived.)*

### Direct answers to the A) questions

| Question | Answer |
|---|---|
| Create campaign / ad set / ad? | **YES** — `ads_create_campaign`, `ads_create_ad_set`, `ads_create_ad`. Always created PAUSED. |
| Upload/attach creative? | **PARTIAL.** `ads_create_creative` is documented as **single-image link ad only**. `ads_get_ad_images`/`ads_get_ad_videos` are READ-ONLY — **there is no image or video upload tool.** No carousel, no DCO, no video creative. This is the MCP's single biggest capability hole. |
| Change budgets? | **YES** — via `ads_update_entity`. |
| Pause / resume? | **YES** — `ads_activate_entity` to resume; `ads_update_entity` to pause. |
| Manage audiences? | **YES, fully** — create/update/delete custom audiences incl. lookalikes, plus hashed-PII list membership. |
| Insights with arbitrary breakdowns? | **UNVERIFIED at parameter level.** `ads_get_ad_entities` is documented as supporting "breakdowns" but the enum is not published. Cannot confirm all 89 API breakdowns are reachable. Requires an authenticated `tools/list` to settle. |

### Still unverified about the MCP

- **The exact JSON schema of every tool** (parameter enums, whether `ads_update_entity` accepts arbitrary field names). Settle with the documented curl: `curl -X POST https://mcp.facebook.com/ads -H "Authorization: Bearer <TOKEN>" --data-raw '{"jsonrpc":"2.0","method":"tools/list","id":1}'`. This needs 5 minutes and a token.
- **`is_ads_mcp_enabled`.** **NOT documented anywhere on developers.facebook.com.** I searched the entire `ads-ai-connectors` section; the overview, get-started and all 7 tool pages contain no eligibility gate, no allowlist, and no such flag. Meta's documented gate is instead: add the **"Create & manage ads with ads MCP server" use case** to your Meta app. The user reports the flag is real and often false — I can neither confirm nor refute that from Meta's docs, and note only that Meta documents no way to check or request it. Treat it as real-but-undocumented.

---

## B) THE CLI QUESTION — RESOLVED: THE OFFICIAL CLI IS REAL

### `meta-ads` on PyPI — OFFICIAL

- **Install:** `pip install meta-ads` (Meta's docs also show `uv sync` / `uv run meta`)
- **Binary:** `meta`
- **Current version: 1.1.0, published 2026-06-17.** Earlier: 1.0.0 and 1.0.1 both on 2026-04-29 (matches the announced launch date — that date is now CONFIRMED).
- **Ownership proof:** package description reads "Official CLI for the Meta Marketing API"; licence field: "Copyright (c) Meta Platforms, Inc. and affiliates. All rights reserved."
- **Dependencies:** `click>=8.1`, **`facebook-business>=20.0`**, `python-dotenv>=1.0`, `rich>=13.0`. It is a Click wrapper over Meta's own Python SDK; my install pulled `facebook_business 25.0.3` (Marketing API **v25.0**).
- **Requires Python >=3.12. Wheels are cp312 and cp313 ONLY — there is no cp314 wheel and no sdist.** My first install attempt failed on Python 3.14 with "No matching distribution found". Real gotcha for a skill: pin 3.12/3.13.
- **Platforms:** macOS arm64, manylinux x86_64 + aarch64, musllinux x86_64 + aarch64. **No Windows wheel** (would need WSL). Verified installed and running on macOS arm64.

### Auth — and this is the decisive fact

**System user access token via `ACCESS_TOKEN` env var or `.env`. There is no browser, ever.** Confirmed on the live binary:

```
$ meta auth --help
Commands:
  status  Check current authentication status.
```

`meta auth` has **only** `status` — there is **no `meta auth login`** (blogs claiming otherwise are wrong; note Meta's own command-reference page describes `meta auth` as "Save system user access token", which does not match the shipped v1.1.0 binary — docs are slightly ahead of or behind the build).

Config precedence: CLI flags > env vars > project `.env` > `~/.config/meta/` (XDG).

### Full command surface — from the running binary (54 leaf commands)

| Group | Subcommands |
|---|---|
| `meta auth` | status |
| `meta ads adaccount` | list, get, current |
| `meta ads campaign` | list, get, **create, update, delete** |
| `meta ads adset` | list, get, **create, update, delete** |
| `meta ads ad` | list, get, **create, update, delete** |
| `meta ads creative` | list, get, **create, update, delete** |
| `meta ads catalog` | list, get, **create, update, delete** |
| `meta ads product-feed` | list, get, **create, update, delete** |
| `meta ads product-item` | list, get, **create, update, delete** |
| `meta ads product-set` | list, get, **create, update, delete** |
| `meta ads dataset` | list, get, **create, connect, disconnect, assign-user** |
| `meta ads page` | list, get |
| `meta ads insights` | get |
| `meta ads guidance` | list |
| `meta ads study` | list |

Note `product-feed`, `product-item`, `product-set`, `guidance` and `study` are **in the binary but missing from Meta's own command-reference page** — the shipped tool is broader than the published docs.

### Where the CLI beats the MCP: creative

`meta ads creative create` is far richer than `ads_create_creative`. From `--help`:

- **Local file upload**: `--image ./banner.jpg`, `--video ./promo.mp4` (jpg/png/gif/bmp/webp; mp4/mov/avi/mkv/wmv). The MCP has no upload tool at all.
- **DCO**: `--images` (×10), `--titles`/`--bodies`/`--descriptions`/`--call-to-actions` (×5 each), `--ad-format SINGLE_IMAGE|SINGLE_VIDEO|CAROUSEL|AUTOMATIC_FORMAT`
- **Boost existing post**: `--object-story-id`, `--source-instagram-media-id`, `--instagram-permalink-url`
- **Catalog/DPA**: `--product-set-id`
- **Raw JSON escape hatches**: `--object-story-spec @oss.json` (carousels, deep links), `--asset-feed-spec @feed.json`, `--degrees-of-freedom-spec @dof.json` (Advantage+ creative enhancements)
- Compliance: `--authorization-category POLITICAL|...`, `--url-tags`, `--applink-treatment`

Ad set create likewise has `--targeting @spec.json` and `--promoted-object @obj.json` raw passthrough, plus `--advantage-audience`, `--dynamic-creative`, `--attribution-spec`, `--dsa-beneficiary`/`--dsa-payor` (EU DSA), `--bid-strategy`, `--pacing-type`.

**Critically, `--fields` on campaign/adset/ad list/get/create is passed straight to the Marketing API** ("names are passed straight to the API"), so reads are not capped by the CLI's flag set.

### Where the CLI LOSES to the MCP

- **No custom audience commands at all.** `grep` over the installed package confirms audiences exist only inside the bundled SDK, not the CLI surface. You can *target* an existing audience via `--targeting @json`, but you cannot create, update, delete, or upload members to one. The MCP has 7 audience tools.
- **No A/B test / lift study creation** (`meta ads study` is `list` only; MCP can create both).
- **No Ad Library search, no ad preview rendering, no opportunity score, no benchmark/anomaly insights, no activity logs, no help-article search.**
- **Insights breakdowns are hard-capped at 8**: `age, gender, country, publisher_platform, device_platform, platform_position, impression_device`. The Marketing API exposes **89** breakdowns (`region`, `dma`, `zip`, `product_id`, `hourly_stats_aggregated_by_advertiser_time_zone`, all the `*_asset` creative breakdowns, etc.) plus **16 `action_breakdowns`** (`action_type`, `action_device`, …) which the CLI does not expose **at all**. Fields are fine (`--fields` accepts "any valid Meta Insights API field"; 220 exist) — it is specifically the breakdown dimension that is gated.
- **No `--level`, no `--filtering`, no async report jobs (`adreportrun`), no cursor pagination** (only `--limit`, default 50).
- **No bulk operations.** Confirmed on both the binary and Meta's docs. Meta's recommended pattern is shell looping: `meta --output json ads campaign list | jq -r '.[].id'` then a `for` loop.

### Non-interactive suitability — excellent

Meta documents a "Scripts and automation" section: `--no-input` and `--force` suppress all prompts, `-o json` gives structured output, and there are **documented exit codes** (e.g. `3` = no results). This is exactly the shape Claude Code wants.

### Community CLIs (all checked against the registries)

| Package | Registry | Status |
|---|---|---|
| `@meta/ads-cli`, `@facebook/ads-cli`, `@meta/ads` | npm | **Do not exist** — `{"error":"Not found"}`. The blog claim `npm install -g @meta/ads-cli` is fabricated. |
| `meta-ads-cli` | npm 0.1.0, 2026-01-05 | Third party (giorgioliapakis), self-described "Unofficial". Stale. |
| `meta-ads-cli` | PyPI 0.2.0, 2026-06-17 | attainmentlabs. Third party. |
| `cli-meta-ads` | npm | No published version; empty. |
| `jon-egbdigital/meta-ads-cli` | GitHub | Explicitly "Replaces the abandoned PyPI meta-ads-cli"; pinned to v21. Third party. |

None are worth using now that the official one exists.

### `facebook-business` (Python SDK) and `facebook-nodejs-business-sdk`

- **`facebook-business` (PyPI): v25.0.3, released 2026-07-17.** Actively maintained, tracks Marketing API v25.0. **Ships NO CLI entrypoint** — the dist-info has no `entry_points.txt` and no `console_scripts`. It is a library only.
- **`facebook-nodejs-business-sdk` (npm): v24.0.1, released 2025-11-21.** Maintained by Meta staff accounts (`vicdus`, `codytwinton`). **No `bin` field — no CLI.** Note it is a **full major version behind** the Python SDK (v24 vs v25) and 8 months staler.
- **Is a thin custom CLI over the Graph API sane for a Claude skill?** It *was* the right answer before this pass. It no longer is: `meta-ads` already is that CLI, written by Meta, over Meta's own SDK. The sane shape now is **official CLI as the primary verb set + raw `curl`/`httpx` Graph calls as the documented escape hatch** for the gaps (audiences, exotic breakdowns, bulk). Writing a whole CLI from scratch is now redundant work.

---

## C) RAW GRAPH API CEILING — QUANTIFIED

Measured against the installed `facebook_business` 25.0.3 (Meta's own SDK, so this is Meta's own object map):

- **990 node classes** in `facebook_business/adobjects/`.
- **`AdAccount` alone exposes 126 edge methods** (`get_*` / `create_*` / `delete_*`).
- **`AdsInsights`: 220 fields, 89 breakdowns, 16 action_breakdowns.**

Main Marketing API nodes, all present and all reachable by raw HTTP but **not** by the CLI: `campaign`, `adset`, `ad`, `adcreative`, `adaccount`, `customaudience`, `savedaudience`, `adsinsights`, `adreportrun` (async reports), `adimage`, `advideo`, `adlabel`, `adrule` (automated rules), `adactivity`, `productcatalog`, `adaccountadvolume`.

**What raw Graph does that no fixed tool list structurally can:**

1. **`adrule` — automated rules.** Server-side "if CPA > $X then pause" automations that keep running when Claude is not. Absent from both the CLI and the MCP.
2. **`adlabel`** — labels for organising/reporting at scale. Absent from both.
3. **`adreportrun`** — async report jobs for large insight pulls that time out synchronously. Absent from both.
4. **`/act_X/asyncbatch` and the `/` batch endpoint** — up to 50 sub-requests in one HTTP call, which is the real answer to bulk. Absent from both.
5. **The 81 breakdowns and all 16 action_breakdowns the CLI omits.**
6. **`adimage` / `advideo` direct upload endpoints** — the MCP cannot upload media at all.
7. **Version pinning and forward compatibility.** New v26/v27 fields work the day they ship; a fixed tool list works when Meta redeploys it.
8. **Arbitrary field selection and nested field expansion** on any node.

The cost is unchanged from section 7 above: you own correctness, and there are no built-in guardrails.

---

## D) HEAD-TO-HEAD MATRIX (Ads CLI now a first-class column)

| Capability | **Official Ads CLI** (`meta-ads` 1.1.0) | **Official MCP** (`mcp.facebook.com/ads`) | **Raw Graph API skill** | **facebook-business SDK** | **Community MCP** (pipeboard / gomarble) |
|---|---|---|---|---|---|
| Auth setup effort | System user token + `ACCESS_TOKEN` env. ~15 min one-time in Business Suite. No browser. | Browser OAuth (needs your own Meta App ID as client_id — **DCR is closed**) OR bearer user token | Same system user token as CLI | Same token | pipeboard: their OAuth, ~2 min. gomarble: `--fb-token` |
| Campaign CRUD | **Full** — create/get/list/update/delete | **Create + update + activate.** No delete tool documented | **Full** `/act_X/campaigns` | Full | pipeboard full; gomarble read-only |
| Ad set CRUD | **Full**, incl. `--targeting @json` raw spec | Create + update. No delete | **Full** | Full | pipeboard full; gomarble none |
| Ad CRUD | **Full** | Create + update. No delete | **Full** | Full | pipeboard full; gomarble none |
| Creative upload | **Best in class** — local image/video upload, DCO (10 imgs/5 titles), carousel + Advantage+ via raw `object_story_spec`/`asset_feed_spec`/`degrees_of_freedom_spec`, IG/FB post boost, DPA | **Weak** — `ads_create_creative` is single-image link only; `ads_get_ad_images`/`_videos` are READ. **No upload tool.** `ads_boost_ig_post` is the one bright spot | **Full** — `/adimages`, `/advideos`, any creative shape | Full | pipeboard has `upload_ad_image`; gomarble none |
| Budget mgmt | **Full** — `--daily-budget`/`--lifetime-budget`/`--spend-cap`/`--bid-strategy` on campaign+adset create & update | **Yes** via `ads_update_entity` | **Full** | Full | pipeboard yes; gomarble no |
| Audiences | **NONE.** No audience commands. Can only target an existing one via `--targeting @json` | **Full — 7 tools** incl. create (customer file/website/lookalike/engagement/offline), update, delete, hashed-PII membership | **Full** — `customaudience`, `savedaudience`, 19 subtypes | Full | pipeboard has create_custom_audience/lookalike; gomarble none |
| Insights / reporting | Good fields (any of 220 via `--fields`), presets + custom dates, daily/weekly/monthly, sort, limit. **Only 8 of 89 breakdowns. Zero action_breakdowns. No `--level`, no `--filtering`.** | `ads_get_ad_entities` + 6 analysis tools (opportunity score, industry benchmark, anomaly, auction ranking, perf trend) unavailable anywhere else. Breakdown enum **unverified** | **220 fields, 89 breakdowns, 16 action_breakdowns, `--filtering`, `adreportrun` async** | Same as raw | gomarble strong read; pipeboard good |
| Bulk operations | **None.** Meta's own answer is shell loops + `jq` | **None documented** | **Yes** — `/asyncbatch` + batch endpoint, 50 sub-requests/call | Yes (`FacebookAdsApiBatch`) | Unverified |
| Rate limits | Your app's Marketing API tier (Limited 60 pts / Full 9,000 pts — see §7) | Meta-hosted; **no published limit.** Third parties claim it bypasses the dev-tier ceiling — UNVERIFIED | Your app's tier | Your app's tier | pipeboard adds its own SaaS quota on top |
| Multi-account | **Yes** — `--ad-account-id` per command, or `AD_ACCOUNT_ID` env | **Yes** — `ads_get_ad_accounts`; account id is a tool param | Yes, trivially | Yes | pipeboard yes |
| Claude Code CLI | **Native.** It is a shell binary — the single best fit | **Yes, documented by Meta**: `claude mcp add --transport http --client-id <APP_ID> meta-ads https://mcp.facebook.com/ads` | **Native** (curl/httpx in a skill) | Native | Yes |
| Claude Code inside Claude Desktop | **Yes** — same binary, same `~/.config/meta/`, same shell | **Yes** — remote MCP is Desktop's native case | **Yes** — identical | Yes | Yes |
| claude.ai chat (web) | **No.** No shell in the browser | **Yes** — this is the only option here. Custom Connector, OAuth | **No** | No | pipeboard yes (remote URL) |
| Token expiry / maintenance | **System user token: never expires.** Zero maintenance | OAuth tokens refresh automatically (`refresh_token` grant advertised); bearer user tokens expire ~60 days | Never expires | Never expires | pipeboard manages refresh for you (and holds your creds) |
| Ceiling on future capability | Medium-high. Raw-JSON escape hatches + `--fields` passthrough soften it, but audiences/breakdowns/bulk are hard walls | **Fixed at ~93 tools.** Meta can extend it; you cannot | **None — the entire 990-node API** | **None** | Fixed, and vendor-controlled |
| Third party in credential path | **No** | **No** | **No** | **No** | **Yes** (pipeboard); no (gomarble, local) |
| Platform support | macOS arm64, Linux x86_64/aarch64 (glibc+musl). **No Windows wheel. Python 3.12/3.13 only — no 3.14** | Any MCP client | Anywhere | Anywhere | Varies |

---

## E) VERDICT — maximum capability, no artificial restrictions, identical in Claude Code CLI and Claude Code inside Claude Desktop

**Winner: the official Ads CLI (`pip install meta-ads`) as the primary surface, with raw Graph API calls as a documented escape hatch, both driven by one system user token from a single skill.**

**Margin: decisive against the MCP on the stated criterion, but not on capability alone — it wins on the criterion, and the raw-Graph hatch is what closes the capability gap.**

Reasoning, in order of weight:

1. **"Identically in Claude Code CLI and Claude Code inside Claude Desktop" is the constraint that settles it.** Both are the same Claude Code process with the same shell and the same `$HOME`. A token in `~/.config/meta/` or a project `.env` is byte-identical in both. Remote MCP *does* work in both (Meta publishes the `claude mcp add` command, so this is now confirmed rather than assumed), but MCP auth is client-held: OAuth consent, connector state, and token storage live in whichever client authorised it, so "identical" requires re-authorising per client. The token file is genuinely portable; the OAuth session is genuinely not. On this specific criterion the CLI wins outright.

2. **"No artificial restrictions" cuts against the MCP twice.** Its tool list is fixed at ~93 and you cannot extend it. And its creative story is genuinely crippled: no image upload, no video upload, single-image link creatives only. For anyone who actually launches ads rather than reading about them, that is the restriction that bites hardest, and the CLI does not have it.

3. **The CLI is not a toy.** 54 leaf commands, full CRUD on campaign/adset/ad/creative/catalog/feeds/sets/items, local media upload, DCO, and three raw-JSON escape hatches (`--object-story-spec`, `--asset-feed-spec`, `--degrees-of-freedom-spec`) plus `--targeting`/`--promoted-object` passthrough and `--fields` passthrough. Meta explicitly designed it for non-interactive use (`--no-input`, `--force`, `-o json`, documented exit codes).

4. **Its two real holes are exactly what raw Graph fills, using the same token.** Audiences (`/act_X/customaudiences`), the missing 81 breakdowns and all action_breakdowns, `adrule`, `adlabel`, `adreportrun`, and `/asyncbatch` bulk. This is a one-line addition to a skill file, not a second integration — same credential, same host, no extra auth. That combination has **no capability ceiling at all**, which nothing else on the list can claim.

**Where the MCP still earns a slot, and it genuinely does:** it is the *only* option that works in claude.ai in the browser, and it has seven analysis tools with no API equivalent — `ads_get_opportunity_score`, `ads_insights_industry_benchmark`, `ads_insights_auction_ranking_benchmarks`, `ads_insights_anomaly_signal`, `ads_insights_performance_trend`, `ads_get_help_article`, `ads_library_search`. Those are Meta-internal signals, not Graph endpoints; you cannot rebuild them. It also has the better audience surface. Adding it costs one command and conflicts with nothing.

**Recommended shape: run both.**
- `pip install meta-ads` (Python 3.12 or 3.13) + system user token → primary execution path in Claude Code, identical in CLI and Desktop, zero token maintenance.
- Skill documents raw `curl` against `graph.facebook.com/v25.0` with the same `$ACCESS_TOKEN` for audiences, exotic breakdowns, `adrule`, and batch.
- `claude mcp add --transport http --client-id <META_APP_ID> meta-ads https://mcp.facebook.com/ads` for the benchmark/diagnostic tools and for claude.ai browser sessions.

**Explicitly rejected:** every third-party MCP. pipeboard puts a SaaS proxy in the credential path for a strictly smaller surface than the official CLI; gomarble is read-only; the community CLIs are unofficial and stale. There is no longer any reason to consider them.

## Remaining unknowns (stated, not smoothed)

- **The MCP's real `tools/list` JSON** — parameter schemas, and whether `ads_get_ad_entities` accepts all 89 breakdowns. Resolvable in 5 minutes with a token and Meta's own documented curl. My ~93 count is scraped from docs, not from a live authenticated session; the two exact category lists (30 and 7) are reliable, the other five are derived.
- **`is_ads_mcp_enabled`** — the user says it is real and often false. I confirmed it appears **nowhere** in Meta's `ads-ai-connectors` docs, and Meta documents no way to check or request it. Unresolved.
- **Whether the MCP bypasses Marketing API rate tiers.** Claimed by third parties, unpublished by Meta.
- **The `meta auth` discrepancy** — Meta's command-reference says it saves a token; shipped v1.1.0 only has `meta auth status`. Minor, but it means the docs and the build are not in lockstep, so verify behaviour against the binary rather than the page.
- **Windows** — no wheel; assume WSL. Not tested.

---

# FOLLOW-UP — 2026-07-28

Authority: the running `meta-ads==1.1.0` binary (reinstalled, live-probed against Meta with a deliberately invalid token) plus primary Meta docs.

## 1. CREATIVE UPLOAD — the CLI DOES upload images AND videos. Verified live.

### Evidence, strongest first

**(a) Live HTTP probe.** With `ACCESS_TOKEN=FAKE_TOKEN_FOR_PROBE` and a real 1×1 PNG / a real ffmpeg-generated MP4:

```
$ meta --debug --no-input ads creative create --name probe --image ./t.png \
    --page-id 123 --body b --link-url https://example.com
WARNING:root:`remote_create` is being deprecated, please update your code with new function.
Error: Image upload failed (190): Invalid OAuth access token data.

$ meta --debug --no-input ads creative create --name probe --video ./t.mp4 ...
Uploading video t.mp4...
WARNING:root:parent_id is being deprecated.
Error: Video upload failed (190): Invalid OAuth access token data.
```

Both reached Meta and failed **only** on token validity (Graph error code 190). The upload code path is real and executes. `remote_create` is the `facebook_business` SDK method that POSTs to `/act_<ID>/adimages`; the video path is the `/act_<ID>/advideos` resumable upload (hence the multiple `parent_id` warnings).

**(b) Symbols in the compiled binary.** `meta/commands/creative.cpython-313-darwin.so` contains `meta.commands.creative._upload_image` ("Upload an image and return its hash") and `meta.commands.creative._upload_video` ("Upload a video and return its ID"). Image hash and video ID are exactly the two handles `object_story_spec` needs.

**(c) Meta's own doc, verbatim** (`ads-cli/ad-creatives`): *"Ads CLI uploads media files automatically when you create or update an ad creative."* Supported: images `.jpg .jpeg .png .gif .bmp .webp`; videos `.mp4 .mov .avi .mkv .wmv`.

**Note:** the package is **mypyc-compiled** (`meta/*.cpython-313-darwin.so`, top-level module is `meta`, not `meta_ads`). That is *why* there are only cp312/cp313 wheels and no sdist — these are native extension modules, not pure Python. It also means you cannot read or patch the source.

### Upload is fused into creative creation — there is no standalone upload command

There is no `meta ads adimage` or `meta ads advideo` group. Upload happens **inside** `creative create` / `creative update`. You pass a local path, it uploads and builds the creative in one call. Practically this is better, not worse — one command instead of two. The only thing you lose is the ability to reuse a previously-uploaded asset by hash without re-uploading it.

Format is inferred, per Meta's doc:
- `--video` given → **video ad**
- `--link-url` given, no video → **link ad**
- neither → **photo post**

`creative update` also re-uploads: `--image ./new-banner.jpg`, `--video ./new-video.mp4`.

### THE COMBINED QUESTION: brand-new image ad AND brand-new video ad, end to end, from a local file, with zero raw Graph calls?

**YES — and the CLI alone is sufficient. The MCP is not even needed for this.**

Image ad:
```bash
meta ads campaign create --name "C" --objective OUTCOME_TRAFFIC --daily-budget 5000
meta ads adset create <CAMPAIGN_ID> --name "A" --optimization-goal LINK_CLICKS \
  --billing-event IMPRESSIONS --targeting-countries US
meta ads creative create --name "Hero" --image ./banner.jpg --page-id <PAGE_ID> \
  --body "..." --title "..." --link-url https://example.com --call-to-action SHOP_NOW
meta ads ad create <ADSET_ID> --name "Hero Ad" --creative-id <CREATIVE_ID>
meta ads campaign update <CAMPAIGN_ID> --status ACTIVE   # + adset + ad
```
Video ad: identical, swapping `--video ./promo.mp4` for `--image`. Thumbnail is optional (Meta auto-generates).

**No missing step. No raw Graph call required.**

**Therefore: the Graph API fallback is OPTIONAL, not mandatory** — for the creative/launch workflow, which is the workflow that matters most. This changes the earlier recommendation's emphasis: raw Graph is a *capability extender*, not a *dependency*.

It becomes **mandatory only** if you need, with CLI-only: custom audiences (CLI has none — but the **MCP covers this fully**, so CLI+MCP together also clears it), or one of: `adrule` automated rules, `adlabel`, `adreportrun` async reports, `/asyncbatch` bulk, or the 81 breakdowns / 16 action_breakdowns neither surface exposes. **None of those block launching ads.**

### Doc/binary drift found (two now)

- Meta's `ad-creatives` page says `--instagram-actor-id`; the shipped v1.1.0 binary's flag is **`--instagram-user-id`**. Using the documented flag will fail.
- (Previously noted) `meta auth` is documented as saving a token; the binary only has `meta auth status`.

**Trust the binary's `--help`, not the docs.** A skill should be built from `--help` output.

---

## 2. TRANSPORT LIST — the framing is CORRECT, with two genuine exceptions

**Confirmed: there is exactly ONE programmatic API — the Graph API (of which the Marketing API is a subset of nodes) — and every option below is a transport over `graph.facebook.com`.**

Proof for the two official surfaces specifically:
- **Ads CLI**: depends on `facebook-business>=20.0`; installed tree contains `facebook_business 25.0.3`; the live probe returned a raw Graph error object (code 190) surfaced verbatim. It is a Click wrapper over Meta's own Graph SDK.
- **Official MCP**: its OAuth metadata points at `https://graph.facebook.com/v25.0/oauth/access_token`, and its scopes are Graph permissions (`ads_management` etc.). Server-side it calls Graph.

### Complete transport list

| Path | Ultimately Graph API? |
|---|---|
| Official Ads CLI (`meta-ads`) | **Yes** — via `facebook_business` SDK |
| Official Ads MCP (`mcp.facebook.com/ads`) | **Yes** — Meta-hosted Graph wrapper |
| Python `facebook_business` SDK | **Yes** — it *is* the Graph client |
| Node `facebook-nodejs-business-sdk` | **Yes** |
| Third-party MCPs (pipeboard, gomarble, brijr, …) | **Yes** |
| Composio / Zapier / Pipedream / Paragon / Klavis | **Yes** |
| n8n Facebook Graph API node | **Yes** — it is literally a generic Graph request node |
| Raw `curl` / `httpx` | **Yes**, by definition |
| **Conversions API** | **Yes** — `POST graph.facebook.com/v25.0/<DATASET_ID>/events`. Same host, same token, same version. Not a separate API; it is a Graph node. Also **inbound only** (you send conversions *to* Meta) — it cannot manage ads. |
| **Webhooks / leadgen** | **Partially — push, not pull.** Meta POSTs to *your* HTTPS endpoint, so the delivery is not a Graph call. But subscription setup is Graph (`/<APP_ID>/subscriptions`), payloads carry IDs you must then resolve via Graph, and **there are no webhook topics for campaign/adset/ad/budget state** — the ads-relevant topic is `leadgen`. Not a management path. |

### The two genuine non-Graph exceptions

**(a) Ads Manager bulk CSV import/export.** Real, and genuinely not the API — you download an XLSX/CSV of your account structure, edit it, and re-upload through the Ads Manager UI. It is the only high-volume bulk-edit surface Meta offers to non-API users. **But it is UI-only: there is no documented endpoint to submit a bulk sheet programmatically.** Reaching it from Claude means browser automation (Playwright), which is brittle, fights Meta's bot detection, and would drive the maintainer's logged-in session. Not a serious candidate; noted for completeness.

**(b) Meta Business Suite UI automation generally** — same verdict, same reasons.

Also non-Graph but non-programmatic: **Meta's BI/reporting integrations** (Ads Reporting scheduled email/CSV exports, Marketing Mix Modelling exports). These emit files rather than serving an API. A Claude skill could parse a delivered CSV, but that is data ingest, not connection, and the data is a strict subset of `/insights`.

### Complete `ads-ai-connectors` doc section — all 17 pages, fully enumerated

Extracted from the rendered sidebar. **There are exactly two products in this section. There is no third official connector.**

*Ads CLI (8):* `ads-cli-overview`, `setup/get-started`, `setup/configuration`, `command-reference`, `tutorials-and-recipes`, `ad-creatives`, `datasets-and-catalogs`, `insights`

*Ads MCP Server (9):* `ads-mcp-server-overview`, `ads-mcp-server-get-started`, and the seven `ads-mcp-server-tools-*` category pages (`comprehensive-reporting`, `ad-creation-and-management`, `catalog-creation-and-management`, `signals-and-datasets`, `help-and-troubleshooting`, `abtests-and-conversion-lift-studies`, `activity-logs`)

Every one of these was fetched this session. Nothing in the section is unenumerated.

### Answer: the complete set of ways to connect Claude to Meta ads, today

1. **Official Ads CLI** — shell, system user token. *(Graph)*
2. **Official Ads MCP** — remote HTTP MCP, OAuth or bearer. *(Graph)*
3. **Raw Graph API** from a skill — curl/httpx. *(Graph)*
4. **Official SDKs** (Python v25.0.3 / Node v24.0.1) in a script. *(Graph)*
5. **Third-party MCP servers.** *(Graph, plus a vendor)*
6. **Aggregators** — Composio, Zapier, Pipedream, Klavis. *(Graph, plus a vendor)*
7. **n8n Facebook Graph API node.** *(Graph)*
8. **Browser automation of Ads Manager**, incl. bulk CSV import. *(NOT Graph — the only true exception, and not recommended)*
9. **Consuming Meta-generated report exports** (CSV/email). *(NOT Graph, but read-only, delayed, and a subset of `/insights`)*

**1–7 are all the same API wearing different clothes.** The only real choices are *which transport* and *whose credentials*.

---

## 3. VERSIONING — three independent clocks

### (a) `meta-ads` CLI — new, slow, currently stable

| Version | Released | Notes |
|---|---|---|
| 1.0.0 | 2026-04-29 16:46 UTC | Launch. 5 wheels (cp312 only) |
| 1.0.1 | 2026-04-29 18:14 UTC | Same-day hotfix; **added cp313 wheels** (5 → 10) |
| **1.1.0** | **2026-06-17 23:58 UTC** | Current latest, re-verified live 2026-07-28 |

**1.1.0 is the latest.** Three releases in three months; **~6 weeks since the last one.** One minor bump, no 2.x — **no breaking changes to date.** Meta publishes no changelog for this package (PyPI description has none, and there is no public repo), so **change detection means diffing `meta --help` between versions.** Pin `meta-ads==1.1.0` and review on upgrade.

Rot risks specific to the CLI:
- **Wheels are cp312/cp313 only, and mypyc-compiled.** Python 3.14 already exists (my system Python) and **fails to install**. When 1.1.0 is the pinned version and the box moves to 3.14+, the kit breaks. **Pin the interpreter, not just the package.**
- **No Windows wheel.**
- The binary already emits SDK deprecation warnings (`remote_create is being deprecated`), so an upstream `facebook_business` bump could break it.

### (b) MCP endpoint — UNVERSIONED, tracks latest

`https://mcp.facebook.com/ads` has **no version segment**, no version header, and no versioned alias (I probed `/mcp`, `/marketing`, `/ads/mcp`, `/ads/sse` — all 404). Its OAuth metadata points at **v25.0** Graph endpoints, so it currently sits on v25.0 server-side, but **you cannot pin it** and Meta can change the tool list under you (docs were "Updated: Jul 14, 2026", already newer than the April launch — which is exactly how "29 tools" became ~93).

**This is the MCP's real maintenance liability, and it cuts both ways:** zero effort to stay current, zero ability to stay still. A skill written against specific MCP tool names can silently break. The CLI, pinned, cannot.

### (c) Graph API — v25.0 current, 2-year minimum support

Probed `graph.facebook.com/vN.0/me` directly:
- **v19.0 through v25.0 all resolve** (return the normal auth error, code 2500).
- **v26.0 and v27.0 do not exist** — `"Unknown path components: /me"`, i.e. the version string isn't recognised.

So **v25.0 is current**, and at least **v19.0–v25.0 (7 versions) are simultaneously live**.

Meta's versioning doc: *"A version will no longer be usable two years after the date that the subsequent version is released."* On expiry, *"any calls made to it will be defaulted to the next oldest, usable version"* — it degrades rather than hard-failing, which is arguably worse because it fails silently. Meta reserves the right to change any version immediately for security/privacy.

Release cadence, inferred from `facebook-business` SDK major bumps (Meta ships the SDK major in lockstep with the Graph version): **v22 → Feb 2025, v23 → Jun 2025, v24 → Oct 2025, v25 → Mar 2026. Roughly every 4–5 months.** So expect **v26 around Aug–Oct 2026**, and v25.0 usable until roughly **late 2028**.

### Anti-rot recommendations for the kit

1. **Pin `meta-ads==1.1.0` AND the interpreter to Python 3.13.** The 3.14 install failure is not hypothetical, it happened here.
2. **Pin the Graph version explicitly** (`/v25.0/`) in every raw call. Never call unversioned — you inherit silent downgrades.
3. **Build the skill from `meta --help` output, not the docs** — two doc/binary drifts found in one session (`--instagram-actor-id`, `meta auth`).
4. **Treat MCP tool names as unstable.** Re-run `tools/list` rather than hardcoding, and keep the CLI as the deterministic path.
5. **Calendar check ~Sept 2026** for Graph v26 and any `meta-ads` 1.2/2.0.

---
---

# CORRECTION PASS 3 — 2026-07-28 (DCR question)

**This section CORRECTS the earlier claim "Dynamic client registration is CLOSED / you must supply your own Meta App ID" (§A above). That conclusion was a probing artifact.**

## VERDICT

**App ID NOT required in Claude Desktop / claude.ai. NOT required in Claude Code CLI either, in principle — Meta's `--client-id` documentation is stale/defensive, and the CLI's real blocker is an Anthropic-side redirect_uri bug, not a Meta app requirement.**

The maintainer's lived experience is correct. The earlier probe was wrong.

## Why the earlier probe was wrong

Meta runs a **client_name-allowlisted pseudo-DCR**. `POST https://mcp.facebook.com/.well-known/register/ads` does not create a new app — it hands back a **pre-provisioned, first-party Meta app**, but only if the request's `client_name` is on Meta's allowlist. The earlier pass posted a generic client_name, got the generic rejection, and concluded DCR was closed for everyone.

Live probes, 2026-07-28 (all reproducible, run 3x):

```
POST /.well-known/register/ads
{"client_name":"Claude","redirect_uris":["https://claude.ai/api/mcp/auth_callback"],
 "grant_types":["authorization_code","refresh_token"],"response_types":["code"],
 "token_endpoint_auth_method":"none"}
-> 200
{"client_id":"4510005499318155","client_id_issued_at":...,"client_secret_expires_at":0,
 "token_endpoint_auth_method":"none",
 "redirect_uris":["https://claude.ai/api/mcp/auth_callback"],
 "client_name":"Claude","grant_types":["authorization_code","refresh_token"],
 "response_types":["code"]}
```

The returned `client_id` is **fixed and identical on every call** (never a freshly minted app), and it is a real Meta-owned app:

```
GET https://graph.facebook.com/v25.0/4510005499318155?fields=id,name
-> {"id":"4510005499318155","name":"ads MCP server"}
```

### The discriminator is `client_name`, isolated by controlled probe

| `client_name` | redirect_uri | result |
|---|---|---|
| `Claude` | `https://claude.ai/api/mcp/auth_callback` | **200** → `4510005499318155` |
| `Claude Desktop` | `https://claude.ai/api/mcp/auth_callback` | **200** → `4510005499318155` |
| `Claude Code` | `http://localhost:60123/callback` | **200** → `4510005499318155` |
| `claude-code` | `http://localhost:8080/callback` | **200** → `4510005499318155` |
| `claude` (lowercase) | `http://localhost:60123/callback` | **200** → `4510005499318155` |
| `MyClaudeApp` | `https://claude.ai/api/mcp/auth_callback` | **200** → `4510005499318155` |
| `ChatGPT` | `https://chatgpt.com/connector_platform_oauth_redirect` | **200** → **`1718457352668935`** (also named "ads MCP server" — a separate OpenAI-facing app) |
| `Anthropic` | `https://claude.ai/api/mcp/auth_callback` | 400 `invalid_client_metadata` |
| `Cursor` | `cursor://.../callback` | 400 `invalid_client_metadata` |
| `x` | `https://claude.ai/api/mcp/auth_callback` | 400 `invalid_client_metadata` |
| `x` | `http://localhost:8080/callback` | 400 `invalid_client_metadata` |

Match appears to be a **case-insensitive substring test on "claude"** (`MyClaudeApp` passes, `Anthropic` fails).

Redirect URI is validated **independently**, against the pre-registered app's own allowlist:

| `client_name` | redirect_uri | result |
|---|---|---|
| `Claude` | `https://claude.ai/api/mcp/auth_callback` | 200 |
| `Claude` | `http://localhost:53211/callback` (arbitrary port) | 200 |
| `Claude` | `https://evil.example.com/cb` | 400 `invalid_redirect_uri` — "The provided redirect_uris are not registered for this client." |
| `Claude` | `claude://mcp/oauth/callback` | 400 `invalid_redirect_uri` |
| any | *(omitted)* | 400 "redirect_uris must contain at least one URI." |

Note `http://localhost:8080/callback` is normalised in the response to `http://127.0.0.1:8080/callback`.

**So: Anthropic (and OpenAI) are pre-registered OAuth clients with Meta. Meta ships a first-party "ads MCP server" app per partner and hands its client_id to any caller that identifies as that partner.** That is exactly the mechanism behind the maintainer's "you just paste a URL and it registers in the background" experience.

The `Anthropic`-fails / `Claude`-passes split is worth noting as a fragility: the allowlist is keyed on a display string, not on anything cryptographic.

## Also re-probed this pass (unchanged)

- `/.well-known/oauth-protected-resource/ads` → 200, same 7 scopes as before.
- `/.well-known/oauth-authorization-server/ads` → 200, and it **advertises** `"registration_endpoint":"https://mcp.facebook.com/.well-known/register/ads"`. An open registration_endpoint in the metadata is itself evidence Meta intends automatic client registration; the earlier pass treated the advertised endpoint as vestigial.
- Bare `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server` (no `/ads`) → 404 `{"title":"MCP server not found"}`. Path suffix is mandatory.
- `POST /ads` unauthenticated → 401 with the same `WWW-Authenticate` resource_metadata + scope header.
- The authorize dialog accepts the handed-back client_id: `GET https://www.facebook.com/v25.0/dialog/oauth?client_id=4510005499318155&redirect_uri=https%3A%2F%2Fclaude.ai%2F...` → 302 to `login.php` with `is_business_login=1`. A normal Facebook Login for Business consent, nothing app-owner-specific.

## Meta's docs — no Claude Desktop flow exists

Full rendered text of `ads-mcp-server-get-started` and `ads-mcp-server-overview` (Playwright; both "Updated: Jul 14, 2026"). **There is no Claude Desktop section, tab or toggle.** Only three connect sections exist: "from Claude Code", "from ChatGPT", and "with user access token". Verbatim, the opening line of get-started:

> "Owning a Meta app is not a prerequisite on using the ads MCP server. For access without owning a Meta app, follow How to set up Meta ads AI connectors instead."

(links to Business Help Centre article `facebook.com/business/help/1456422242197840`)

> "To use the ads MCP server with your own Meta app, you must follow some key steps to set up your environment and gain access. **Create or reuse a Meta developer app** — Go to developers.facebook.com/apps and create a new app, or open an existing app. Add the **Create & manage ads with ads MCP server** use case."

> "**OAuth** — The MCP client redirects you to the Facebook Login for Business dialog. You sign in with your Facebook account or your Meta Managed Account (MMA) and approve the requested permissions. **No manual token setup is required.** Make sure your Meta developer app's redirect URL is configured correspondingly with your choice of MCP client in the Facebook Login for Business settings."

> "**Connect to the ads MCP server from Claude Code** — To add the ads MCP server to Claude Code, run the command below.
> `claude mcp add --transport http --client-id <META_APP_ID> meta-ads https://mcp.facebook.com/ads`"

Note the framing: **the whole "create a developer app" block is explicitly the BYO-app path**, opened by a sentence saying an app is *not* a prerequisite. The earlier pass read the app-owner path as mandatory. It is one of two documented paths, and the docs only ever spell out the app-owner one because that is the developer-docs audience. No business verification is mentioned anywhere. `is_ads_mcp_enabled` appears nowhere in either page (consistent with the earlier pass).

## Anthropic's side

Anthropic's custom-connectors support article, verbatim:

> "Add your connector's remote MCP server URL." … "Optionally, click 'Advanced settings' to specify an OAuth Client ID and OAuth Client Secret for your server."

So the Desktop/web dialog **does** have client_id/secret fields — but under *Advanced settings*, and **optional**. Default path is URL + OAuth click, DCR in the background. This matches the probe exactly.

## First-hand reports

One verified primary source. **anthropics/claude-code#57191** (confirmed real via `gh api`), "Meta Ads MCP at mcp.facebook.com/ads rejects Claude Code CLI OAuth — redirect_uris not registered", @marializura, 2026-05-08, closed as duplicate. Verbatim error:

> `SDK auth failed: The provided redirect_uris are not registered for this client.`

The reporter states OAuth **works from claude.ai web (Pro/Max) and Claude Desktop**, and fails only in Claude Code CLI. Closed as a duplicate of #37747, described as a *"Claude Code 2.1.80+ CIMD regression where redirect_uris omit the dynamic port"* — **an Anthropic client bug, not a Meta app-ID requirement.** No one in the thread mentions needing a Meta App ID.

That is consistent with my probe: `client_name: "Claude Code"` + `http://localhost:60123/callback` registers fine today, so a correctly-formed loopback redirect from the CLI is accepted by Meta. A malformed one (port omitted) hits exactly the `invalid_redirect_uri` string above.

No genuine Reddit/forum first-hand accounts found. All other coverage is the same SEO content-farm cluster (theadspend, lucidmedia, pipeboard, adkit, get-ryze, windsor, getpassionfruit) — several are third-party MCP vendors with an incentive to push readers to their paid product after the supposed "not enabled" wall. **The `is_ads_mcp_enabled` gate remains UNCONFIRMED RUMOUR** — no screenshot, no verbatim server response, no named individual anywhere.

## Answers

| Question | Answer |
|---|---|
| Desktop / claude.ai "Add custom connector" needs your own App ID? | **No.** URL + OAuth click. DCR returns Meta's own app `4510005499318155`. Advanced settings field exists but is optional. |
| Claude Code CLI needs `--client-id`? | **Not per the protocol** — `client_name: "Claude Code"` + a well-formed loopback redirect registers fine. But Meta documents it, and there is a real reported CLI redirect_uri bug. **Passing `--client-id` with your own app is the reliable CLI path today.** |
| Was "DCR is closed" ever true? | No evidence it was. The error is what a **non-allowlisted client_name** gets. Meta may have added the allowlist since, but the earlier probe never tested a Claude-named client, so it cannot distinguish. |

## What I could NOT determine without a real Meta login

1. **Whether the OAuth consent then succeeds for the maintainer's account.** Registration and the authorize redirect both work unauthenticated; what happens *after* login — consent screen, or an eligibility/allowlist refusal on `ads_mcp_management` — is invisible without credentials.
2. **Whether `is_ads_mcp_enabled` bites.** Unresolvable by probe. Only an authenticated attempt settles it.
3. **The exact `client_name` Claude Desktop actually sends.** Inferred, not observed. Any "claude"-containing string works, so the risk is low.

**The 2-minute manual check:** Claude Desktop → Settings → Connectors → Add custom connector → paste `https://mcp.facebook.com/ads` → Add (leave Advanced settings empty, do NOT enter a client ID). If the Facebook Login for Business consent screen appears listing the ads scopes, no App ID is needed — confirmed end to end. If it errors before the browser opens, that is a DCR/client problem; if it errors *after* consent, that is the eligibility gate.

## If an App ID does turn out to be needed

Minimum path, per Meta's own get-started page: a **bare developer app in Development mode is enough — no App Review, no business verification** (consistent with §7 above, standard access suffices for your own ad accounts). Roughly: developers.facebook.com/apps → Create app → add the **"Create & manage ads with ads MCP server"** use case → copy the App ID → add the client's redirect URL under Facebook Login for Business settings. ~5 clicks, under 5 minutes. **Not safely browser-automatable** — it requires a logged-in Meta session and the redirect-URL step is app-settings config; drive it manually.
