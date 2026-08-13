"""Author the tiny, fully-synthetic seed IFC models used by the demo.

The models are generated from scratch with the IfcOpenShell authoring API (a few
IfcWall / IfcSlab / IfcBeam / IfcSpace entities), so they carry NO third-party
data and are license-clean to redistribute. They are checked in under
`services/api/seed/` for inspection and BYO testing; the running app can also
author them on demand (POST /projects/{slug}/ingest-samples).

Run:  services/api/.venv/bin/python scripts/make_seed_ifc.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.repo.ifc_engine import author_seed_models  # noqa: E402


def main() -> int:
    out_dir = API_ROOT / "seed"
    out_dir.mkdir(parents=True, exist_ok=True)
    for discipline, data in author_seed_models().items():
        path = out_dir / f"seed-{discipline}.ifc"
        path.write_bytes(data)
        sys.stdout.write(f"wrote {path.relative_to(REPO_ROOT)} ({len(data)} bytes)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
