"""Copy ``skills/`` into both plugin directories; ``--check`` fails when they differ."""

import argparse
import filecmp
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "plugins" / host / "aipe-semiconductor-database" / "skills"
    for host in ("claude", "codex")
]


def differs(left: Path, right: Path) -> bool:
    if not right.is_dir():
        return True
    comparison = filecmp.dircmp(left, right)
    return bool(
        comparison.left_only
        or comparison.right_only
        or filecmp.cmpfiles(left, right, comparison.common_files, shallow=False)[1:] != ([], [])
        or any(differs(left / name, right / name) for name in comparison.common_dirs)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = [target for target in TARGETS if differs(ROOT / "skills", target)]
    if args.check:
        for target in stale:
            print(f"out of sync: {target.relative_to(ROOT)}")
        return int(bool(stale))
    for target in stale:
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(ROOT / "skills", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
