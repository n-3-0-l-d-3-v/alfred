/**
 * The platform registry, and the wiring that makes it more than decoration.
 *
 * The registry shipped once with every adapter registering into it and nothing
 * reading from it: the content script still called one hardcoded adapter and the
 * panel still matched a LeetCode URL pattern. Everything "worked", so nothing
 * caught it. These tests assert the seam is actually load-bearing.
 */
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const read = (...p) => readFileSync(join(here, "..", "src", ...p), "utf8");

function load({ url = "https://leetcode.com/problems/two-sum/", withGeneric = true } = {}) {
  const ctx = {
    globalThis: null,
    location: { href: url },
    console: { debug() {}, table() {}, warn() {} },
    setTimeout: (fn, ms) => setTimeout(fn, ms),
    document: {
      querySelector: () => null,
      querySelectorAll: () => [],
      getElementById: () => null,
      createElement: () => ({ setAttribute() {} }),
      head: { appendChild() {} },
      documentElement: { appendChild() {} },
    },
    window: { addEventListener() {}, postMessage() {} },
    LL: { ext: { runtime: { getURL: (p) => `chrome-extension://test/${p}` } } },
  };
  ctx.globalThis = ctx;
  ctx.window.window = ctx.window;
  vm.createContext(ctx);
  vm.runInContext(read("content", "platforms.js"), ctx);
  vm.runInContext(read("content", "leetcode-adapter.js"), ctx);
  if (withGeneric) vm.runInContext(read("content", "platform-generic.js"), ctx);
  return ctx.LL;
}

// --- the registry ------------------------------------------------------------

test("adapters register themselves into the registry", () => {
  const ids = load().platforms.all().map((a) => a.id);
  assert.ok(ids.includes("leetcode"), "leetcode did not register");
  assert.ok(ids.includes("generic"), "generic did not register");
});

test("a registry entry must implement the whole contract", () => {
  const LL = load();
  assert.throws(() => LL.platforms.register({ id: "broken", label: "Broken" }), /missing/);
});

test("forUrl picks the adapter that claims the page", () => {
  const LL = load();
  assert.equal(LL.platforms.forUrl("https://leetcode.com/problems/two-sum/")?.id, "leetcode");
});

test("forUrl returns null rather than guessing on an unknown site", () => {
  // The generic adapter must never auto-claim. Guessing is what produced the
  // "Choose a type" class of confident wrong answer.
  const LL = load();
  assert.equal(LL.platforms.forUrl("https://example.com/some/page"), null);
});

test("readContext reports failure off a claimed page", async () => {
  const LL = load({ url: "https://example.com/" });
  const ctx = await LL.platforms.readContext("https://example.com/");
  assert.equal(ctx.ok, false);
});

test("readContext tags the platform it came from", async () => {
  // Problem ids are only unique within a site, so the tag is what stops a
  // session on one platform resuming a session from another.
  const LL = load();
  const ctx = await LL.platforms.readContext("https://leetcode.com/problems/two-sum/");
  assert.equal(ctx.ok, true);
  assert.equal(ctx.platform, "leetcode");
  assert.equal(ctx.slug, "two-sum");
});

// --- the generic fallback ----------------------------------------------------

test("the generic adapter builds a context from pasted input", () => {
  const LL = load();
  const generic = LL.platforms.all().find((a) => a.id === "generic");
  assert.ok(generic, "generic adapter missing");

  const adapter = LL.platforms.forUrl("https://leetcode.com/problems/two-sum/");
  assert.notEqual(adapter.id, "generic", "generic must never win by URL");
});

// --- the wiring that was previously missing ----------------------------------

test("the content script reads through the registry, not one adapter", () => {
  const src = read("content", "content.js");
  assert.match(src, /LL\.platforms\.readContext/,
    "content.js must extract via the registry or the seam is decoration");
  assert.doesNotMatch(src, /LL\.adapter\.readContext/,
    "content.js is still calling the LeetCode adapter directly");
});

test("the panel does not hardcode a site pattern", () => {
  const src = read("panel", "panel.js");
  assert.doesNotMatch(src, /leetcode\\?\.com/,
    "panel.js matches a LeetCode URL itself, which re-breaks multi-platform support");
});

test("the panel sends the platform when opening a session", () => {
  assert.match(read("panel", "panel.js"), /startSession\([^)]*platform/s,
    "sessions would collide across platforms without this");
});
