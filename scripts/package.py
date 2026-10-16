"""Build an installable plugin ZIP: dist/arcskin-<version>.zip.

Usage:  python scripts/package.py
"""

import configparser
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = "arcskin"


def plugin_version() -> str:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / PLUGIN / "metadata.txt", encoding="utf-8")
    return cfg["general"]["version"]


def main() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "i18n.py"),
                    "compile"], check=True)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"{PLUGIN}-{plugin_version()}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted((ROOT / PLUGIN).rglob("*")):
            if (path.is_file() and "__pycache__" not in path.parts
                    and path.suffix != ".ts"):
                zf.write(path, path.relative_to(ROOT).as_posix())
        zf.write(ROOT / "LICENSE", f"{PLUGIN}/LICENSE")
    print(out)


if __name__ == "__main__":
    main()
