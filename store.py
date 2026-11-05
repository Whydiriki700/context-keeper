"""Context Keeper core: rolling session checkpoints on disk.

Pure stdlib, no Hermes imports. A checkpoint is a small JSON record:

  {ts, session_id, summary, actions: [...], files: [...], tools: {name: n}}

Checkpoints live at <HERMES_HOME>/context-keeper/latest.json (the one the
next session restores) plus a bounded history in checkpoints.jsonl.
Argument values are never stored wholesale: actions keep the tool name and
a short, redacted hint of what it touched, nothing more.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_MAX_HINT = 160
_SENSITIVE_KEYS = ("key", "token", "secret", "password", "auth", "credential")
_PATH_KEYS = ("path", "file", "filename", "filepath", "target", "dest", "destination")


def hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return Path(get_hermes_home())
    except Exception:
        pass
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    return Path.home() / ".hermes"


def data_dir() -> Path:
    path = hermes_home() / "context-keeper"
    path.mkdir(parents=True, exist_ok=True)
    return path


def extract_files(args: Any) -> List[str]:
    """Pull file-ish paths out of a tool call's arguments, shallowly."""
    found: List[str] = []
    if isinstance(args, dict):
        for key, value in args.items():
            low = str(key).lower()
            if any(word in low for word in _SENSITIVE_KEYS):
                continue
            if any(word in low for word in _PATH_KEYS) and isinstance(value, str):
                found.append(value)
            elif isinstance(value, dict):
                found.extend(extract_files(value))
    return found[:10]


def action_hint(tool_name: str, args: Any) -> str:
    files = extract_files(args)
    hint = tool_name
    if files:
        hint += " -> " + ", ".join(files[:3])
    return hint[:_MAX_HINT]


def save_checkpoint(checkpoint: Dict[str, Any], keep: int = 50) -> Dict[str, Any]:
    line = json.dumps(checkpoint, ensure_ascii=False, default=str)
    with _LOCK:
        base = data_dir()
        with open(base / "checkpoints.jsonl", "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        tmp = base / "latest.json.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(line + "\n")
        tmp.replace(base / "latest.json")
        rows = read_history(limit=100000)
        if len(rows) > keep:
            trimmed = rows[-keep:]
            with open(base / "checkpoints.jsonl", "w", encoding="utf-8") as handle:
                for row in trimmed:
                    handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return checkpoint


def read_latest() -> Optional[Dict[str, Any]]:
    path = data_dir() / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_history(limit: int = 20) -> List[Dict[str, Any]]:
    path = data_dir() / "checkpoints.jsonl"
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def format_checkpoint(cp: Optional[Dict[str, Any]]) -> str:
    if not cp:
        return "No Context Keeper checkpoint exists yet."
    lines = []
    ts = cp.get("ts")
    if ts:
        import time as _time

        lines.append("Saved: " + _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(ts)))
    if cp.get("summary"):
        lines.append("Summary: " + str(cp["summary"]))
    tools = cp.get("tools") or {}
    if tools:
        lines.append("Tools used: " + ", ".join(f"{k} x{v}" for k, v in sorted(tools.items())))
    files = cp.get("files") or []
    if files:
        lines.append("Files touched: " + ", ".join(str(f) for f in files[-10:]))
    actions = cp.get("actions") or []
    if actions:
        lines.append("Recent actions:")
        for action in actions[-8:]:
            lines.append("- " + str(action))
    return "\n".join(lines)
