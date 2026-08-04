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
      throw new Error(`Can't reach the LeetLearn server. Is it running? (${e.message})`);
    }
    const text = await res.text();
    const data = text ? JSON.parse(text) : {};
    if (!res.ok) {
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
    login: async (email) => {
      const r = await call("/auth/dev-login", { method: "POST", body: { email }, auth: false });
      await LL.storage.set({ token: r.token, userId: r.user_id, email });
      return r;
    },
    logout: () => LL.storage.set({ token: null }),
    isSignedIn: async () => !!(await token()),
    startSession: (slug, language) => call("/sessions", { method: "POST", body: { slug, language } }),
    hint: (sid, level, code, personalized = false) =>
      call(`/sessions/${sid}/hint`, { method: "POST", body: { level, code, personalized } }),
    verdict: (sid, verdict) => call(`/sessions/${sid}/verdict`, { method: "POST", body: { verdict } }),
    review: (sid, code, persona, failedAttempts = 0) =>
      call(`/sessions/${sid}/review`, {
        method: "POST",
        body: { code, persona, failed_attempts: failedAttempts },
      }),
    card: (sid) => call(`/sessions/${sid}/card`),
    unlocked: (sid) => call(`/sessions/${sid}/unlocked`),
    progress: () => call("/progress"),
    personas: () => call("/personas", { auth: false }),
    feedback: (slug, level, reason, note) =>
      call("/feedback", { method: "POST", body: { slug, level, reason, note } }),
  };
})();
