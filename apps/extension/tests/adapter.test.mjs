/**
 * Unit tests for the LeetCode DOM adapter — the most breakage-prone code in the
 * project. Uses Node's built-in test runner (no npm install required):
 *
 *   node --test apps/extension/tests/
 *
 * The DOM-dependent paths run against stubbed globals, so these tests catch
 * logic regressions. They can NOT catch LeetCode changing their markup — only
 * loading the extension on a real problem page does that.
 */
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(here, "..", "src", "content", "leetcode-adapter.js"), "utf8");

/** Build a fresh adapter with stubbed browser globals. */
function loadAdapter({ url = "https://leetcode.com/problems/two-sum/", storage = {}, dom = {} } = {}) {
  const ls = { ...storage };
  Object.defineProperty(ls, "getItem", { value: (k) => (k in ls ? ls[k] : null), enumerable: false });

  const ctx = {
    globalThis: null,
    location: { href: url },
    localStorage: ls,
    console: { debug() {}, table() {} },
    document: {
      querySelector(sel) {
        return dom[sel] ?? null;
      },
    },
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return ctx.LL.adapter;
}

// --- slug parsing (the one thing that must never break) ---

test("readSlug handles the standard problem URL", () => {
  const a = loadAdapter();
  assert.equal(a.readSlug("https://leetcode.com/problems/two-sum/"), "two-sum");
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
    "C++": "cpp", "Python3": "python", "Python": "python", Java: "java",
    JavaScript: "javascript", TypeScript: "typescript", Go: "go", "  Java  ": "java",
  };
  for (const [input, expected] of Object.entries(cases)) {
    assert.equal(a.normalizeLanguage(input), expected, input);
  }
});

test("normalizeLanguage passes through unknown languages instead of crashing", () => {
  const a = loadAdapter();
  assert.equal(a.normalizeLanguage("Kotlin"), "kotlin");
  assert.equal(a.normalizeLanguage(null), null);
});

// --- code extraction ---

test("readCode prefers localStorage and reports it as complete", () => {
  const a = loadAdapter({
    storage: { "1_two-sum_code": JSON.stringify("def twoSum(nums, target):\n    return []") },
  });
  const r = a.readCode("two-sum");
  assert.match(r.code, /def twoSum/);
  assert.equal(r.complete, true);
  assert.match(r.strategy, /^localStorage:/);
});

test("readCode falls back to visible DOM lines and flags them as partial", () => {
  const viewLines = {
    querySelectorAll: () => [{ textContent: "def twoSum(nums):" }, { textContent: "    pass" }],
  };
  const a = loadAdapter({ dom: { ".view-lines": viewLines } });
  const r = a.readCode("two-sum");
  assert.equal(r.code, "def twoSum(nums):\n    pass");
  // Monaco virtualises its DOM, so a scrape is never guaranteed complete.
  assert.equal(r.complete, false);
  assert.match(r.strategy, /^dom:/);
});

test("readCode returns null rather than throwing when nothing is available", () => {
  const a = loadAdapter();
  const r = a.readCode("two-sum");
  assert.equal(r.code, null);
  assert.equal(r.strategy, null);
});

test("readCode ignores tiny/irrelevant localStorage entries", () => {
  const a = loadAdapter({ storage: { "two-sum_code": "x", unrelated_key: "a".repeat(50) } });
  assert.equal(a.readCode("two-sum").code, null);
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

test("readContext degrades gracefully off a problem page", () => {
  const a = loadAdapter({ url: "https://leetcode.com/problemset/all/" });
  assert.equal(a.readContext().ok, false);
});

test("readContext defaults language to python when the selector breaks", () => {
  const a = loadAdapter({ storage: { "two-sum_code": JSON.stringify("print(1)\n# padding to pass length check") } });
  const ctx = a.readContext();
  assert.equal(ctx.ok, true);
  assert.equal(ctx.slug, "two-sum");
  assert.equal(ctx.language, "python");
});

test("adapter never throws on a hostile/empty DOM", () => {
  const a = loadAdapter({ dom: {} });
  assert.doesNotThrow(() => a.readContext());
  assert.doesNotThrow(() => a.selfTest());
});
