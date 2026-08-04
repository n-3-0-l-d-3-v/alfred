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
