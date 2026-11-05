"""Scenario tests for the Context Keeper core store.

Run: python3 tests/test_store.py   (no dependencies)
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["HERMES_HOME"] = tempfile.mkdtemp(prefix="ck-home-")

import store  # noqa: E402

CASES = []


def case(name):
    def wrap(fn):
        CASES.append((name, fn))
        return fn

    return wrap


@case("no checkpoint reads back as none")
def _():
    assert store.read_latest() is None
    assert "No Context Keeper checkpoint" in store.format_checkpoint(None)


@case("save then read latest round trips")
def _():
    cp = {
        "ts": 1700000000.0,
        "session_id": "s1",
        "summary": "Halfway through the gateway fix.",
        "tools": {"read": 3, "edit": 1},
        "files": ["gateway/server.js"],
        "actions": ["read -> gateway/server.js"],
    }
    store.save_checkpoint(cp)
    latest = store.read_latest()
    assert latest["summary"] == cp["summary"] and latest["session_id"] == "s1"
    text = store.format_checkpoint(latest)
    assert "gateway/server.js" in text and "read x3" in text


@case("file extraction pulls paths and skips credential keys")
def _():
    args = {"path": "src/app.py", "api_key": "sk-should-not-appear", "nested": {"file": "a.txt"}}
    files = store.extract_files(args)
    assert "src/app.py" in files and "a.txt" in files
    hint = store.action_hint("edit", args)
    assert "sk-should-not-appear" not in hint and "src/app.py" in hint


@case("history is bounded by keep")
def _():
    for i in range(10):
        store.save_checkpoint({"ts": float(i), "session_id": f"s{i}", "summary": f"n{i}"}, keep=5)
    rows = store.read_history(limit=100)
    assert len(rows) == 5 and rows[-1]["summary"] == "n9"


def main() -> int:
    failed = 0
    for name, fn in CASES:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    print(f"{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
