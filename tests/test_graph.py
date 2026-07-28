"""The real Graph client, driven directly.

Everywhere else the suite injects a fake, which means the mapping from Meta's
error shapes to this kit's exception types is otherwise unverified — and that
mapping is what decides whether a probe says "re-mint your token" or "wait a
minute". Getting it backwards would send an owner to re-mint over a rate limit.

No network is touched: the client's transport is driven through a stub opener.
"""

from __future__ import annotations

import io
import json
import urllib.error
from typing import Any

import pytest

from meta_ads_connect.graph import (
    GraphAuthError,
    GraphError,
    GraphNetworkError,
    GraphRateLimitError,
    HttpGraphClient,
    _decodeBody,
    _errorFromResponse,
)


def _metaError(*, code: int | None = None, subcode: int | None = None, message: str = "boom") -> dict[str, Any]:
    error: dict[str, Any] = {"message": message}
    if code is not None:
        error["code"] = code
    if subcode is not None:
        error["error_subcode"] = subcode
    return {"error": error}


@pytest.mark.parametrize("code", [102, 190, 200, 2500])
def test_meta_auth_codes_become_an_auth_error(code: int) -> None:
    """These are the ones that mean "re-mint", not "retry"."""
    raised = _errorFromResponse(_metaError(code=code), status=400)

    assert isinstance(raised, GraphAuthError)
    assert raised.code == code


@pytest.mark.parametrize("code", [4, 17, 32, 613, 80000, 80004])
def test_meta_throttling_codes_become_a_rate_limit_error(code: int) -> None:
    """Distinct from an auth failure, because the fix is waiting, not re-minting."""
    raised = _errorFromResponse(_metaError(code=code), status=400)

    assert isinstance(raised, GraphRateLimitError)
    assert not isinstance(raised, GraphAuthError)


def test_a_401_is_an_auth_error_even_without_a_recognised_code() -> None:
    assert isinstance(_errorFromResponse(_metaError(), status=401), GraphAuthError)


def test_a_429_is_a_rate_limit_even_without_a_recognised_code() -> None:
    assert isinstance(_errorFromResponse(_metaError(), status=429), GraphRateLimitError)


def test_an_unrecognised_code_stays_a_plain_graph_error() -> None:
    """Guessing "your token is bad" from an unknown code would send the owner
    to re-mint a credential that was never the problem."""
    raised = _errorFromResponse(_metaError(code=100, message="Unknown edge"), status=400)

    assert type(raised) is GraphError
    assert raised.message == "Unknown edge"


def test_the_error_subcode_is_carried_through() -> None:
    raised = _errorFromResponse(_metaError(code=190, subcode=463), status=400)

    assert raised.subcode == 463


def test_a_response_with_no_error_object_still_produces_something_actionable() -> None:
    raised = _errorFromResponse({"nonsense": True}, status=500)

    assert isinstance(raised, GraphError)
    assert "500" in raised.message


def test_a_non_json_body_does_not_crash_the_decoder() -> None:
    assert "error" in _decodeBody(b"<html>502 Bad Gateway</html>")


def test_an_empty_body_decodes_to_nothing() -> None:
    assert _decodeBody(b"") == {}


def test_a_json_list_body_is_wrapped_rather_than_dropped() -> None:
    assert _decodeBody(b'[{"id": "act_1"}]') == {"data": [{"id": "act_1"}]}


# --- transport -------------------------------------------------------------


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def test_a_successful_call_returns_the_decoded_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"data": [{"id": "act_111", "name": "Selr AI"}]}
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: _Response(json.dumps(payload).encode()),
    )

    assert HttpGraphClient().get("/me/adaccounts", token="t") == payload


def test_the_token_travels_in_a_header_not_the_query_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A token in a query parameter ends up in proxy and server logs."""
    seen: dict[str, Any] = {}

    def capture(request: Any, timeout: float | None = None) -> _Response:
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        return _Response(b"{}")

    monkeypatch.setattr("urllib.request.urlopen", capture)

    HttpGraphClient().get("/me/adaccounts", token="secret-token", params={"fields": "id"})

    assert seen["auth"] == "Bearer secret-token"
    assert "secret-token" not in seen["url"]
    assert "access_token" not in seen["url"]


def test_the_pinned_graph_version_is_in_the_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unpinned version silently degrades to the next oldest rather than erroring."""
    seen: dict[str, str] = {}

    def capture(request: Any, timeout: float | None = None) -> _Response:
        seen["url"] = request.full_url
        return _Response(b"{}")

    monkeypatch.setattr("urllib.request.urlopen", capture)

    HttpGraphClient().get("/me/adaccounts", token="t")

    assert "/v25.0/" in seen["url"]


def test_an_http_error_is_mapped_rather_than_raised_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    def raiseHttpError(request: Any, timeout: float | None = None) -> None:
        raise urllib.error.HTTPError(
            url="https://graph.facebook.com",
            code=400,
            msg="Bad Request",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(json.dumps(_metaError(code=190)).encode()),
        )

    monkeypatch.setattr("urllib.request.urlopen", raiseHttpError)

    with pytest.raises(GraphAuthError):
        HttpGraphClient().get("/me/adaccounts", token="t")


def test_an_unreachable_host_becomes_a_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Which must never be reported as a bad token."""

    def raiseUrlError(request: Any, timeout: float | None = None) -> None:
        raise urllib.error.URLError("Name or service not known")

    monkeypatch.setattr("urllib.request.urlopen", raiseUrlError)

    with pytest.raises(GraphNetworkError):
        HttpGraphClient().get("/me/adaccounts", token="t")


def test_a_timeout_becomes_a_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raiseTimeout(request: Any, timeout: float | None = None) -> None:
        raise TimeoutError

    monkeypatch.setattr("urllib.request.urlopen", raiseTimeout)

    with pytest.raises(GraphNetworkError):
        HttpGraphClient().get("/me/adaccounts", token="t")


def test_a_post_sends_a_form_encoded_body(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def capture(request: Any, timeout: float | None = None) -> _Response:
        seen["data"] = request.data
        seen["method"] = request.get_method()
        return _Response(b'{"success": true}')

    monkeypatch.setattr("urllib.request.urlopen", capture)

    HttpGraphClient().post("/act_1/assigned_users", token="t", data={"user": "6100"})

    assert seen["method"] == "POST"
    assert b"user=6100" in seen["data"]
