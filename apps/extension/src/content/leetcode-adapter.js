/**
 * LeetCodeAdapter — the ONLY place that knows LeetCode's DOM.
 *
 * This is the most fragile file in the project, and it has already been broken
 * once by a LeetCode reskin: the previous version searched for `headlessui`
 * listbox buttons, LeetCode moved to `radix-ui`, and every language selector
 * missed. The fallback selector then matched a comment-filter dropdown and
 * confidently reported the language as "Choose a type", which the backend
 * rejected as unsupported — so static analysis returned nothing and every
 * downstream feature silently degraded to its "couldn't parse" branch.
 *
 * The lesson is in the design now:
 *
 *   1. Prefer APIs over markup. `window.monaco` gives the full buffer and the
 *      language id directly; both survive reskins. DOM scraping is the fallback,
 *      not the primary path (see content/page-bridge.js).
 *   2. Validate what you extract. A language is only accepted if it is a
 *      language we recognise. Returning an unrecognised string was the actual
 *      defect — a wrong answer is worse than no answer, because no answer can
 *      be handled and a wrong one propagates.
 *   3. Report confidence. Every extraction says where it came from, so
 *      `selfTest()` and the panel can tell "read from the editor" apart from
 *      "guessed from markup".
 *
 * Run `LL.adapter.selfTest()` in the console on a problem page — select the
 * Alfred context in the console's dropdown first — to see what still works.
 */
globalThis.LL = globalThis.LL || {};

/**
 * Bumped whenever extraction changes. `selfTest()` prints it because Chrome
 * keeps running the previously loaded copy of an unpacked extension until you
 * press reload on chrome://extensions — rebuilding `dist/` is not enough.
 * Without a visible stamp, testing a stale build is indistinguishable from a
 * fix that did not work, which has already cost one debugging round trip.
 */
const ADAPTER_VERSION = "2026.08.08-monaco";

const SELECTORS = {
  // Kept only as a fallback for when the Monaco bridge is unavailable.
  codeLines: [".view-lines", ".monaco-editor .view-lines"],
  // Current LeetCode uses radix-ui; the older headlessui forms are retained so
  // an older deployment still works.
  languageButton: [
    "button[aria-haspopup='dialog'][data-state]",
    "button[id^='radix-']",
    "button[id^='headlessui-listbox-button']",
    "[data-cy='lang-select']",
  ],
  resultArea: [
    "[data-e2e-locator='submission-result']",
    "[data-e2e-locator='console-result']",
    "[class*='text-green-s'], [class*='text-red-s']",
  ],
};

/** Languages the backend can analyse, plus the labels LeetCode shows for them. */
const LANGUAGE_MAP = {
  "c++": "cpp", cpp: "cpp", c: "cpp",
  python: "python", python3: "python", py: "python",
  java: "java",
  javascript: "javascript", js: "javascript", node: "javascript",
  typescript: "typescript", ts: "typescript",
  go: "go", golang: "go",
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

/**
 * Normalize a language label, returning null for anything unrecognised.
 *
 * The null matters. The previous version ended in `?? s`, passing whatever it
 * scraped straight through to the API — which is how "Choose a type" became a
 * language and took the entire review pipeline down with it. An unknown label
 * means extraction failed, and failure has to be representable.
 */
function normalizeLanguage(label) {
  if (!label) return null;
  const s = String(label).trim().toLowerCase();
  return LANGUAGE_MAP[s] ?? null;
}

/** Scrape the language from the toolbar. Fallback only — the bridge is better. */
function readLanguageFromDom() {
  for (const sel of SELECTORS.languageButton) {
    let nodes;
    try {
      nodes = document.querySelectorAll(sel);
    } catch (_) {
      continue;
    }
    for (const el of nodes) {
      // Only accept a node whose text *is* a language. Several unrelated
      // dropdowns share this markup, so matching the selector proves nothing.
      const lang = normalizeLanguage(el.textContent);
      if (lang) return { language: lang, strategy: `dom:${sel}` };
    }
  }
  return { language: null, strategy: null };
}

// --- page-world bridge -------------------------------------------------------

let bridgeReady = false;
const pending = new Map();

window.addEventListener("message", (event) => {
  if (event.source !== window || event.data?.type !== "LL_PAGE_RESPONSE") return;
  const { id, payload } = event.data;
  if (id === "ready") {
    bridgeReady = true;
    return;
  }
  const resolve = pending.get(id);
  if (resolve) {
    pending.delete(id);
    resolve(payload);
  }
});

/** Inject the bridge into the page context. Idempotent. */
function installBridge() {
  if (document.getElementById("ll-page-bridge")) return;
  try {
    const s = document.createElement("script");
    s.id = "ll-page-bridge";
    s.src = LL.ext.runtime.getURL("content/page-bridge.js");
    (document.head || document.documentElement).appendChild(s);
  } catch (_) {
    /* injection blocked — DOM fallback still applies */
  }
}

/** Ask the page world for the editor buffer. Resolves null if it can't answer. */
function askBridge(timeoutMs = 400) {
  return new Promise((resolve) => {
    let settled = false;
    const done = (v) => {
      if (!settled) {
        settled = true;
        resolve(v);
      }
    };
    const id = `ll-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    pending.set(id, done);
    try {
      window.postMessage({ type: "LL_PAGE_REQUEST", id }, "*");
    } catch (_) {
      done(null);
    }
    setTimeout(() => {
      pending.delete(id);
      done(null);
    }, timeoutMs);
  });
}

/**
 * Read the editor buffer.
 *
 * Strategy 1: Monaco via the page bridge — the whole file, plus the language.
 * Strategy 2: scrape the rendered lines. Monaco virtualises, so this is a
 *   fragment of a long solution and sometimes empty entirely; it is flagged
 *   `complete: false` so callers can warn rather than silently analysing part
 *   of the code and reporting conclusions about all of it.
 */
async function readCode() {
  const fromBridge = await askBridge();
  if (fromBridge?.ok && fromBridge.code?.trim()) {
    return {
      code: fromBridge.code,
      complete: true,
      language: normalizeLanguage(fromBridge.language),
      strategy: "monaco",
    };
  }

  const { el, sel } = firstMatch(SELECTORS.codeLines);
  if (el) {
    const lines = [...el.querySelectorAll(".view-line")].map((n) => n.textContent ?? "");
    const text = lines.join("\n").replace(/ /g, " ");
    if (text.trim()) {
      return { code: text, complete: false, language: null, strategy: `dom:${sel}` };
    }
  }

  return { code: null, complete: false, language: null, strategy: null };
}

// --- problem metadata --------------------------------------------------------

/**
 * Title, difficulty, topic tags and the statement text.
 *
 * The backend needs these to teach a problem nobody has authored a card for:
 * they are what an archetype is inferred from. Read via LeetCode's own GraphQL
 * endpoint rather than the DOM, for the reason at the top of this file —
 * markup is reskinned, the query behind the page's own data is not. The content
 * script is same-origin with leetcode.com, so this needs no host permission and
 * sends no cookies anywhere else.
 *
 * Topic tags are the single most useful signal here and are the one thing the
 * DOM genuinely cannot supply: the page keeps them collapsed behind a Topics
 * toggle and does not render them until clicked.
 */
const META_QUERY = `query q($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId title difficulty content
    topicTags { slug }
  }
}`;

let metaCache = { slug: null, value: null };

async function readMeta(slug = readSlug(), timeoutMs = 2500) {
  if (!slug) return null;
  // Metadata for a problem does not change while the tab is open, and the
  // panel re-reads context on every hint and review.
  if (metaCache.slug === slug && metaCache.value) return metaCache.value;

  let meta = null;
  try {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), timeoutMs);
    const res = await fetch("/graphql", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query: META_QUERY, variables: { titleSlug: slug } }),
      credentials: "omit",
      signal: ctl.signal,
    });
    clearTimeout(timer);
    const q = (await res.json())?.data?.question;
    if (q) {
      meta = {
        title: q.questionFrontendId ? `${q.questionFrontendId}. ${q.title}` : q.title,
        difficulty: q.difficulty ?? null,
        topics: (q.topicTags ?? []).map((t) => t.slug),
        // Tags and prose only. The statement is HTML; the backend matches
        // keywords against it, so markup would just be noise in the signal.
        statement: stripHtml(q.content ?? ""),
        strategy: "graphql",
      };
    }
  } catch (_) {
    /* offline, aborted, or the query shape moved — fall through to the DOM */
  }

  if (!meta) meta = readMetaFromDom();
  if (meta) metaCache = { slug, value: meta };
  return meta;
}

function stripHtml(html) {
  try {
    const doc = new DOMParser().parseFromString(html, "text/html");
    return (doc.body.textContent ?? "").replace(/\s+/g, " ").trim();
  } catch (_) {
    return "";
  }
}

/** Fallback metadata scrape. Coarser than GraphQL and cannot see topic tags. */
function readMetaFromDom() {
  const title =
    document.querySelector("div.text-title-large a, a[href^='/problems/'] .text-title-large")
      ?.textContent?.trim() || null;

  let difficulty = null;
  for (const el of document.querySelectorAll("div,span")) {
    const t = el.textContent?.trim();
    if (t && /^(Easy|Medium|Hard)$/.test(t)) {
      difficulty = t;
      break;
    }
  }

  const statement = stripHtml(
    document.querySelector("[data-track-load='description_content']")?.innerHTML ?? ""
  );

  if (!title && !difficulty && !statement) return null;
  return { title, difficulty, topics: [], statement, strategy: "dom" };
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

async function readContext() {
  const slug = readSlug();
  if (!slug) return { ok: false, reason: "not a problem page" };

  // Both are network/DOM-bound and independent; serialising them added most of
  // a second to every hint press, since the panel re-reads context each time.
  const [{ code, complete, language: modelLanguage, strategy }, meta] = await Promise.all([
    readCode(),
    readMeta(slug),
  ]);
  const fromDom = modelLanguage ? null : readLanguageFromDom();
  const language = modelLanguage ?? fromDom?.language ?? null;

  return {
    ok: true,
    slug,
    title: meta?.title ?? null,
    difficulty: meta?.difficulty ?? null,
    topics: meta?.topics ?? [],
    statement: meta?.statement ?? null,
    metaStrategy: meta?.strategy ?? null,
    // Null rather than a guess. The panel decides how to handle not knowing;
    // inventing a language is what broke the review pipeline before.
    language,
    languageStrategy: modelLanguage ? "monaco" : fromDom?.strategy ?? null,
    code,
    codeComplete: complete,
    codeStrategy: strategy,
    verdict: readVerdict(),
    url: location.href,
  };
}

/** Diagnostic: which extraction strategies still work on this page? */
async function selfTest() {
  const ctx = await readContext();
  const report = {
    adapterVersion: ADAPTER_VERSION,
    slug: ctx.slug ?? "FAIL",
    language: ctx.language ? `${ctx.language} (via ${ctx.languageStrategy})` : "FAIL",
    code: ctx.code
      ? `OK via ${ctx.codeStrategy} (${ctx.code.length} chars, complete=${ctx.codeComplete})`
      : "FAIL",
    bridge: bridgeReady ? "installed" : "NOT INSTALLED",
    verdict: ctx.verdict ?? "none on screen",
    meta: ctx.metaStrategy
      ? `OK via ${ctx.metaStrategy} (${ctx.difficulty ?? "?"}, ${ctx.topics.length} tags)`
      : "FAIL",
  };
  console.table(report);
  return report;
}

installBridge();

LL.adapter = {
  VERSION: ADAPTER_VERSION,
  readSlug,
  readLanguageFromDom,
  readCode,
  readMeta,
  readMetaFromDom,
  readVerdict,
  readContext,
  normalizeLanguage,
  selfTest,
  installBridge,
  SELECTORS,
  LANGUAGE_MAP,
};

// --- registration through the platform seam ----------------------------------

// The adapter above predates the seam and is kept as-is: it is the most
// battle-tested code in the project and the reference implementation other
// platforms are written against. This wrapper is the whole cost of making it
// pluggable.
if (LL.platforms) {
  LL.platforms.register({
    id: "leetcode",
    label: "LeetCode",
    matches: (url) => /(^|\/\/)([a-z]+\.)?leetcode\.com\/problems\//i.test(url),
    // Stays synchronous: content.js reads the slug from this on every mutation
    // and every navigation tick, where a promise would be pure overhead. The
    // metadata that does need a round trip is a separate, optional method.
    readProblem: () => {
      const id = readSlug();
      return id ? { id, title: null } : null;
    },
    readMeta: () => readMeta(),
    readCode: async () => {
      const r = await readCode();
      // Monaco reports the language alongside the buffer; the DOM path can't,
      // so the toolbar scrape fills in only when the bridge came up empty.
      const language = r.language ?? readLanguageFromDom().language;
      return { ...r, language, languageStrategy: r.language ? "monaco" : "dom" };
    },
    readVerdict,
  });
}
