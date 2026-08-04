"""Guard the extension manifests from the Python suite, so one `pytest` run
catches cross-browser packaging regressions too.

Deep JS logic lives in `apps/extension/tests/adapter.test.mjs` (`node --test`).
"""

import importlib.util
import json
from pathlib import Path

import pytest

EXT = Path(__file__).resolve().parents[2] / "extension"
SRC = EXT / "src"


def _load_build_module():
    spec = importlib.util.spec_from_file_location("ext_build", EXT / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pytestmark = pytest.mark.skipif(not (EXT / "build.py").exists(), reason="extension not present")


@pytest.mark.parametrize("browser,manifest", [("chrome", "manifest.chrome.json"), ("firefox", "manifest.firefox.json")])
def test_manifest_is_valid(browser, manifest):
    build = _load_build_module()
    problems = build.validate_manifest(SRC / manifest, browser)
    assert problems == [], "\n".join(problems)


def test_both_browsers_share_name_and_version():
    chrome = json.loads((SRC / "manifest.chrome.json").read_text(encoding="utf-8"))
    firefox = json.loads((SRC / "manifest.firefox.json").read_text(encoding="utf-8"))
    assert chrome["name"] == firefox["name"]
    assert chrome["version"] == firefox["version"]
    assert chrome["content_scripts"][0]["js"] == firefox["content_scripts"][0]["js"]


def test_host_permissions_are_narrow():
    """Chrome Web Store review punishes broad host permissions — keep them tight."""
    for manifest in ("manifest.chrome.json", "manifest.firefox.json"):
        m = json.loads((SRC / manifest).read_text(encoding="utf-8"))
        for perm in m["host_permissions"]:
            assert "<all_urls>" not in perm, manifest
            assert perm.startswith(("https://leetcode.com/", "http://localhost")), perm


def test_firefox_does_not_use_service_worker():
    """Firefox MV3 has no service_worker support — it must use background.scripts."""
    m = json.loads((SRC / "manifest.firefox.json").read_text(encoding="utf-8"))
    assert "service_worker" not in m["background"]
    assert m["background"]["scripts"]
