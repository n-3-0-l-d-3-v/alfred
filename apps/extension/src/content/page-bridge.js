/**
 * Page-world bridge. Runs in LeetCode's own JavaScript context, not the
 * extension's isolated one.
 *
 * Why this file has to exist: the editor is Monaco, and `window.monaco` holds
 * the authoritative buffer and language id. A content script cannot see it —
 * isolated worlds share the DOM but not page globals. Everything reachable from
 * the isolated side is a degraded proxy for what this file can read directly:
 *
 *   - Scraping `.view-lines` returns only the lines currently rendered. Monaco
 *     virtualises, so on a long solution you get a fragment, and on a freshly
 *     loaded page you can get nothing at all.
 *   - localStorage no longer holds the buffer (LeetCode stopped persisting it
 *     under any key we can find).
 *   - The language *label* has to be scraped out of a dropdown whose markup
 *     changes whenever LeetCode reskins. `getLanguageId()` is a stable API.
 *
 * Communication is a `postMessage` request/response pair. The listener checks
 * `event.source === window` so another frame cannot answer on our behalf, and
 * this file only ever *reads* — it never accepts code to run.
 */
(() => {
  const REQUEST = "LL_PAGE_REQUEST";
  const RESPONSE = "LL_PAGE_RESPONSE";

  /** The model actually being edited: the largest non-empty one. */
  function activeModel() {
    if (typeof window.monaco === "undefined" || !window.monaco.editor) return null;
    const models = window.monaco.editor.getModels().filter((m) => {
      try {
        return m.getValue().trim().length > 0;
      } catch (_) {
        return false;
      }
    });
    if (!models.length) return null;
    // LeetCode keeps a second, empty plaintext model around; picking the
    // largest avoids depending on their ordering.
    return models.sort((a, b) => b.getValue().length - a.getValue().length)[0];
  }

  function read() {
    try {
      const model = activeModel();
      if (!model) return { ok: false, reason: "no editor model with content" };
      return {
        ok: true,
        code: model.getValue(),
        language: model.getLanguageId(),
        lines: model.getLineCount(),
        source: "monaco",
      };
    } catch (err) {
      return { ok: false, reason: String(err && err.message) };
    }
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.data?.type !== REQUEST) return;
    window.postMessage({ type: RESPONSE, id: event.data.id, payload: read() }, "*");
  });

  // Announce readiness so the content script knows the bridge landed rather
  // than waiting out a timeout on every single extraction.
  window.postMessage({ type: RESPONSE, id: "ready", payload: { ok: true, ready: true } }, "*");
})();
