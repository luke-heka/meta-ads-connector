"""``redact`` is the last line of defence on a credential with spend authority.

Everywhere else it is exercised transitively. Here it is driven directly,
because the case that actually matters is the one nobody writes a command test
for: text the kit did not author, relayed from Meta or from a subprocess, that
happens to contain the token.
"""

from __future__ import annotations

from meta_ads_connect.tokens import REDACTED, redact

SYSTEM_USER_TOKEN = "EAAGm0PX4ZCpsBO1ZBqZAZBZC9ZBk8ZBZAqZC7dZBZAZC0ZBZAqZC9ZBZAZC1ZBZAqZC"
LONG_OPAQUE = "a" * 80


def test_removes_the_known_token() -> None:
    scrubbed = redact(f"Bearer {SYSTEM_USER_TOKEN}", token=SYSTEM_USER_TOKEN)

    assert SYSTEM_USER_TOKEN not in scrubbed
    assert REDACTED in scrubbed


def test_removes_a_meta_shaped_token_nobody_told_it_about() -> None:
    """The realistic leak: an error we relay, carrying a credential we were
    never handed."""
    scrubbed = redact(f"Invalid OAuth access token: {SYSTEM_USER_TOKEN}")

    assert SYSTEM_USER_TOKEN not in scrubbed
    assert REDACTED in scrubbed


def test_removes_anything_long_enough_to_be_a_credential() -> None:
    """So a rotated token format does not silently start leaking."""
    scrubbed = redact(f"token={LONG_OPAQUE}")

    assert LONG_OPAQUE not in scrubbed


def test_removes_every_occurrence_not_just_the_first() -> None:
    text = f"{SYSTEM_USER_TOKEN} ... again {SYSTEM_USER_TOKEN}"

    assert SYSTEM_USER_TOKEN not in redact(text, token=SYSTEM_USER_TOKEN)


def test_ignores_surrounding_whitespace_on_the_known_token() -> None:
    scrubbed = redact(f"value: {SYSTEM_USER_TOKEN}", token=f"  {SYSTEM_USER_TOKEN}\n")

    assert SYSTEM_USER_TOKEN not in scrubbed


def test_leaves_ordinary_output_alone() -> None:
    """Redaction that eats real output makes doctor useless."""
    text = "✓ Meta Ads CLI — Version 1.1.0.\n✓ Ad accounts — Selr AI (act_111)"

    assert redact(text) == text


def test_leaves_account_ids_alone() -> None:
    assert redact("act_1234567890123456") == "act_1234567890123456"


def test_handles_empty_input() -> None:
    assert redact("") == ""


def test_a_none_token_still_scrubs_by_shape() -> None:
    assert SYSTEM_USER_TOKEN not in redact(SYSTEM_USER_TOKEN, token=None)
