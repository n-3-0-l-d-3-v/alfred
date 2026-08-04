/**
 * Background (service worker on Chrome, event page on Firefox).
 * Routes panel <-> content-script messages and opens the side panel.
 */
importScriptsSafe();

function importScriptsSafe() {
  // Chrome MV3 service workers support importScripts; Firefox event pages load
  // scripts via the manifest instead, so this is a no-op there.
  try {
    if (typeof importScripts === "function") importScripts("lib/ext.js");
  } catch (_) {
    /* Firefox: lib/ext.js is already loaded by the manifest */
  }
}

const ext = globalThis.browser ?? globalThis.chrome;

// Chrome: clicking the toolbar icon opens the side panel.
if (ext.sidePanel?.setPanelBehavior) {
  ext.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
}

// Firefox: clicking the action toggles the sidebar.
if (ext.sidebarAction?.toggle && ext.action?.onClicked) {
  ext.action.onClicked.addListener(() => ext.sidebarAction.toggle());
}

// Relay verdict / navigation events from the content script to the panel.
ext.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "LL_VERDICT" || msg?.type === "LL_NAVIGATED") {
    ext.runtime.sendMessage(msg).catch(() => {});
    sendResponse({ ok: true });
    return true;
  }
  return false;
});
