# Token Acquisition & Automation Risk

**Date:** 2026-07-29
**Status:** Research complete. One design fork resolved, three spikes outstanding.
**Supersedes:** the token-minting decision in [`findings-and-decisions.md`](./findings-and-decisions.md) §7 ("Token minting: Claude drives Playwright").
**Trigger:** a live drive of Business Settings on 2026-07-29 hit four separate gates in one session.

---

## 1. Why this question exists

The locked design has Claude drive a throwaway Playwright Chromium through Meta Business
Settings to mint a never-expiring system user token. Driving it live on 2026-07-29 produced,
in one session:

1. **The page had moved.** `/settings/system-users` now 302s to
   `/latest/settings/system_users?...bm_redirect_migration=true`.
2. **A second-admin approval gate.** *"Someone else needs to approve request to generate an
   access token"* — *"this request must be approved by another admin first"*, request expires
   in 7 days. The business had 3 admins.
3. **A device block.** `business.facebook.com/security/block/` — *"The action isn't available
   right now. We are running additional checks on this new device. Please retry in 69
   minutes."*
4. **Name rejection.** "Meta Ads Connect" and "Ads Connect" both returned *"You chose an
   invalid system user name."*
5. **Missing scopes.** Only `ads_management`, `ads_read`, `business_management` were offered.
   `pages_show_list` and `leads_retrieval` were not offered at all for the selected app.
6. **A hidden prerequisite.** Token generation requires the system user to hold the app as an
   assigned asset with "Manage app", else *"No permissions available"*.

Any one of (2) or (3) breaks the kit's headline promise — connect in one shot — for reasons
that are invisible ahead of time, unfixable from inside the automation, and measured in hours
or days. That is a product failure before it is ever a policy question. The policy question is
below anyway, because the kit ships publicly and runs on hundreds of unrelated businesses.

---

## 2. The risk question: does UI automation violate Meta's terms?

**Short answer: yes, under the consumer Terms of Service — and the observed enforcement is
checkpoints and identity verification, not bans. Both halves of that sentence are load-bearing.**

### 2.1 What is documented policy

The prohibition does not live where you would expect it. It is **not** in the Platform Terms
or the Developer Policies — both of those govern what you may do with Platform Data obtained
*through the API*, and neither contains any clause on browser automation, scraping, crawlers,
or bots as a standalone topic. The relevant text is in the ordinary **Facebook Terms of
Service**, §3.2, and there are two distinct clauses:

> "You may not access or collect data from our Products using automated means (without our
> prior permission) or attempt to access data that you do not have permission to access,
> **regardless of whether such automated access or collection is undertaken while logged in to
> a Facebook account**."
>
> — [facebook.com/terms.php](https://www.facebook.com/terms.php), §3.2 (effective 10 Dec 2025).
> Emphasis added.

That trailing clause is the one that matters. The intuitive defence — *it's my own account, my
own business, my own data* — is explicitly anticipated and explicitly does not apply.

The second clause is scoped to method rather than data:

> "You may not do, or attempt to do, anything to circumvent, bypass or override any
> technological measures that Meta uses to control or limit access to our Products or data."
>
> — same section.

This second clause is what any browser-realism work (§6) runs into head-on.

**What does *not* apply.** The [Automated Data Collection
Terms](https://www.facebook.com/legal/automated_data_collection_terms) (effective 7 Oct 2024)
require *separate express written permission* for automated collection — but they define their
scope as tools "capable of navigating or indexing the surface-layer of the World Wide Web", cap
permitted use at "providing results for your Search Engine" or "displaying previews of Meta
URLs", and restrict collectable personal data to "Publicly Available Personal Data". That is a
document about third parties harvesting other people's public data. Nothing in it purports to
govern a logged-in owner acting on their own assets. It is frequently miscited as the blanket
anti-automation rule; it is not.

### 2.2 What Meta documents about enforcement

Meta's Account Integrity policy is the only primary source that names automation and business
assets in the same document, and it draws a clear structural line.

Automation sits in the **verification** bucket — Meta "may request additional information about
an account to ascertain ownership and/or permissible activity" in these scenarios:

> "Compromised accounts; **Creating or using an account or other entity through automated means,
> such as scripting (unless the scripting activity occurs through authorised routes and does not
> otherwise violate our policies)**; Empty accounts with prolonged dormancy."
>
> — [transparency.meta.com — Account
> Integrity](https://transparency.meta.com/policies/community-standards/account-integrity/)
> (updated 29 May 2026). Emphasis added.

Note the parenthetical. "Authorised routes" is the carve-out, and the API is the authorised
route. UI scripting is not.

The **restrict or disable** bucket — which does explicitly cover "Business Managers, ad
accounts" — is populated by something else entirely: egregious harms referred to law
enforcement, deceptive or dangerous Advertising Standards violations, persistent Community
Standards violations, ban evasion, and network coordination. Automation is not in that list.

Meta's one published, graduated enforcement ladder (warning → feature restriction → 1/3/7/30-day
restrictions → disable) is scoped in its own text to *content*: "if you continue to post content
that goes against the Community Standards after repeated warnings and restrictions, we will
disable your account"
([transparency.meta.com — Restricting
accounts](https://transparency.meta.com/enforcement/taking-action/restricting-accounts/)). It
does not mention automation, scripting, or bot detection anywhere.

Meta's own account of how it fights automated access is framed throughout as *data extraction*:
detection by "patterns in activity and behavior that are typically associated with automated
computer activity", first-line response "rate limits and data limits", and escalation to "cease
and desist letters, disabling accounts, filing lawsuits against scrapers engaging in egregious
behavior" ([How we combat scraping](https://about.fb.com/news/2021/04/how-we-combat-scraping/),
Meta Newsroom, 15 Apr 2021).

And the backstop, which applies to everything: Meta may "suspend or permanently disable your
access to Meta Company Products" for breaches determined "in our discretion"
([facebook.com/terms.php](https://www.facebook.com/terms.php), §4.2).

### 2.3 Is there evidence of bans from UI automation?

**No primary evidence. State this precisely: the evidence supports checkpoints and throttles,
and nothing more.**

There is no Meta policy document, no transparency report, no court record, and no Meta
developer statement that browser automation of one's own Business Settings has produced
permanent restriction of an account, Business Manager, or ad account. Meta's own policy text
places that behaviour in the ownership-verification category, not the disable category (§2.2).

What exists on the other side is **community anecdote and commercially interested vendor
content** — Reddit threads, ad-agency "account recovery" blogs, and anti-detect-browser vendors
whose product is the proposed remedy. Explicitly labelled as such; not weighted as evidence.
None of it was traceable to a specific, verifiable first-hand account of automation-caused
permanent loss.

*Meta Platforms v. Bright Data* (N.D. Cal., summary judgment 23 Jan 2024, suit dropped 23 Feb
2024) is sometimes cited here. It held that logged-**out** scraping of public data did not
constitute "use" under Meta's ToS. Different fact pattern — third party, logged out, public data
— and it says nothing about logged-in first-party automation. Sourced from law-firm summaries,
not the docket; cited for completeness only.

### 2.4 The honest verdict on risk

| | Established |
|---|---|
| Is it a ToS breach? | **Yes.** FB ToS §3.2, explicitly not excused by owning the account. |
| Is it a *Platform Terms* / Developer Policy breach? | **No clause found.** Those documents govern the API, not the UI. |
| Documented enforcement response to scripting? | **Request for ownership verification** — Account Integrity policy, verbatim. |
| Documented path from UI automation to permanent ban? | **None found.** Meta's disable ladder is content- and network-scoped. |
| Observed on 2026-07-29? | **A 69-minute device block and a 7-day approval gate.** Checkpoints and throttles — exactly what the documented policy predicts. |
| Ban risk, honestly stated | Non-zero because §4.2 is discretionary, but **unsupported by any primary evidence**. Do not tell installers they risk losing their ad account; there is nothing to back that. |

The reason to abandon UI-driving is therefore **not** "it will get people banned". It is: it is a
ToS breach we would be shipping to hundreds of people who did not read the terms, in service of
a flow that the observed checkpoints have already shown cannot deliver its one-shot promise.

---

## 3. Every documented way to get a token that can manage an ad account

Five paths exist. Only two are viable for a publicly cloned kit.

| # | Path | Token & expiry | App Review? | Business Verification? | Tech Provider? | Real cost |
|---|---|---|---|---|---|---|
| 1 | **Facebook Login for Business → user token → long-lived exchange** | User token, **~60 days**, not renewable after expiry | **No**, if every user has a role on the app | **No**, same condition | **No**, same condition | Installer creates their own app (~5 min, manual); re-auth every 60 days |
| 2 | **Facebook Login for Business → Business Integration System User token** | System user token, **never expires** by default | **No** for businesses you own/manage; yes to serve others | Not stated for own-business | No, for own-business | Same app creation + a login *configuration* (`config_id`). **Unproven for the own-business case** |
| 3 | **System user + token via Business Management API** | System user token, **never expires** unless `set_token_expires_in_60_days` | **Sources conflict** — see §3.3 | Conflicting | No | Bootstrap token from a human admin still needed; app must be claimed by the business |
| 4 | **System user token via Business Settings UI** (today's path, and Meta's own documented onboarding) | System user token, **never expires** | No | No | No | The human clicks it. Automating the clicking is §2. |
| 5 | **Central Selr-owned app, App Review'd for Advanced Access** | Either of the above | **Yes** | **Yes — Selr AI's** | Effectively yes | Screencasts, review, ongoing compliance reviews, **and a hosted token broker** — see §7.3 |

### 3.1 Path 1 — Facebook Login for Business, user token

`ads_management` is a supported scope for Facebook Login for Business, which Meta calls "the
preferred authentication and authorization solution for tech providers building integrations
with Meta's business tools"
([docs](https://developers.facebook.com/docs/facebook-login/facebook-login-for-business)). The
app must be a **business type app**.

Long-lived exchange is `GET oauth/access_token` with `grant_type=fb_exchange_token`,
`client_id`, `client_secret`, `fb_exchange_token`. "A long-lived token generally lasts about
**60 days**." The hard limit:

> "You can not use an expired token to request a long-lived token. If the token has expired,
> your app must send the user through the login flow again to regenerate a new short-lived
> access token."
>
> — [Get long-lived
> tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived)

So a user token is a 60-day lease with a manual renewal. Renewal is one browser click *if* done
before expiry; a full re-login if not.

**Localhost redirect URIs work, but only in Development mode.** Meta's HTTPS-enforcement
announcement states it directly: *"You will still be able to use HTTP with 'localhost'
addresses, but only while your app is still in development mode."*
([Requiring HTTPS for Facebook
Login](https://developers.facebook.com/blog/post/2018/06/08/enforce-https-facebook-login/), 8
Jun 2018). This is a genuine convenience for a locally-run kit and a genuine constraint: the app
must stay in Development mode, which is exactly where §4 says it should stay anyway.

### 3.2 Path 2 — Business Integration System User token

Meta documents a second token type obtainable through the same login dialog:

> "Business integration system user access tokens should be used if your app performs
> programmatic, automated actions on your business clients' assets without having to rely on
> input from an app user, or require re-authentication at a future date." … "Defaults to
> **never expire** for the common offline server-to-server communication."

Requirements listed: the app must be a business type app; "Businesses onboarding to your app
must have, or be willing to create, a business portfolio"; "Your app must be associated with a
business portfolio, which you have full control"; and Advanced Access is required only "to serve
businesses that you do not own or manage".

The sentence that suggests it works for our case:

> "To test the business integration system user access token flow, the tester must have a role
> on the app and full control of the client business."

— all from
[Facebook Login for Business](https://developers.facebook.com/docs/facebook-login/facebook-login-for-business).

An installer who owns the app and the business satisfies both conditions. **This would be the
ideal path** — one browser consent, a never-expiring token, no App Review. It is inference from
the documented conditions, not a confirmed result. **Spike it.**

### 3.3 Path 3 — the Business Management API chain

Every link in this chain is documented, and the chain terminates in a never-expiring token:

1. `POST /{business-id}/system_users` — params `name`, optional `role`. Caller: "an access token
   of an admin user, or admin system user for this Business Manager". Constraint: "Apps can only
   target businesses (or child businesses of those businesses) that have claimed them", and error
   104001: "In order to create a system user, an app must be part of this business."
   ([reference](https://developers.facebook.com/docs/graph-api/reference/business/system_users/))
2. `POST /{system-user-id}/applications` — param `business_app`. "Both system user and app should
   belong to a same Business Manager. **Only apps with Ads Management API standard access and
   above can be installed.**"
3. `POST /{system-user-id}/access_tokens` — params `business_app`, `scope`, `appsecret_proof`,
   optional `set_token_expires_in_60_days`. Omit that last param and the token **never expires**.
   Caller must be "a Business Manager admin, admin system user or regular system user".
   (2 and 3 from [Install apps, generate, refresh and revoke
   tokens](https://developers.facebook.com/docs/business-management-apis/system-users/install-apps-and-generate-tokens/))
4. `POST /act_{ad-account-id}/assigned_users` — params `user` ("Business user id or system user
   id") and `tasks` (`MANAGE`, `ADVERTISE`, `ANALYZE`, `DRAFT`, `AA_ANALYZE`).
   ([reference](https://developers.facebook.com/docs/graph-api/reference/ad-account/assigned_users/))

**The conflict.** The system users *Overview* page lists as a prerequisite:

> "Have the Meta app go through an app review (and Business verification) for the permissions the
> system user wants access to."
>
> — [System users
> overview](https://developers.facebook.com/docs/business-management-apis/system-users/overview/)

That contradicts step 2's own requirement, which is only "Ads Management API standard access and
above" — the Marketing API *access tier*, which is granted automatically on adding the Marketing
API product (§4.3), not an App Review of a permission. It also contradicts the role-holder
carve-outs in §4. Meta has not harmonised these pages.

There is a defensible reading of why the Overview might be right: **a system user is not a person
with a role on the app.** The role-holder carve-outs in §4 are all phrased about *app users
granting permissions through login*. A system user is a non-human identity, and Meta may scope
the `scope=` parameter against the app's approved permission set rather than against anyone's
role. That would make Path 3 genuinely App-Review-gated while Path 1 is not.

Against that reading: Path 4 — the Business Settings UI — mints exactly this kind of token, is
what Meta's own Ads CLI onboarding tells people to do (§3.4), and demonstrably works for
dev-mode apps. Observation 5 above is a data point in the same direction: the UI offered exactly
`ads_management`, `ads_read`, `business_management` and withheld `pages_show_list` and
`leads_retrieval` — which reads far more like "the app has these products configured and not
those" than like an App Review gate, since App Review would have withheld the ads permissions too.

**Unresolved. Spike it.** The same probe settles §3.2.

The same Overview page also caps system user counts: **Standard Access → 1 system user + 1 admin
system user; Advanced → 10 + 1.** One is enough, but it means a re-run must reuse the existing
system user, as the current minting code already does.

### 3.4 Path 4 — the Business Settings UI, which is Meta's own documented onboarding

Worth stating plainly, because it reframes the "manual fallback" from a consolation prize into
the sanctioned path. Meta's Ads CLI get-started page instructs, in Meta's own words:

> "Ads CLI requires a system user access token to authenticate for programmatic access."

with prerequisites of an admin system user, assets assigned to it, and **the system user added as
an App Admin in Meta for Developers** — which is exactly observation 6 above, documented all
along. The steps are *Meta Business Suite → Settings → Users → System Users*, select the system
user, choose the app, tick permissions, "Click Generate Token and copy the resulting token". Meta
lists the scopes as `business_management, ads_management, pages_show_list, pages_read_engagement,
pages_manage_ads, catalog_management, read_insights` — a broader set than the kit currently asks
for.

— [Ads CLI get
started](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/get-started)

**A human doing these clicks is Meta's documented instruction. A bot doing them is §2.** The
difference between the compliant path and the non-compliant one is entirely who moves the mouse.

### 3.5 Path 5 — a central Selr app with App Review

For completeness. `ads_management` App Review requires the submitter to "Provide specific
examples of why your app requires managing ads on behalf of **other businesses**" plus three
screencasts of the login and reporting flows
([permission reference](https://developers.facebook.com/docs/permissions/reference/ads_management)).
Advanced Access additionally requires Business Verification of the owning business, mandatory
since 1 Feb 2023
([Business
Verification](https://developers.facebook.com/docs/development/release/business-verification)).
Facebook Login for Business adds "ongoing compliance reviews" for Advanced Access apps.

Rejected for a reason that has nothing to do with the review effort. See §7.3.

---

## 4. The crux: App Review is not required, and Meta says so four times

**Established: an app used only by people who hold a role on that app gets every permission it
asks for, including `ads_management`, with no App Review, no Business Verification, and no Tech
Provider status.** This is not a loophole or an inference — it is stated explicitly on four
independent Meta doc pages.

### 4.1 The access-level rule

> "Permissions with **Standard Access** can only be requested from app users who have a role on
> the requesting app. Similarly, features with Standard Access are only active for app users who
> have a role on the app."
>
> "Permissions with **Advanced Access** can be requested from any app user…"
>
> "Advanced Access … must be approved on an individual permission and feature basis through the
> App Review process."
>
> — [Access
> levels](https://developers.facebook.com/docs/graph-api/overview/access-levels/)

The same page states that Business, Consumer and Gaming apps receive **automatic Standard Access
approval for all permissions and features**. Standard Access is not applied for; it is the
default.

### 4.2 The four carve-outs

| Source | Verbatim |
|---|---|
| [App Review / release](https://developers.facebook.com/docs/development/release/) | "If your app will only be used by people who have a role on the app itself you do not need to complete any of these processes because your app is already available to these users." |
| [Business Verification](https://developers.facebook.com/docs/development/release/business-verification) | "If your app will only be used by app users who have a role on the app itself you do not need to complete verification; **these users can grant your app any permissions at any time and all features are always active.**" |
| [Tech Providers](https://developers.facebook.com/docs/development/release/tech-providers/) | "Apps that have been created or claimed by a business cannot be granted any of the permission below unless the business has been verified as a Tech Provider, **or the person using the app has a role on the app itself**." — and the restricted list explicitly includes `ads_management`, `ads_read`, `business_management`, `leads_retrieval`, `pages_show_list`. |
| [Marketing API authorization](https://developers.facebook.com/docs/marketing-api/overview/authorization/) | "If your app is only managing your ad account, standard access to the `ads_read` and `ads_management` [permissions are sufficient]" … "if your app is managing other people's ad accounts, you need advanced access". |

The Tech Providers page is the most decisive of the four, because it is the one that names
`ads_management` and `leads_retrieval` in a restricted list and then hands you the exact key that
opens it: *a role on the app*.

### 4.3 Roles, and the separate rate-limit tier

Meta's app-roles page: Administrators, Developers and Testers "can grant the app any permission
while it is in development"
([app roles](https://developers.facebook.com/docs/development/build-and-test/app-roles/)). An app
can have up to 500 administrators. The installer who creates the app is its administrator by
construction.

Do not confuse permission access levels with the **Marketing API access tier**, which is a
separate gate governing rate limits only. It is granted automatically on adding the Marketing API
product ("Limited Access … Heavily rate-limited per ad account. For development only"), and
upgrades to Full Access on **usage**, not review: "at least 500 Marketing API calls in the last
15 days" with "an error rate of less than 15% in the last 500 calls"
([Marketing API
authorization](https://developers.facebook.com/docs/marketing-api/overview/authorization/)).
Meta renamed the tiers — old Standard → **Limited**, old Advanced → **Full** — effective 4 May
2026, which is why secondary sources are a mess here
([Meta blog](https://developers.meta.com/blog/updates-to-ads-management-standard-access-feature/)).

This is unchanged from `findings-and-decisions.md` §4 and remains the real production ceiling.

### 4.4 The one thing Meta does not say

Meta's documentation speaks about *an* app and *a* business. **No Meta page addresses the
category "distributed tooling where thousands of independent installers each create their own
Development-mode app."** Every rule above is written per-app and satisfied per-app, so the
conclusion follows — but it follows by construction, not because Meta has blessed the
distribution pattern by name. Recorded as inference, not quote.

The strongest corroboration is prior art: n8n has shipped exactly this pattern to a very large
user base for years (§6).

---

## 5. The approval gate: undocumented

**Not documented anywhere I could find.** This is a real finding, not a gap in the search.

Searched and found nothing on it: the Business Management APIs system-user pages, the
`system_users` and `access_tokens` Graph API references, the Marketing API step-by-step
[Generate an access token for a system
user](https://developers.facebook.com/docs/marketing-api/collaborative-ads/managed-partner-ads/api-guide/prerequisites/generate-access-token-system-user/)
walkthrough (which gives the full click sequence and mentions no approval step at all), the
developer community forum, and the Business Help Centre.

What is documented is a *different* approval flow: Meta Business Suite has a "People → Requests"
pending-approval queue for **adding people and changing their access rights**. Whether the same
mechanism has been extended to system-user token generation is not stated anywhere primary.

Specifically **not established**:

- What triggers it. Admin count, device trust, Business Verification status, two-factor
  enforcement, account age, business age, or a Business Settings security toggle — no source
  distinguishes between these. Observation 2 occurred in a business with 3 admins; that is one
  data point and rules nothing in or out.
- The 7-day request expiry — no documentation.
- **What happens in a business with exactly one admin.** Nothing found, primary or secondary.
  This is the single most consequential unknown for the kit, because a solo business owner is the
  modal installer. Either the gate does not fire (there is no second admin to ask), or it fires
  and is unsatisfiable. Both are plausible; neither is documented.
- Whether the gate applies to the **API** path (§3.3) as well as the UI path. If it does, it
  wounds Path 3 too.

One caveat on method: the Business Help Centre article on system users
(facebook.com/business/help/503306463479099) would not yield body text to any fetch — only its
title. Treat that page as **unread**, not as evidence of absence.

Practical consequence regardless of cause: this gate is undetectable in advance, unresolvable
from inside automation, and can add up to seven days. A one-shot connector cannot absorb it.

---

## 6. Browser realism: a real distinction, and the wrong answer anyway

### 6.1 What the tools actually do

`channel="chrome"` is documented and unambiguous: Playwright will "operate against the branded
Google Chrome and Microsoft Edge browsers available on the machine (note that Playwright doesn't
install them by default)"
([Browsers](https://playwright.dev/python/docs/browsers#google-chrome--microsoft-edge)). It is the
real Chrome binary, not a patched Chromium.

`launch_persistent_context(user_data_dir=...)` gives "a User Data Directory, which stores browser
session data like cookies and local storage". Two documented constraints: browsers "do not allow
launching multiple instances with the same User Data Directory", and "Due to recent Chrome policy
changes, automating the default Chrome user profile is not supported" — pointing `user_data_dir`
at Chrome's real profile "may result in pages not loading or the browser exiting"
([API](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context)).
So a persistent profile can only ever be a *separate* profile, built up from scratch — which
means it starts as a new device on first run regardless.

### 6.2 Device newness and automation detection are different mechanisms

This distinction is real and worth stating, because it is usually collapsed.

**Automation detection** is structural and unavoidable under Playwright. `navigator.webdriver` is
a W3C-standardised *deliberate disclosure*: the spec defines it to return true when "the user
agent is under remote control", existing expressly "for co-operating user agents to inform the
document that it is controlled by WebDriver, … so that alternate code paths can be triggered
during automation" ([W3C WebDriver
Level 2](https://www.w3.org/TR/webdriver2/#interface)). Chrome sets it true under
`--enable-automation`, `--headless`, or `--remote-debugging-port`
([MDN](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/webdriver)) — i.e. under
exactly the conditions Playwright creates. Neither `channel="chrome"` nor a persistent profile
changes this. Beyond the flag there is the CDP `Runtime.enable` side-channel, which Playwright
uses for most evaluate-based actions and which is observable to detection scripts
([Rebrowser writeup](https://rebrowser.net/blog/how-to-fix-runtime-enable-cdp-detection-of-puppeteer-playwright-and-other-automation-libraries)
— technical research, not a vendor-neutral primary source).

Playwright's own docs are **silent** on stealth and anti-detection — no position, in either
direction. The third-party stealth ecosystem (`playwright-stealth`, `patchright`) exists because
Playwright does nothing to hide these signals.

**Device trust** is a different thing: a new cookie jar, a fingerprint Meta has not seen before,
an unfamiliar profile-plus-IP combination. *"We are running additional checks on this new
device"* is textually a device-trust message, not a bot-detection message. A persistent profile
plausibly does address it, by carrying cookies and localStorage across runs.

### 6.3 Why it is still the wrong answer

Three reasons, in order of weight.

1. **It is the clause-two violation, explicitly.** Adopting a real Chrome channel and a warmed
   persistent profile *for the purpose of clearing the device check* is, on its face, an attempt
   "to circumvent, bypass or override any technological measures that Meta uses to control or
   limit access to our Products" (§2.1). Plain UI automation is a §3.2-clause-one problem with a
   documented response of "verify you own this account". Deliberate detection evasion is a
   different and worse posture, and a bad thing to ship in a public repo to hundreds of people.
2. **It does not solve the actual blocker.** It cannot help with the 7-day admin approval gate
   (§5), which is an authorisation decision, not a device check.
3. **It is unproven.** **No source — primary, secondary, or even anecdotal — was found that
   confirms or denies that `channel="chrome"` plus a persistent profile changes Meta's device
   gate.** The mechanism is plausible from documented first principles; the outcome is unverified.
   And on first run, when it matters most, the profile is empty and the device is new anyway.

Also established: **Meta publishes nothing about bot detection on business.facebook.com.** No
developer doc, no help-centre article, no statement of any kind. Everything circulating on the
topic is vendor content or forum lore.

---

## 7. Prior art: nobody drives the UI, and there are exactly two patterns

Across every vendor whose own documentation was read, the access-grant step is either an OAuth
consent screen or an instruction to the user to change a setting in Meta's UI themselves. **No
vendor documents automating Business Settings.** The vendors split cleanly into two camps.

### 7.1 Camp A — one central, reviewed vendor app

| Vendor | Evidence |
|---|---|
| **Zapier** | "log into Facebook Lead Ads to authenticate and grant Zapier permission to access your account". Permissions named: Manage Pages, Manage Ad Account, Leads Access, Business integration access. No Client ID/Secret field anywhere. [help.zapier.com](https://help.zapier.com/hc/en-us/articles/8496040397965-What-permissions-do-I-need-to-use-Facebook-Lead-Ads-with-Zapier) |
| **Supermetrics** | "Either log in with a new Facebook account, or click Continue as… Select the Businesses and Pages you want… Review the permissions, and click Save." Straight consent, no app creation. [docs.supermetrics.com](https://docs.supermetrics.com/docs/facebook-ads-connection-guide) |
| **Windsor.ai** | "Authorization is handled through secure OAuth"; requests `ads_management` and `business_management`. [windsor.ai](https://windsor.ai/documentation/authorize-via-link-in-windsor/) |
| **Hootsuite, Buffer** | Docs discuss only what Facebook-side *role* the user must hold; no custom-app step. |

These vendors run a hosted service. The consent screen implies an App-Reviewed app; none of them
states its own review status in user-facing docs, so that is inference from the flow rather than a
quote.

### 7.2 Camp B — the user brings their own app

**n8n is the direct precedent, and it is documented in Meta's own terms:**

> "Regardless of the authentication method you choose, you'll need a Meta for Developers account
> and a Meta app."
>
> "In Development mode, only people with a role on the app … can authenticate or generate tokens."
>
> "Your app must go through App Review if it will be used by someone who doesn't have a role on
> the app itself."
>
> — [docs.n8n.io — Facebook Graph API
> credentials](https://docs.n8n.io/integrations/builtin/credentials/facebookgraph)

n8n instructs the user to create a Business-type app in the Meta Developer dashboard and paste
either OAuth client credentials or a generated token. That is the whole flow. Shipped, at scale,
for years.

**Make sits in both camps.** Its Facebook Ads Campaign Management module connects through Make's
own app by default, but exposes an advanced toggle: "switch on 'show advanced settings' and enter
your facebook ads campaign client credentials … refer to the meta create an app documentation",
with redirect URI `https://www.integromat.com/oauth/cb/facebook`
([apps.make.com](https://apps.make.com/facebook-ads-cm)). Make's white-label documentation, for
resellers who must use their own app, warns: "Without completing Meta's app review and business
verification you have limited API access to Facebook. As a result, some modules may encounter
errors."
([developers.make.com](https://developers.make.com/white-label-documentation/install-and-configure-apps/facebook-and-other-meta-apps/steps-in-make))
— note that this warning is about a *reseller* serving *other people's* businesses, which is the
Advanced Access case, not ours.

### 7.3 Why Camp A is not available to this kit

The obvious read of §7.1 is "do what Zapier does". It cannot be done, for a reason that is
structural rather than procedural.

**A publicly cloned repository cannot hold an app secret.** Exchanging an OAuth code for a token,
and refreshing a long-lived token, both require `client_secret`
(["Make this call from your server, not a client. Your app secret is included in this API call, so
you should never make the request
client-side."](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived)).
A central shared app would therefore require a hosted token-broker service — a full product with
the security and liability posture of one, not a kit people clone. Camp B has no such problem: the
installer's own app secret and token stay on the installer's own machine.

---

## 8. What could not be established

Listed plainly, because each is a live risk rather than a tidy gap.

1. **What triggers the second-admin approval gate, and what a one-admin business experiences.**
   No primary source. The Business Help Centre system-users article would not yield body text and
   should be treated as unread.
2. **Whether the Business Management API chain (§3.3) works for a Development-mode app.** Meta's
   own pages contradict each other: "Only apps with Ads Management API standard access and above
   can be installed" versus "Have the Meta app go through an app review (and Business
   verification)". Unresolvable from documentation.
3. **Whether the Business Integration System User flow (§3.2) yields a never-expiring token for a
   business you own, in Development mode.** The conditions read as satisfiable; no confirmation.
4. **Whether the Ads CLI accepts a plain user access token.** Meta says it "requires a system user
   access token". If that is a hard check rather than a description, items 2 and 3 stop being
   nice-to-haves and become load-bearing.
5. **Whether `channel="chrome"` plus a persistent profile actually changes Meta's device gate.**
   No evidence found in either direction.
6. **Why `pages_show_list` and `leads_retrieval` were not offered** in the token dialog. The
   likeliest explanation is app product configuration rather than an access-level gate, since an
   access-level gate would have withheld the ads permissions too — but that is inference.
7. **Any Meta statement addressing distributed tooling** where many independent installers each
   run their own Development-mode app (§4.4).
8. **Whether Meta has ever permanently restricted an account for UI automation.** No primary
   evidence of any kind; only community anecdote (§2.3).

### The spike that settles 2, 3 and 4

One authenticated session, one dev-mode app, one hour:

1. Create a Business-type app, add the Marketing API product, add `http://localhost:8765/callback`
   as a valid OAuth redirect URI, leave it in Development mode.
2. Run Facebook Login for Business against it, scopes `ads_management,ads_read,business_management,
   pages_show_list,leads_retrieval`. **Does the consent screen render all five, or only three?**
   That single observation settles §4 empirically and explains observation 5.
3. Exchange for a long-lived token. Run `meta ads account list` with it. **Does the Ads CLI accept
   a user token?** (item 4)
4. With that token, walk §3.3 steps 1–4. **Does `POST /{system-user-id}/access_tokens` return a
   token, or an App Review error?** (item 2)
5. Create a Business login configuration and re-run login for a Business Integration System User
   token. **Never-expiring token, or an Advanced Access error?** (item 3)

Run it on a business with exactly one admin if one is available — that also probes item 1.

---

## 9. Primary sources

**Terms & policy**
- [Facebook Terms of Service §3.2, §4.2](https://www.facebook.com/terms.php)
- [Meta Platform Terms](https://developers.facebook.com/terms/dfc_platform_terms/)
- [Meta Developer Policies](https://developers.facebook.com/devpolicy/)
- [Automated Data Collection Terms](https://www.facebook.com/legal/automated_data_collection_terms)
- [Account Integrity — Community Standards](https://transparency.meta.com/policies/community-standards/account-integrity/)
- [Restricting accounts — enforcement](https://transparency.meta.com/enforcement/taking-action/restricting-accounts/)
- [How we combat scraping](https://about.fb.com/news/2021/04/how-we-combat-scraping/)

**Access levels & review**
- [Access levels — Standard vs Advanced](https://developers.facebook.com/docs/graph-api/overview/access-levels/)
- [App Review / release](https://developers.facebook.com/docs/development/release/)
- [Business Verification](https://developers.facebook.com/docs/development/release/business-verification)
- [Tech Providers](https://developers.facebook.com/docs/development/release/tech-providers/)
- [App roles](https://developers.facebook.com/docs/development/build-and-test/app-roles/)
- [`ads_management` permission reference](https://developers.facebook.com/docs/permissions/reference/ads_management)

**Tokens**
- [Marketing API authorization](https://developers.facebook.com/docs/marketing-api/overview/authorization/)
- [Facebook Login for Business](https://developers.facebook.com/docs/facebook-login/facebook-login-for-business)
- [Get long-lived access tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived)
- [Requiring HTTPS for Facebook Login (localhost carve-out)](https://developers.facebook.com/blog/post/2018/06/08/enforce-https-facebook-login/)
- [System users overview](https://developers.facebook.com/docs/business-management-apis/system-users/overview/)
- [Install apps, generate, refresh and revoke tokens](https://developers.facebook.com/docs/business-management-apis/system-users/install-apps-and-generate-tokens/)
- [`business/system_users` reference](https://developers.facebook.com/docs/graph-api/reference/business/system_users/)
- [`ad-account/assigned_users` reference](https://developers.facebook.com/docs/graph-api/reference/ad-account/assigned_users/)
- [Generate an access token for a system user (UI walkthrough)](https://developers.facebook.com/docs/marketing-api/collaborative-ads/managed-partner-ads/api-guide/prerequisites/generate-access-token-system-user/)
- [Ads CLI get started](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/get-started)
- [Ads Management Standard Access rename](https://developers.meta.com/blog/updates-to-ads-management-standard-access-feature/)

**Browser**
- [Playwright — Browsers / channels](https://playwright.dev/python/docs/browsers#google-chrome--microsoft-edge)
- [Playwright — `launch_persistent_context`](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context)
- [W3C WebDriver Level 2 § navigator.webdriver](https://www.w3.org/TR/webdriver2/#interface)
- [MDN — `Navigator.webdriver`](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/webdriver)

**Prior art**
- [n8n — Facebook Graph API credentials](https://docs.n8n.io/integrations/builtin/credentials/facebookgraph)
- [Make — Facebook Ads Campaign Management](https://apps.make.com/facebook-ads-cm)
- [Make white-label — Meta apps](https://developers.make.com/white-label-documentation/install-and-configure-apps/facebook-and-other-meta-apps/steps-in-make)
- [Zapier — Facebook Lead Ads permissions](https://help.zapier.com/hc/en-us/articles/8496040397965-What-permissions-do-I-need-to-use-Facebook-Lead-Ads-with-Zapier)
- [Supermetrics — Facebook Ads connection guide](https://docs.supermetrics.com/docs/facebook-ads-connection-guide)

**Labelled non-primary, cited once each:** the Rebrowser CDP `Runtime.enable` writeup (§6.2);
law-firm summaries of *Meta v. Bright Data* (§2.3). All ban claims encountered were community
anecdote or commercially interested vendor content and are cited nowhere in this document as
evidence.

---

## 10. What this means for the kit

### The recommendation: neither. Take the third option.

**Stop driving Meta's UI. Do not pursue App Review. Ship the n8n pattern: each installer creates
their own Development-mode Meta app by hand, once, in about five minutes — and from that point the
kit does everything through OAuth and the Graph API, and never touches a browser it controls
again.**

`mint-token` should be deleted, not fixed. `minting.py`'s `MANUAL_FALLBACK` — the path it treats
as the sad case — is the correct path, and Meta's own Ads CLI onboarding documents almost exactly
those steps (§3.4). The kit should promote it to the primary flow, extend it with app creation, and
then automate the *token* half through Facebook Login rather than through Playwright.

### The four findings that drive it

1. **App Review is not required, and Meta says so on four separate pages** (§4). "If your app will
   only be used by app users who have a role on the app itself you do not need to complete
   verification; these users can grant your app any permissions at any time and all features are
   always active." The Tech Providers page makes it explicit for `ads_management` specifically. An
   installer who creates their own app is its administrator by construction, so this is satisfied
   automatically, forever. **The "App Review once" fork is a false choice — there is nothing to
   review.**

2. **A public repo cannot hold an app secret, so the Zapier model is structurally unavailable**
   (§7.3). Choosing App Review means choosing to build and operate a hosted token broker with
   hundreds of businesses' ad credentials passing through it. That is a different product. Choosing
   the installer's own app means the secret and the token both stay on the installer's machine, and
   Selr holds nothing.

3. **UI automation is a Terms of Service breach that owning the account does not excuse** (§2.1) —
   "regardless of whether such automated access or collection is undertaken while logged in to a
   Facebook account" — and Meta's Account Integrity policy names the carve-out as "authorised
   routes", which is the API. There is **no primary evidence it causes bans**; the honest reading is
   checkpoints and identity-verification requests, which is exactly what was observed. But shipping
   a known ToS breach to hundreds of people who have not read the terms is not a decision to take on
   the grounds that enforcement looks survivable.

4. **The observed gates already break the promise, whatever the policy says** (§1, §5). A 7-day
   second-admin approval requirement is not detectable in advance, not resolvable from inside
   automation, and — for a solo business owner — of completely undocumented behaviour. A kit whose
   entire premise is "connected in one shot" cannot ship a path with a seven-day failure mode it
   cannot see coming.

### What the flow becomes

| | Who does it | How often |
|---|---|---|
| Create a Business-type Meta app, add Marketing API, set `http://localhost:PORT/callback` as a valid OAuth redirect URI, stay in Development mode | **Owner, in their own browser, guided step by step by Claude** | Once, ~5 min |
| Paste App ID and App Secret | Owner, once, into the kit | Once |
| OAuth consent → token | **Kit**, via a local HTTP listener; owner clicks one consent screen in their own browser | Once, plus renewal |
| Everything after | Kit, via CLI and MCP | — |

This is not more work than today. Today's design *already* requires a manually created BYO app for
the MCP fallback (`findings-and-decisions.md` §7), and already concedes that app creation "breaks
silently under automation". The change is to accept that concession once, up front, and let it pay
for the token as well — rather than doing the manual app walkthrough *and* a Playwright drive of
Business Settings.

Everything downstream survives intact: the Ads CLI, the MCP alongside it, the precedence rule,
`~/.meta-ads/.env` at mode 600, the idempotent live probe, the doctor script. Only the token
acquisition changes. Existing installers who already hold a working system user token change
nothing — the probe finds it and exits, as designed.

### The one thing to decide with a spike, not a document

Which token the OAuth flow lands on. In descending order of preference:

1. **Business Integration System User token** — never expires, one consent screen (§3.2).
2. **User token → Business Management API chain → never-expiring system user token** (§3.3).
3. **Long-lived user token, 60 days, renewed by re-consent** (§3.1).

All three are strictly better than the status quo, so this does not gate the decision — build for
(3) and treat (1) and (2) as upgrades. But run the §8 spike before writing the code, because it
costs an hour and it also produces the one observation that would falsify §4 if §4 is wrong: does a
Development-mode app's consent screen actually offer all five scopes?

### Two things to write down for installers

- The app stays in **Development mode permanently**. It is not a temporary state to be graduated
  out of. Switching to Live mode is what would start requiring App Review, and it also breaks the
  `http://localhost` redirect URI. The doctor script should check app mode and say so.
- The Marketing API tier ceiling (~20 writes / 5 min at Limited Access) is unchanged and still the
  real production constraint. It self-clears on usage, not review (§4.3).
