/**
 * Unit tests for the LeetCode DOM adapter — the most breakage-prone code in the
 * project. Uses Node's built-in test runner (no npm install required):
 *
 *   node --test apps/extension/tests/adapter.test.mjs
 *
 * These run against stubbed globals, so they catch logic regressions but cannot
 * catch LeetCode changing their markup — only loading the extension on a real
 * problem page does that, which is exactly how the radix-ui migration was found.
 *
 * Worth recording: the previous version of this file asserted that
 * `normalizeLanguage("Kotlin")` returns `"kotlin"`. That test passed, and the
 * behaviour it protected is precisely what shipped "Choose a type" to the API as
 * a language. A test can lock in a bug as firmly as it locks in a fix, so the
 * language cases below assert rejection rather than passthrough.
 */
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(here, "..", "src", "content", "leetcode-adapter.js"), "utf8");

/**
 * Build a fresh adapter with stubbed browser globals.
 *
 * `bridge` stands in for the page-world Monaco reader: when supplied, the
 * stubbed `postMessage` answers as the real bridge would.
 */
function loadAdapter({ url = "https://leetcode.com/problems/two-sum/", dom = {}, bridge = null } = {}) {
  const listeners = [];

  const ctx = {
    globalThis: null,
    location: { href: url },
    console: { debug() {}, table() {}, warn() {} },
    setTimeout: (fn, ms) => setTimeout(fn, ms),
    document: {
      querySelector: (sel) => dom[sel] ?? null,
      querySelectorAll: (sel) => {
        const hit = dom[sel];
        if (!hit) return [];
        return Array.isArray(hit) ? hit : [hit];
      },
      getElementById: () => null,
      createElement: () => ({ setAttribute() {} }),
      head: { appendChild() {} },
      documentElement: { appendChild() {} },
    },
    window: {
      addEventListener: (type, fn) => listeners.push({ type, fn }),
      postMessage: (data) => {
        if (data?.type !== "LL_PAGE_REQUEST") return;
        // Deliver asynchronously, as a real page round trip would.
        setTimeout(() => {
          for (const l of listeners) {
            if (l.type !== "message") continue;
            l.fn({
              source: ctx.window,
              data: {
                type: "LL_PAGE_RESPONSE",
                id: data.id,
                payload: bridge ?? { ok: false, reason: "no bridge" },
              },
            });
          }
        }, 0);
      },
    },
    LL: { ext: { runtime: { getURL: (p) => `chrome-extension://test/${p}` } } },
  };
  ctx.globalThis = ctx;
  ctx.window.window = ctx.window;
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return ctx.LL.adapter;
}

// --- slug parsing (the one thing that must never break) ---

test("readSlug handles the standard problem URL", () => {
  assert.equal(loadAdapter().readSlug("https://leetcode.com/problems/two-sum/"), "two-sum");
});

test("readSlug handles description/solutions sub-paths and query strings", () => {
  const a = loadAdapter();
  for (const url of [
    "https://leetcode.com/problems/valid-parentheses/description/",
    "https://leetcode.com/problems/valid-parentheses/solutions/?envType=study-plan",
    "https://leetcode.com/problems/valid-parentheses/submissions/12345/",
  ]) {
    assert.equal(a.readSlug(url), "valid-parentheses", url);
  }
});

test("readSlug returns null off a problem page", () => {
  const a = loadAdapter();
  for (const url of ["https://leetcode.com/problemset/all/", "https://example.com/problems/two-sum/"]) {
    assert.equal(a.readSlug(url), null, url);
  }
});

// --- language normalization ---

test("normalizeLanguage maps LeetCode labels to backend ids", () => {
  const a = loadAdapter();
  const cases = {
    "C++": "cpp", Python3: "python", Python: "python", Java: "java",
    JavaScript: "javascript", TypeScript: "typescript", Go: "go", "  Java  ": "java",
  };
  for (const [input, expected] of Object.entries(cases)) {
    assert.equal(a.normalizeLanguage(input), expected, input);
  }
});

test("normalizeLanguage REJECTS anything it does not recognise", () => {
  // The regression this file exists for. Passing an unknown string through is
  // how a comment-filter dropdown reading "Choose a type" reached the backend
  // as a language, failed static analysis, and silently degraded every
  // downstream feature to its couldn't-parse branch.
  const a = loadAdapter();
  for (const junk of ["Choose a type", "Sort by:Best", "", "Kotlin", "Rust", null, undefined, "1"]) {
    assert.equal(a.normalizeLanguage(junk), null, JSON.stringify(junk));
  }
});

// --- language extraction from the DOM ---

test("readLanguageFromDom ignores matching elements whose text is not a language", () => {
  // Several unrelated dropdowns share the language button's markup, so matching
  // the selector proves nothing — the text has to be a language too.
  const a = loadAdapter({
    dom: {
      "button[aria-haspopup='dialog'][data-state]": [
        { textContent: "Choose a type" },
        { textContent: "Sort by:Best" },
        { textContent: "C++" },
      ],
    },
  });
  assert.equal(a.readLanguageFromDom().language, "cpp");
});

test("readLanguageFromDom reports failure rather than guessing", () => {
  const a = loadAdapter({
    dom: { "button[aria-haspopup='dialog'][data-state]": [{ textContent: "Choose a type" }] },
  });
  assert.equal(a.readLanguageFromDom().language, null);
});

// --- code extraction ---

test("readCode prefers the Monaco bridge and reports the buffer as complete", async () => {
  const a = loadAdapter({
    bridge: { ok: true, code: "class Solution {\n  // full file\n}", language: "cpp", source: "monaco" },
  });
  const r = await a.readCode();
  assert.match(r.code, /full file/);
  assert.equal(r.complete, true);
  assert.equal(r.language, "cpp");
  assert.equal(r.strategy, "monaco");
});

test("readCode falls back to visible DOM lines and flags them as partial", async () => {
  const viewLines = {
    querySelectorAll: () => [{ textContent: "def twoSum(nums):" }, { textContent: "    pass" }],
  };
  const a = loadAdapter({ dom: { ".view-lines": viewLines } });
  const r = await a.readCode();
  assert.equal(r.code, "def twoSum(nums):\n    pass");
  // Monaco virtualises, so a scrape is never guaranteed to be the whole file.
  assert.equal(r.complete, false);
  assert.match(r.strategy, /^dom:/);
});

test("readCode returns null rather than throwing when nothing is available", async () => {
  const r = await loadAdapter().readCode();
  assert.equal(r.code, null);
  assert.equal(r.strategy, null);
});

// --- verdict detection ---

test("readVerdict recognizes each judge outcome", () => {
  const cases = {
    Accepted: "Accepted",
    "Wrong Answer": "Wrong Answer",
    "Time Limit Exceeded": "Time Limit Exceeded",
    "Runtime Error": "Runtime Error",
    "Compile Error": "Compile Error",
  };
  for (const [text, expected] of Object.entries(cases)) {
    const a = loadAdapter({ dom: { "[data-e2e-locator='submission-result']": { textContent: text } } });
    assert.equal(a.readVerdict(), expected, text);
  }
});

test("readVerdict returns null when no result is on screen", () => {
  assert.equal(loadAdapter().readVerdict(), null);
});

// --- whole-context read ---

test("readContext degrades gracefully off a problem page", async () => {
  const a = loadAdapter({ url: "https://leetcode.com/problemset/all/" });
  assert.equal((await a.readContext()).ok, false);
});

test("readContext takes the language from the editor model when available", async () => {
  const a = loadAdapter({ bridge: { ok: true, code: "print(1)", language: "python3" } });
  const ctx = await a.readContext();
  assert.equal(ctx.language, "python");
  assert.equal(ctx.languageStrategy, "monaco");
  assert.equal(ctx.codeComplete, true);
});

test("readContext reports language as null when it genuinely cannot read one", async () => {
  // Null is the honest answer and lets the caller decide. The old behaviour
  // invented a value, which is strictly worse: a wrong language cannot be
  // detected downstream, it just quietly poisons the analysis.
  const a = loadAdapter({
    dom: { "button[aria-haspopup='dialog'][data-state]": [{ textContent: "Choose a type" }] },
  });
  const ctx = await a.readContext();
  assert.equal(ctx.ok, true);
  assert.equal(ctx.slug, "two-sum");
  assert.equal(ctx.language, null);
});

test("adapter never throws on a hostile/empty DOM", async () => {
  const a = loadAdapter({ dom: {} });
  await assert.doesNotReject(() => a.readContext());
  await assert.doesNotReject(() => a.selfTest());
});

test("selfTest surfaces which strategy produced each field", async () => {
  const a = loadAdapter({ bridge: { ok: true, code: "print(1)", language: "python3" } });
  const report = await a.selfTest();
  assert.match(report.language, /python \(via monaco\)/);
  assert.match(report.code, /via monaco/);
});
