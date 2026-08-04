# LeetLearn Extension (Chrome + Firefox)

One source tree, two builds. **No Node or npm toolchain is required to build** —
`build.py` does the assembly. (Node is only used to *run the tests*, and even
then only Node's built-in runner, no packages.)

## Build

```bash
cd apps/extension
python build.py          # -> dist/chrome/ and dist/firefox/
python build.py --zip    # also produce store-upload zips
```

The build validates both manifests and fails loudly if a manifest references a
file that doesn't exist.

## Load it

**Chrome** — `chrome://extensions` → enable *Developer mode* → *Load unpacked* →
select `apps/extension/dist/chrome`.

**Firefox** — `about:debugging#/runtime/this-firefox` → *Load Temporary Add-on* →
select `apps/extension/dist/firefox/manifest.json`.

> Firefox loads temporary add-ons only until you restart the browser. That's
> normal for unsigned development builds.

Start the backend first (`cd apps/api && uvicorn leetlearn.main:app --reload`),
then open a LeetCode problem and open the side panel (Chrome) or sidebar (Firefox).

### Firefox permission gotcha

Firefox treats MV3 `host_permissions` as **optional** — they are not granted at
install. If the panel says it can't reach the server, open the add-on's
permission settings and allow access for `leetcode.com` and `localhost`.

## Test

```bash
node --test tests/adapter.test.mjs   # 14 tests, no npm install
```

Manifest validity is additionally covered by the Python suite
(`apps/api/tests/test_extension_manifests.py`), so one `pytest` run guards
packaging too.

## Architecture

```
src/
  manifest.chrome.json     Chrome MV3: service_worker + side_panel
  manifest.firefox.json    Firefox MV3: background.scripts + sidebar_action + gecko id
  background.js            message relay; opens the panel/sidebar
  lib/
    ext.js                 chrome.* / browser.* shim (avoids an npm polyfill)
    api.js                 backend client — lives here because the panel holds
                           the host permissions; the content script never fetches
  content/
    leetcode-adapter.js    ⚠ the only file that knows LeetCode's DOM
    content.js             verdict observer + message handling
  panel/                   the UI (tabs: Understand / Hints / Review / You)
```

### The fragile part, and how it's contained

`leetcode-adapter.js` is the highest-risk file in the whole project — LeetCode
can change their markup at any time and break extraction. Containment:

1. **All selectors live in one `SELECTORS` object** — a fix is a one-line edit.
2. **Every extractor tries multiple strategies.** Code reading prefers
   `localStorage` (returns the *whole* buffer) and falls back to scraping
   `.view-lines` (only the visible lines — Monaco virtualises its DOM, so the
   result is flagged `complete: false`).
3. **Nothing throws.** A failed extraction returns `null` and the panel offers a
   manual paste box, so a broken selector degrades the product instead of killing it.

**Diagnosing a break:** open a LeetCode problem, open devtools console, run:

```js
LL.adapter.selfTest()
```

It prints a table showing exactly which of slug / language / code / verdict
still extract, and which strategy succeeded.

## What is verified, and what isn't

| Verified | How |
|---|---|
| Slug, language, code, verdict parsing logic | 14 Node tests against stubbed DOM/localStorage |
| Manifest validity for both browsers | `build.py` + 5 pytest checks |
| Panel rendering, hint ladder, review, memes | rendered against real backend fixtures in a browser |

| **Not** verified | Why |
|---|---|
| Selectors against **live leetcode.com** | Needs a signed-in browser session on the real site |
| Chrome/Firefox install + side panel behaviour | Needs a human to load the unpacked build |

Those two are the manual steps — see the root README.
