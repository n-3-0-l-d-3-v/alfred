/**
 * Platform registry — the seam that makes this more than a LeetCode extension.
 *
 * Everything that teaches is platform-independent: the archetype library, the
 * static analysis, the review engine, the personas, the AC gate, XP, streaks.
 * What differs per site is small and mechanical — how to read the problem id,
 * the code, and the verdict. That is the entire contract below.
 *
 *   PlatformAdapter {
 *     id            unique key, stored on the session
 *     label         human name, shown in the panel
 *     matches(url)  is this adapter responsible for this page?
 *     readProblem() { id, title } or null
 *     readCode()    { code, complete, language, strategy }
 *     readVerdict() a verdict string, or null
 *     readMeta()    optional; { title, difficulty, topics, statement, strategy }
 *   }
 *
 * `readMeta` is what lets the backend teach a problem nobody wrote a card for:
 * the topic tags and statement are what an algorithmic archetype is inferred
 * from. It is optional because a site may have nothing to read.
 *
 * Adding a site is one file implementing that, not a fork of the product.
 *
 * The generic adapter matters as much as the site-specific ones: it makes the
 * tool useful on a site nobody has written an adapter for — university work,
 * an interview prep site, a language tutorial — by asking the learner to paste
 * instead of scraping. "Works everywhere, better on sites we know" is a much
 * stronger promise than "works on LeetCode".
 */
globalThis.LL = globalThis.LL || {};

const _adapters = [];

LL.platforms = {
  /** Register an adapter. Order matters: first match wins, generic goes last. */
  register(adapter) {
    for (const method of ["id", "label", "matches", "readProblem", "readCode", "readVerdict"]) {
      if (!(method in adapter)) {
        throw new Error(`platform adapter '${adapter.id}' is missing ${method}`);
      }
    }
    _adapters.push(adapter);
    return adapter;
  },

  /** The adapter responsible for a URL, or null if none claims it. */
  forUrl(url = location.href) {
    return _adapters.find((a) => {
      try {
        return a.matches(url);
      } catch (_) {
        return false;
      }
    }) ?? null;
  },

  all() {
    return _adapters.map((a) => ({ id: a.id, label: a.label }));
  },

  /**
   * Read the full context from whichever adapter claims this page.
   *
   * Returns a platform-tagged shape so the backend can distinguish "two-sum on
   * LeetCode" from a same-named problem elsewhere — problem ids are only unique
   * within a site.
   */
  async readContext(url = location.href) {
    const adapter = this.forUrl(url);
    if (!adapter) return { ok: false, reason: "no adapter for this page" };

    const problem = adapter.readProblem();
    if (!problem?.id) return { ok: false, reason: "not a problem page", platform: adapter.id };

    // `readMeta` is optional: an adapter for a site with no problem statement
    // to read simply omits it, and the backend falls back to teaching from the
    // learner's code alone.
    const [code, meta] = await Promise.all([
      adapter.readCode(),
      adapter.readMeta ? adapter.readMeta().catch(() => null) : null,
    ]);
    return {
      ok: true,
      platform: adapter.id,
      platformLabel: adapter.label,
      slug: problem.id,
      title: meta?.title ?? problem.title ?? null,
      // Everything the backend needs to teach a problem no card was authored
      // for: the archetype is inferred from these.
      difficulty: meta?.difficulty ?? null,
      topics: meta?.topics ?? [],
      statement: meta?.statement ?? null,
      metaStrategy: meta?.strategy ?? null,
      language: code.language ?? null,
      languageStrategy: code.languageStrategy ?? null,
      code: code.code ?? null,
      codeComplete: code.complete ?? false,
      codeStrategy: code.strategy ?? null,
      verdict: adapter.readVerdict(),
      url,
    };
  },
};
