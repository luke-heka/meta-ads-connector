"""The token has spend authority. These tests are about the two ways it could
leak — wrong file permissions, and appearing in output — and about a re-run
replacing it rather than piling up a second one.
"""

from __future__ import annotations

import io
import os
import stat

from meta_ads_connect.commands.store_token import runStoreToken
from meta_ads_connect.config import TOKEN_ENV_VAR, Paths
from meta_ads_connect.context import Context
from meta_ads_connect.exits import Exit
from meta_ads_connect.tokens import readToken, writeToken

from .conftest import VALID_TOKEN, Recorder

SECOND_TOKEN = "EAAsecondtokenvaluethatisalsolongenoughtolooklikeacredential00"


def _store(ctx: Context, text: str) -> int:
    return runStoreToken(ctx, source=io.StringIO(text))


def test_writes_the_token_where_the_cli_will_find_it(ctx: Context, paths: Paths) -> None:
    assert _store(ctx, VALID_TOKEN) == Exit.OK
    assert readToken(paths) == VALID_TOKEN


def test_the_token_file_is_readable_only_by_its_owner(ctx: Context, paths: Paths) -> None:
    _store(ctx, VALID_TOKEN)

    assert stat.S_IMODE(paths.env_file.stat().st_mode) == 0o600


def test_the_containing_directory_is_reachable_only_by_its_owner(ctx: Context, paths: Paths) -> None:
    _store(ctx, VALID_TOKEN)

    assert stat.S_IMODE(paths.root.stat().st_mode) == 0o700


def test_tightens_permissions_on_a_directory_that_already_existed(
    ctx: Context, paths: Paths
) -> None:
    paths.root.mkdir(parents=True)
    os.chmod(paths.root, 0o755)

    _store(ctx, VALID_TOKEN)

    assert stat.S_IMODE(paths.root.stat().st_mode) == 0o700


def test_replaces_an_existing_token_rather_than_appending(ctx: Context, paths: Paths) -> None:
    """A second token in the same file would be ignored by the reader and
    leave the owner using a credential they thought they had replaced."""
    writeToken(paths, VALID_TOKEN)

    _store(ctx, SECOND_TOKEN)

    contents = paths.env_file.read_text()
    assert contents.count(TOKEN_ENV_VAR) == 1
    assert readToken(paths) == SECOND_TOKEN
    assert VALID_TOKEN not in contents


def test_never_prints_the_token(ctx: Context, out: Recorder, err: Recorder) -> None:
    _store(ctx, VALID_TOKEN)

    assert VALID_TOKEN not in out.text
    assert VALID_TOKEN not in err.text


def test_confirms_where_the_token_went_so_it_can_be_removed(
    ctx: Context, paths: Paths, out: Recorder
) -> None:
    _store(ctx, VALID_TOKEN)

    assert str(paths.env_file) in out.text
    assert "shell profile" in out.text
    assert "keychain" in out.text


def test_ignores_surrounding_whitespace_from_a_clipboard_paste(
    ctx: Context, paths: Paths
) -> None:
    _store(ctx, f"  {VALID_TOKEN}\n\n")

    assert readToken(paths) == VALID_TOKEN


def test_accepts_a_whole_env_line_being_pasted_by_mistake(ctx: Context, paths: Paths) -> None:
    """Storing `META_ACCESS_TOKEN=EAA...` verbatim would break silently later."""
    _store(ctx, f"{TOKEN_ENV_VAR}={VALID_TOKEN}")

    assert readToken(paths) == VALID_TOKEN


def test_refuses_an_empty_token_with_a_next_action(ctx: Context, paths: Paths, err: Recorder) -> None:
    assert _store(ctx, "   \n") == Exit.USAGE
    assert not paths.env_file.exists()
    assert "Next:" in err.text


def test_a_missing_token_file_reads_as_absent_not_as_an_error(paths: Paths) -> None:
    assert readToken(paths) is None


def test_a_token_file_with_no_token_in_it_reads_as_absent(paths: Paths) -> None:
    """A half-written file is the same problem as no file, with the same fix."""
    paths.root.mkdir(parents=True)
    paths.env_file.write_text("# nothing useful here\nSOMETHING_ELSE=1\n")

    assert readToken(paths) is None


def test_reads_a_quoted_value(paths: Paths) -> None:
    paths.root.mkdir(parents=True)
    paths.env_file.write_text(f'export {TOKEN_ENV_VAR}="{VALID_TOKEN}"\n')

    assert readToken(paths) == VALID_TOKEN
