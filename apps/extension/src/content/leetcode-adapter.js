/**
 * LeetCodeAdapter — the ONLY place that knows LeetCode's DOM.
 *
 * This is the most fragile file in the project: LeetCode ships DOM changes
 * whenever they like, and any of these selectors can break without warning.
 * Three defences:
 *   1. Every selector lives in SELECTORS, so a fix is a one-line edit.
 *   2. Every extractor tries several strategies and reports which one worked.
 *   3. Nothing throws — a failed extraction returns null and the panel falls
 *      back to manual paste, so the product degrades instead of dying.
 *
 * Run `LL.adapter.selfTest()` in the console on a problem page to see exactly
 * which strategies are alive.
 */
globalThis.LL = globalThis.LL || {};

const SELECTORS = {
  codeLines: [".view-lines", ".monaco-editor .view-lines"],
  languageButton: [
    "button[id^='headlessui-listbox-button']",
    "[data-cy='lang-select']",
    ".relative button.rounded",
  ],
  resultArea: [
    "[data-e2e-locator='submission-result']",
    "[data-e2e-locator='console-result']",
    ".text-green-s, .text-red-s",
  ],
  titleEl: ["div[class*='text-title-large'] a", "a[href^='/problems/']"],
};

function firstMatch(list) {
  for (const sel of list) {
    try {
      const el = document.querySelector(sel);
      if (el) return { el, sel };
    } catch (_) {
      /* invalid selector on this engine — skip */
    }
  }
  return { el: null, sel: null };
}

/** Problem slug from the URL. Pure — the one thing that never breaks. */
function readSlug(href = location.href) {
  const m = href.match(/leetcode\.com\/problems\/([a-z0-9-]+)/i);
  return m ? m[1].toLowerCase() : null;
}

/** Normalize LeetCode's language labels to what the backend expects. */
function normalizeLanguage(label) {
  if (!label) return null;
  const s = String(label).trim().toLowerCase();
  const map = {
    "c++": "cpp", cpp: "cpp", c: "cpp",
    python: "python", python3: "python", py: "python",
    java: "java",
    javascript: "javascript", js: "javascript",
    typescript: "typescript", ts: "typescript",
    go: "go", golang: "go",
  };
  return map[s] ?? s;
}

function readLanguage() {
  const { el } = firstMatch(SELECTORS.languageButton);
  const raw = el?.textContent?.trim();
  return normalizeLanguage(raw) ?? null;
}

/**
 * Read the editor buffer.
 *
 * Strategy 1: localStorage — LeetCode persists the buffer per problem+language.
 *   This is the only strategy that returns the WHOLE file; Monaco virtualises
 *   its DOM so the visible lines are all you can scrape.
 * Strategy 2: scrape .view-lines (visible portion only — flagged as partial).
 */
function readCode(slug) {
  // --- strategy 1: localStorage ---
  try {
    const keys = Object.keys(localStorage).filter(
      (k) => k.includes(slug) && /code|editor/i.test(k)
    );
    for (const k of keys) {
      const v = localStorage.getItem(k);
      if (v && v.length > 20) {
        try {
          const parsed = JSON.parse(v);
          const text = typeof parsed === "string" ? parsed : parsed?.code ?? parsed?.value;
          if (typeof text === "string" && text.trim()) {
            return { code: text, complete: true, strategy: `localStorage:${k}` };
          }
        } catch (_) {
          return { code: v, complete: true, strategy: `localStorage:${k}` };
        }
      }
    }
  } catch (_) {
    /* storage blocked */
  }

  // --- strategy 2: scrape visible lines ---
  const { el, sel } = firstMatch(SELECTORS.codeLines);
  if (el) {
    const lines = [...el.querySelectorAll(".view-line")].map((n) => n.textContent ?? "");
    const text = lines.join("\n").replace(/ /g, " ");
    if (text.trim()) {
      // Monaco virtualises: this is only what's on screen.
      return { code: text, complete: false, strategy: `dom:${sel}` };
    }
  }

  return { code: null, complete: false, strategy: null };
}

/** Read a submission verdict, if one is on screen. */
function readVerdict() {
  const { el } = firstMatch(SELECTORS.resultArea);
  const text = el?.textContent?.trim();
  if (!text) return null;
  const t = text.toLowerCase();
  if (t.includes("accepted")) return "Accepted";
  if (t.includes("wrong answer")) return "Wrong Answer";
  if (t.includes("time limit")) return "Time Limit Exceeded";
  if (t.includes("runtime error")) return "Runtime Error";
  if (t.includes("compile error")) return "Compile Error";
  if (t.includes("memory limit")) return "Memory Limit Exceeded";
  return null;
}

function readContext() {
  const slug = readSlug();
  if (!slug) return { ok: false, reason: "not a problem page" };
  const { code, complete, strategy } = readCode(slug);
  return {
    ok: true,
    slug,
    language: readLanguage() ?? "python",
    code,
    codeComplete: complete,
    codeStrategy: strategy,
    verdict: readVerdict(),
    url: location.href,
  };
}

/** Diagnostic: which extraction strategies still work on this page? */
function selfTest() {
  const ctx = readContext();
  const report = {
    slug: ctx.slug ?? "FAIL",
    language: ctx.language ?? "FAIL",
    code: ctx.code ? `OK via ${ctx.codeStrategy} (${ctx.code.length} chars, complete=${ctx.codeComplete})` : "FAIL",
    verdict: ctx.verdict ?? "none on screen",
  };
  console.table(report);
  return report;
}

LL.adapter = { readSlug, readLanguage, readCode, readVerdict, readContext, normalizeLanguage, selfTest, SELECTORS };
