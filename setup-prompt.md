# Setup prompt

Copy everything inside the box below and paste it into Claude Code as one message.
That is the whole install. Pasting it again later is also how you update to the
latest version.

This prompt only installs the kit onto your machine. It does not touch your Meta
account — connecting happens in your next session, and you approve it yourself.

```text
Install the Meta Ads connector kit on this machine. Follow these steps exactly, in order, and do nothing beyond them.

1. Check that you are running as Claude Code with access to a terminal and a ~/.claude/skills folder. If you are not — for example this is the Claude desktop or web app — stop here and tell me to open Claude Code and paste this prompt there. If I only use the desktop app, tell me to instead add the connector under Settings → Connectors → Add custom connector, using the URL https://mcp.facebook.com/ads
2. Check that git is available. If it is not, stop and tell me the one thing to install (git), with the easiest way to get it on my operating system.
3. Clone https://github.com/lukeselr/meta-ads-connector into ~/meta-ads-connector. If that folder already exists, run git pull inside it instead of cloning a second copy.
4. Create ~/.claude/skills if it does not exist, then copy ~/meta-ads-connector/skills/meta-ads-connect into ~/.claude/skills/, replacing any earlier copy.
5. Optional, and allowed to fail: install the helper package with pip install ~/meta-ads-connector. If this fails for any reason — no Python, a managed environment, anything at all — do not try to fix it. Note that the optional helper did not install, and carry on: the kit works without it.
6. Finish by telling me, in plain language: exactly what you installed and where; that I must start a NEW Claude session before the skill exists; and that in that new session I should type /meta-ads-connect, or just say "connect my Meta ads".

Do not connect to anything, do not open a browser, do not touch my Meta account, and do not create or store any token or credential. Installing and connecting are separate steps — this prompt only installs.
```

The Skool post reproduces this block verbatim, and so does the README. If they
ever disagree, this file is the source of truth — `tests/test_setup_prompt.py`
holds them in step.
