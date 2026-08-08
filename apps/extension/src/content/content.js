/**
 * Content script: answers context requests from the panel, and watches for a
 * submission verdict so the AC gate can flip the moment you pass.
 */
(function () {
  const seen = { verdict: null };

  // Extraction is async now — reading the real editor buffer means a round
  // trip to the page world. Returning true keeps the message channel open
  // until the promise settles; without it the panel receives undefined.
  LL.ext.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type === "LL_EXTRACT") {
      LL.platforms.readContext().then(sendResponse);
      return true;
    }
    if (msg?.type === "LL_SELFTEST") {
      LL.adapter.selfTest().then(sendResponse);
      return true;
    }
    return false;
  });

  // Watch the result area. LeetCode renders verdicts asynchronously, so poll
  // the DOM via MutationObserver rather than hooking their network layer
  // (which would be brittle and invasive).
  // Read through the active adapter, not a hardcoded one, so a second platform
  // gets verdict detection for free rather than needing this file edited.
  const adapter = () => LL.platforms.forUrl();

  const observer = new MutationObserver(() => {
    const v = adapter()?.readVerdict() ?? null;
    if (v && v !== seen.verdict) {
      seen.verdict = v;
      LL.sendMessage({
        type: "LL_VERDICT",
        verdict: v,
        platform: adapter()?.id ?? null,
        slug: adapter()?.readProblem()?.id ?? null,
      }).catch(() => {
        /* panel closed — the panel re-reads on open, so nothing is lost */
      });
    }
  });

  observer.observe(document.body, { childList: true, subtree: true, characterData: true });

  // Re-arm on SPA navigation between problems.
  let lastUrl = location.href;
  setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      seen.verdict = null;
      LL.sendMessage({
        type: "LL_NAVIGATED",
        platform: adapter()?.id ?? null,
        slug: adapter()?.readProblem()?.id ?? null,
      }).catch(() => {});
    }
  }, 1000);

  const active = adapter();
  console.debug("[LeetLearn] content script ready —", active ? active.id : "no adapter", location.href);
})();
