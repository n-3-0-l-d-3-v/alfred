/**
 * Generic adapter — the fallback for every site without a bespoke one.
 *
 * This is what makes "one place to practise" true today rather than after
 * someone writes twenty adapters. On an unrecognised page the panel asks the
 * learner to paste their code and name the topic; everything downstream — the
 * archetypes, the analysis, the review, the personas, the AC gate — works
 * identically, because none of it ever needed the page.
 *
 * Deliberately claims nothing automatically. `matches()` returns false so it is
 * never selected by URL; the panel selects it explicitly when no other adapter
 * applies. An adapter that guessed would produce exactly the class of confident
 * wrong answer that the "Choose a type" bug already taught us to avoid.
 */
globalThis.LL = globalThis.LL || {};

LL.platforms.register({
  id: "generic",
  label: "Anywhere else",

  // Never auto-selected — see the module comment.
  matches: () => false,

  // There is no page to read; the panel supplies these from what the learner
  // typed. The methods exist so the adapter satisfies the same contract.
  readProblem: () => null,
  readCode: async () => ({ code: null, complete: false, language: null, strategy: "manual" }),
  readVerdict: () => null,

  /**
   * Build a context from manual input.
   *
   * `solved` is self-reported here, which is a real weakening of the AC gate —
   * on LeetCode a passing verdict is observed, and here it is claimed. That is
   * an acceptable trade: someone who lies to a practice tool to unlock a code
   * review has defeated only themselves, and refusing to work off LeetCode
   * would cost far more than this leaks.
   */
  fromManualInput({ topic, code, language, solved = false }) {
    return {
      ok: true,
      platform: "generic",
      platformLabel: "Anywhere else",
      slug: topic,
      title: null,
      language: language ?? null,
      languageStrategy: "manual",
      code: code ?? null,
      // Pasted code is whole by definition — that is the point of pasting.
      codeComplete: Boolean(code),
      codeStrategy: "manual",
      verdict: solved ? "Accepted" : null,
      url: location.href,
    };
  },
});
