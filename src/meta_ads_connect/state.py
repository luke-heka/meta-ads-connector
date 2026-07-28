"""The small amount the kit remembers between runs.

Only facts that are expensive to re-derive and cheap to be wrong about — the
resolved interpreter, chiefly. Nothing here is ever treated as evidence that a
connection works; that question is only ever answered by asking Meta.
"""

from __future__ import annotations

import json
from typing import Any

from .config import Paths
from .tokens import DIR_MODE


def readState(paths: Paths) -> dict[str, Any]:
    try:
        loaded = json.loads(paths.state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def recordedInterpreter(paths: Paths) -> str | None:
    """The interpreter a previous ``install`` settled on, if there was one.

    Returned as a candidate to re-check, never as a fact: an interpreter can be
    uninstalled or upgraded out of support between runs, so whoever asks still
    has to confirm it before using it.
    """
    recorded = readState(paths).get("interpreter_path")
    return recorded if isinstance(recorded, str) and recorded else None


def writeState(paths: Paths, updates: dict[str, Any]) -> None:
    state = readState(paths)
    state.update(updates)
    paths.root.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
    paths.state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
