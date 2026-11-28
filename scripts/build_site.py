"""Build the AIPE Semiconductor Data Explorer: a static, read-only site over the committed records.

    python scripts/build_site.py --out _site

Reads the data only through ``aipe_devices.api.Database`` (the same queries as the MCP
server) and writes only to ``--out``: ``data/summary.json``, ``data/sources.json``,
``data/devices.json``, ``data/contributions.json`` and one ``data/devices/<device_id>.json`` per device, plus the
frontend from ``site/``. It never modifies ``data/``, downloads nothing and performs no
fitting, interpolation or derivation. Every device file carries its sources and their
rights status, which the page shows.
"""

import argparse
import datetime
import json
import shutil
import subprocess
from pathlib import Path

from aipe_devices.api import COLLECTIONS, Database

ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    path.write_text(text, encoding="utf-8")


def build(out: Path, data: Path | None = None, contributed: Path | None = None) -> dict:
    database = Database(data or ROOT / "data", contributed=contributed)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "site", out, ignore=shutil.ignore_patterns("README.md"))
    devices = database.list_devices(limit=1000)
    summary = database.summary()
    summary["reviewed_devices"] = sum(d["review_status"] != "unreviewed" for d in devices)
    summary["build"] = {
        "commit": _git("rev-parse", "HEAD"),
        "date": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
    }
    _write(out / "data/summary.json", summary)
    _write(out / "data/sources.json", database.list_sources())
    _write(out / "data/devices.json", devices)
    _write(
        out / "data/contributions.json",
        [database.get_contribution(c["contribution_id"]) for c in database.list_contributions()],
    )
    for item in devices:
        device = database.export_device(item["device_id"])
        folder = COLLECTIONS[device["collection"]][0]
        device["record_path"] = f"data/{folder}/{device['device_id']}.json"
        _write(out / "data/devices" / f"{device['device_id']}.json", device)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return {"devices": len(devices), "out": str(out)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    parser.add_argument(
        "--contributed", type=Path, help="Preview only: read contributions from this directory"
    )
    args = parser.parse_args()
    print(json.dumps(build(args.out, contributed=args.contributed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
