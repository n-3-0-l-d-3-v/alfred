#!/usr/bin/env python3
"""Build the extension for Chrome and Firefox — no Node, no npm.

Copies `src/` into `dist/<browser>/`, drops in the right manifest, and
validates the result. Run:  python build.py
"""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"

TARGETS = {"chrome": "manifest.chrome.json", "firefox": "manifest.firefox.json"}

# Files that must exist in every build (referenced by the manifests).
REQUIRED = [
    "background.js",
    "lib/ext.js",
    "lib/api.js",
    "content/platforms.js",
    "content/leetcode-adapter.js",
    "content/platform-generic.js",
    "content/content.js",
    "content/page-bridge.js",
    "panel/panel.html",
    "panel/panel.css",
    "panel/panel.js",
]


def validate_manifest(path: Path, browser: str) -> list[str]:
    """Return a list of problems (empty == valid)."""
    problems: list[str] = []
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{path.name}: invalid JSON — {e}"]

    if m.get("manifest_version") != 3:
        problems.append(f"{browser}: manifest_version must be 3")
    for key in ("name", "version", "description"):
        if not m.get(key):
            problems.append(f"{browser}: missing '{key}'")

    if browser == "chrome":
        if "service_worker" not in m.get("background", {}):
            problems.append("chrome: background.service_worker is required on MV3")
        if "side_panel" not in m:
            problems.append("chrome: side_panel missing")
        if "sidePanel" not in m.get("permissions", []):
            problems.append("chrome: 'sidePanel' permission missing")
    else:
        if "scripts" not in m.get("background", {}):
            problems.append("firefox: background.scripts is required (no service_worker support)")
        if "sidebar_action" not in m:
            problems.append("firefox: sidebar_action missing")
        gecko = m.get("browser_specific_settings", {}).get("gecko", {})
        if not gecko.get("id"):
            problems.append("firefox: browser_specific_settings.gecko.id is required to install")

    # every referenced script must actually exist
    referenced = set(m.get("background", {}).get("scripts", []))
    sw = m.get("background", {}).get("service_worker")
    if sw:
        referenced.add(sw)
    for cs in m.get("content_scripts", []):
        referenced.update(cs.get("js", []))
    panel = m.get("side_panel", {}).get("default_path") or m.get("sidebar_action", {}).get("default_panel")
    if panel:
        referenced.add(panel)
    # Injected into the page world at runtime, so it is never listed as a
    # content script — but it still has to ship, and a missing entry here is a
    # silent degradation rather than a crash.
    for entry in m.get("web_accessible_resources", []):
        referenced.update(entry.get("resources", []))
    for rel in sorted(referenced):
        if not (SRC / rel).exists():
            problems.append(f"{browser}: manifest references missing file '{rel}'")

    return problems


def build(browser: str, manifest_name: str, make_zip: bool) -> list[str]:
    out = DIST / browser
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for item in SRC.iterdir():
        if item.name.startswith("manifest."):
            continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, out / item.name)

    shutil.copy2(SRC / manifest_name, out / "manifest.json")

    missing = [r for r in REQUIRED if not (out / r).exists()]
    problems = [f"{browser}: missing required file '{r}'" for r in missing]

    if make_zip:
        zpath = DIST / f"leetlearn-{browser}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for p in out.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(out))
        print(f"  packaged  {zpath.relative_to(ROOT)}")

    return problems


def main() -> int:
    make_zip = "--zip" in sys.argv
    all_problems: list[str] = []

    for browser, manifest_name in TARGETS.items():
        all_problems += validate_manifest(SRC / manifest_name, browser)
        all_problems += build(browser, manifest_name, make_zip)
        print(f"  built     dist/{browser}/")

    if all_problems:
        print("\nPROBLEMS:")
        for p in all_problems:
            print(f"  ✗ {p}")
        return 1

    print("\nOK — both builds valid.")
    print("  Chrome : chrome://extensions -> Developer mode -> Load unpacked -> apps/extension/dist/chrome")
    print("  Firefox: about:debugging#/runtime/this-firefox -> Load Temporary Add-on -> apps/extension/dist/firefox/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
