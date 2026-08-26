/**
 * Backend client. Lives in the panel (an extension page), which holds the host
 * permissions — the content script never talks to the API directly.
 */
globalThis.LL = globalThis.LL || {};

LL.api = (function () {
  const DEFAULT_BASE = "http://localhost:8000";

  async function base() {
    const { apiBase } = await LL.storage.get(["apiBase"]);
    return apiBase || DEFAULT_BASE;
  }

  async function token() {
    const { token } = await LL.storage.get(["token"]);
    return token || null;
  }

  async function call(path, { method = "GET", body = null, auth = true } = {}) {
    const headers = { "content-type": "application/json" };
    if (auth) {
      const t = await token();
      if (!t) throw new Error("not signed in");
      headers.Authorization = `Bearer ${t}`;
    }
    let res;
    try {
      res = await fetch((await base()) + path, {
        method,
        headers,
        body: body ? JSON.stringify(body) : null,
      });
    } catch (e) {
      const err = new Error(`Can't reach the LeetLearn server. Is it running? (${e.message})`);
      // Flagged rather than string-matched: the panel renders this as a
      // retryable state with the configured address, not as a failure of the
      // feature the learner happened to click.
      err.offline = true;
      throw err;
    }
    const text = await res.text();
    const data = text ? JSON.parse(text) : {};
    if (!res.ok) {
      if (res.status === 401 && auth) {
        // The stored token no longer identifies anyone — expired, or minted
        // against a database that has since been rebuilt. Holding on to it
        // makes every subsequent call fail the same way, which is how a stale
        // token turned into a permanent "unknown user" with no way out but
        // clearing storage by hand. Drop it so the panel can show sign-in.
        await LL.storage.set({ token: null });
        const err = new Error(data.detail || "Your session expired — sign in again.");
        err.status = 401;
        err.signedOut = true;
        throw err;
      }
      const err = new Error(data.detail || `HTTP ${res.status}`);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  return {
    setBase: (b) => LL.storage.set({ apiBase: b }),
    getBase: base,
    health: () => call("/health", { auth: false }),
    /**
     * GitHub sign-in. The extension only ever handles the short-lived OAuth
     * code and the JWT that comes back — the client secret stays on the server.
     */
    loginWithGithub: async () => {
      const { auth } = await call("/health", { auth: false });
      if (!auth?.github) throw new Error("This server doesn't have GitHub sign-in configured.");

      const code = await LL.identity.getGithubCode(auth.github_client_id);
      const r = await call("/auth/github", {
        method: "POST",
        body: { code, redirect_uri: LL.identity.redirectUri() },
        auth: false,
      });
      await LL.storage.set({ token: r.token, userId: r.user_id, handle: r.handle, avatarUrl: r.avatar_url });
      return r;
    },

    /** Local-development sign-in. Only works when the server enables it. */
    login: async (email) => {
      const r = await call("/auth/dev-login", { method: "POST", body: { email }, auth: false });
      await LL.storage.set({ token: r.token, userId: r.user_id, email });
      return r;
    },
    logout: () => LL.storage.set({ token: null }),
    isSignedIn: async () => !!(await token()),
    /**
     * Open a session. `meta` (title/difficulty/topics/statement) is what lets
     * the server build a card for a problem nobody has authored one for, so it
     * is sent on every start rather than only when the client suspects a miss —
     * the client has no way to know what the knowledge base covers.
     */
    startSession: (slug, language, platform = "leetcode", meta = {}) =>
      call("/sessions", {
        method: "POST",
        body: {
          slug,
          language,
          platform,
          title: meta.title ?? null,
          difficulty: meta.difficulty ?? null,
          topics: meta.topics ?? [],
          statement: meta.statement ?? null,
        },
      }),
    hint: (sid, level, code, personalized = false) =>
      call(`/sessions/${sid}/hint`, { method: "POST", body: { level, code, personalized } }),
    verdict: (sid, verdict) => call(`/sessions/${sid}/verdict`, { method: "POST", body: { verdict } }),
    review: (sid, code, persona, failedAttempts = 0) =>
      call(`/sessions/${sid}/review`, {
        method: "POST",
        body: { code, persona, failed_attempts: failedAttempts },
      }),
    card: (sid) => call(`/sessions/${sid}/card`),
    // Two calls on purpose: fetching the answers alongside the questions would
    // put them one devtools tab away, and answering before you see a good
    // answer is the only part of the exercise that teaches anything.
    interview: (sid, code, limit = 4) =>
      call(`/sessions/${sid}/interview`, { method: "POST", body: { code, limit } }),
    interviewAnswers: (sid, code, limit = 4) =>
      call(`/sessions/${sid}/interview/answers`, { method: "POST", body: { code, limit } }),
    unlocked: (sid) => call(`/sessions/${sid}/unlocked`),
    progress: () => call("/progress"),
    personas: () => call("/personas", { auth: false }),
    feedback: (slug, level, reason, note) =>
      call("/feedback", { method: "POST", body: { slug, level, reason, note } }),
  };
})();
