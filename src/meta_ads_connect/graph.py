"""Outbound HTTP to Meta's Graph API.

The second of exactly two faked boundaries. There is only ever one API — the
Graph / Marketing API — and both official transports sit on top of it, so this
module is how the kit checks whether a token is genuinely live rather than
merely present on disk.

The kit does not use the Graph API to *manage* ads; that is the Ads CLI's job.
This is used only where the CLI cannot help: verifying a token against Meta and
repairing Business Manager / ad account assignment.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping, Protocol

from .config import GRAPH_API_VERSION, GRAPH_HOST

#: Graph error codes meaning "this token is no good", as opposed to "try again".
AUTH_ERROR_CODES = frozenset({102, 190, 200, 2500})

#: Throttling. Distinct from an auth failure because the right response is to
#: wait, not to re-mint a token.
RATE_LIMIT_ERROR_CODES = frozenset({4, 17, 32, 613, 80000, 80004})


class GraphError(Exception):
    """Any error Meta returned as a structured Graph error."""

    def __init__(self, message: str, *, code: int | None = None, subcode: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.subcode = subcode


class GraphAuthError(GraphError):
    """The token was rejected. Re-minting is the fix."""


class GraphRateLimitError(GraphError):
    """Meta is throttling. Waiting is the fix."""


class GraphNetworkError(GraphError):
    """Never reached Meta at all. Says nothing about the token."""


class GraphClient(Protocol):
    def get(
        self, path: str, *, token: str, params: Mapping[str, str] | None = None
    ) -> dict[str, Any]: ...

    def post(
        self, path: str, *, token: str, data: Mapping[str, str] | None = None
    ) -> dict[str, Any]: ...


class HttpGraphClient:
    """urllib-backed client. No third-party runtime dependency."""

    def __init__(self, *, host: str = GRAPH_HOST, version: str = GRAPH_API_VERSION, timeout: float = 20.0) -> None:
        self.host = host.rstrip("/")
        self.version = version
        self.timeout = timeout

    def get(
        self, path: str, *, token: str, params: Mapping[str, str] | None = None
    ) -> dict[str, Any]:
        query = urllib.parse.urlencode(dict(params or {}))
        url = f"{self._url(path)}?{query}" if query else self._url(path)
        return self._send(urllib.request.Request(url, method="GET"), token)

    def post(
        self, path: str, *, token: str, data: Mapping[str, str] | None = None
    ) -> dict[str, Any]:
        body = urllib.parse.urlencode(dict(data or {})).encode("utf-8")
        request = urllib.request.Request(self._url(path), data=body, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        return self._send(request, token)

    def _url(self, path: str) -> str:
        return f"{self.host}/{self.version}/{path.lstrip('/')}"

    def _send(self, request: urllib.request.Request, token: str) -> dict[str, Any]:
        # In the Authorization header rather than an `access_token` query
        # parameter, so the token cannot end up in a proxy or server log.
        request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return _decodeBody(response.read())
        except urllib.error.HTTPError as exc:
            raise _errorFromResponse(_decodeBody(exc.read()), status=exc.code) from None
        except urllib.error.URLError as exc:
            raise GraphNetworkError(f"could not reach {self.host}: {exc.reason}") from None
        except TimeoutError:
            raise GraphNetworkError(f"timed out reaching {self.host}") from None


def _decodeBody(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"error": {"message": "Meta returned a response that was not JSON."}}
    return parsed if isinstance(parsed, dict) else {"data": parsed}


def _errorFromResponse(body: Mapping[str, Any], *, status: int) -> GraphError:
    error = body.get("error")
    if not isinstance(error, Mapping):
        return GraphError(f"Meta returned HTTP {status}.", code=status)

    message = str(error.get("message") or f"Meta returned HTTP {status}.")
    code = _asInt(error.get("code"))
    subcode = _asInt(error.get("error_subcode"))

    if code in AUTH_ERROR_CODES or status == 401:
        return GraphAuthError(message, code=code, subcode=subcode)
    if code in RATE_LIMIT_ERROR_CODES or status == 429:
        return GraphRateLimitError(message, code=code, subcode=subcode)
    return GraphError(message, code=code, subcode=subcode)


def _asInt(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
