"""Run the heavy IfcOpenShell pass in an isolated subprocess with a timeout.

Mirrors the worker-isolation stance of other native-engine samples: the parse +
geometry + analyze work executes in a child process (`app.repo.ifc_child`), so a
runaway or crashing native geometry pass surfaces here as a typed error instead
of taking down the FastAPI worker. All heavy `ifcopenshell` imports stay in the
child; this module only orchestrates the process boundary.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# services/api — the cwd the child needs so `import app...` resolves.
API_ROOT = Path(__file__).resolve().parents[2]

# Generous per-model ceiling: the synthetic seed models finish in well under a
# second; a real multi-thousand-element model still has a hard bound so one bad
# model can't hang a run forever.
DEFAULT_TIMEOUT_SECONDS = 180


class IfcParseError(Exception):
    """The child ran to completion but reported a parse/geometry failure."""


class IfcTimeout(Exception):
    """The child exceeded the hard wall-clock timeout and was killed."""


class IfcCrashed(Exception):
    """The child died on a signal (e.g. a native segfault) or emitted no result."""


@dataclass
class WorkerResult:
    mesh_count: int = 0
    element_count: int = 0
    space_count: int = 0
    storey_count: int = 0
    type_counts: dict[str, int] = field(default_factory=dict)


def run_model(
    ifc_path: str,
    out_dir: str,
    detail: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> WorkerResult:
    """Parse + mesh + analyze one model in a child process. Raises on failure."""
    cmd = [sys.executable, "-m", "app.repo.ifc_child", ifc_path, out_dir, detail]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(API_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise IfcTimeout(
            f"IfcOpenShell timed out after {timeout}s on {Path(ifc_path).name}"
        ) from exc

    # A negative return code means the process was killed by a signal — the
    # classic native crash. Distinguish it from an orderly non-zero exit.
    if proc.returncode < 0:
        raise IfcCrashed(
            f"IfcOpenShell child crashed (signal {-proc.returncode}) on "
            f"{Path(ifc_path).name}"
        )

    summary = _parse_summary(proc.stdout)
    if summary is None:
        detail_msg = (proc.stderr or proc.stdout or "no output").strip()[:400]
        raise IfcCrashed(f"IfcOpenShell child produced no result: {detail_msg}")

    if not summary.get("ok"):
        raise IfcParseError(summary.get("error", "unknown IfcOpenShell failure"))

    return WorkerResult(
        mesh_count=summary.get("mesh_count", 0),
        element_count=summary.get("element_count", 0),
        space_count=summary.get("space_count", 0),
        storey_count=summary.get("storey_count", 0),
        type_counts=summary.get("type_counts", {}),
    )


def _parse_summary(stdout: str) -> dict | None:
    """The child prints one JSON line last; tolerate leading log noise."""
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None
