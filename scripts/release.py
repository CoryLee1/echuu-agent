"""Export distributable copies of echuu/ as SDK and public release artifacts.

Run from echuu-agent/ root:
    python scripts/release.py --target sdk
    python scripts/release.py --target public

Outputs to:
    echuu-agent/dist/echuu-sdk/
    echuu-agent/dist/echuu-public/
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # echuu-agent/
SRC = ROOT / "echuu"
DIST = ROOT / "dist"

LICENSE_HEADERS = {
    "sdk": '"""Echuu SDK — internal release.\n\nCopyright (c) 2026 Anngel LLC. All rights reserved.\n"""\n',
    "public": '"""Echuu — AI VTuber Auto-Live System.\n\nPublic release for hackathon / demos.\n"""\n',
}

def copy_package(target: str) -> Path:
    out = DIST / f"echuu-{target}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(SRC, out / "echuu")
    # Rewrite __init__.py header
    init = out / "echuu" / "__init__.py"
    existing = init.read_text(encoding="utf-8")
    # Drop existing docstring (first """...""" block)
    if existing.startswith('"""'):
        end = existing.find('"""', 3)
        existing = existing[end + 3 :].lstrip("\n")
    init.write_text(LICENSE_HEADERS[target] + existing, encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["sdk", "public"], required=True)
    args = parser.parse_args()
    out = copy_package(args.target)
    print(f"Wrote release: {out}")


if __name__ == "__main__":
    main()
