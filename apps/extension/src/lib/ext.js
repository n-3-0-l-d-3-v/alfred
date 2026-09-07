/**
 * Cross-browser shim. Firefox exposes `browser.*` (promise-based); Chrome
 * exposes `chrome.*` (promise-based for most MV3 APIs). Aliasing gets us
 * ~95% of the way without pulling in the webextension-polyfill npm package,
 * which would force a Node build step we deliberately don't have.
 */
globalThis.LL = globalThis.LL || {};

LL.ext = globalThis.browser ?? globalThis.chrome;
LL.isFirefox = typeof globalThis.browser !== "undefined" && !!globalThis.browser.runtime?.getBrowserInfo;

/** Promise-safe sendMessage that works on both engines. */
LL.sendMessage = function (msg) {
  try {
    const r = LL.ext.runtime.sendMessage(msg);
    return r && typeof r.then === "function"
      ? r
      : new Promise((res) => LL.ext.runtime.sendMessage(msg, res));
  } catch (e) {
    return Promise.reject(e);
  }
};

/**
 * OAuth in a browser extension. `launchWebAuthFlow` opens the provider's page
 * in a controlled popup and resolves with the redirect URL it lands on — the
 * extension never sees the user's GitHub password, and the redirect target is
 * an extension-owned URL that no web page can claim.
 */
LL.identity = {
  /** The redirect URI to register in the GitHub OAuth app settings. */
  redirectUri() {
    return LL.ext.identity.getRedirectURL();
  },

  /** Run the flow and return the `code` query parameter GitHub sends back. */
  async getGithubCode(clientId) {
    const authUrl =
      "https://github.com/login/oauth/authorize" +
      `?client_id=${encodeURIComponent(clientId)}` +
      `&redirect_uri=${encodeURIComponent(this.redirectUri())}` +
      // Identity only. Alfred never reads or writes a user's repositories,
      // so it asks for no scopes beyond the implicit public profile.
      "&scope=read:user%20user:email" +
      `&state=${crypto.randomUUID()}`;

    const opts = { url: authUrl, interactive: true };
    const redirect = await new Promise((resolve, reject) => {
      const maybe = LL.ext.identity.launchWebAuthFlow(opts, (url) => {
        const err = LL.ext.runtime.lastError;
        if (err) reject(new Error(err.message));
        else resolve(url);
      });
      // Chrome MV3 also returns a promise; Firefox only uses the callback.
      if (maybe && typeof maybe.then === "function") maybe.then(resolve, reject);
    });

    if (!redirect) throw new Error("Sign-in was cancelled.");
    const code = new URL(redirect).searchParams.get("code");
    if (!code) throw new Error("GitHub didn't return an authorization code.");
    return code;
  },
};

LL.storage = {
  async get(keys) {
    const r = LL.ext.storage.local.get(keys);
    return r && typeof r.then === "function"
      ? r
      : new Promise((res) => LL.ext.storage.local.get(keys, res));
  },
  async set(obj) {
    const r = LL.ext.storage.local.set(obj);
    return r && typeof r.then === "function"
      ? r
      : new Promise((res) => LL.ext.storage.local.set(obj, res));
  },
};
