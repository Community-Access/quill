/* QuillBeacon capture background (MV3 service worker).
 *
 * Receives capture requests from the popup and context menu, gathers page
 * context via scripting.executeScript, and POSTs to the local capture bridge
 * (http://127.0.0.1:<port>/capture) with the shared bearer token. All network
 * egress is to 127.0.0.1 only -- nothing leaves the machine.
 */

const DEFAULT_BASE = "http://127.0.0.1:8752";
const NATIVE_HOST = "com.communityaccess.quillbeacon";

async function config() {
  const cfg = await chrome.storage.sync.get(["base", "token"]);
  return {
    base: (cfg.base || DEFAULT_BASE).replace(/\/$/, ""),
    token: cfg.token || ""
  };
}

async function gatherContext(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => self.quillbeaconGatherContext()
  });
  return results && results[0] && results[0].result ? results[0].result : null;
}

function buildPayload(mode, ctx, extra) {
  extra = extra || {};
  const p = {
    url: ctx.url,
    title: ctx.title,
    source: "extension",
    tags: extra.tags || [],
    collection: extra.collection || "",
    note: extra.note || ""
  };
  if (mode === "selection") {
    p.note = p.note || ctx.selection;
    p.tags = p.tags.concat(["selection"]);
    p.type_hint = "textQuote";
  } else if (mode === "heading") {
    p.note = p.note || (ctx.heading ? ("Heading: " + ctx.heading) : "");
    if (ctx.textQuote) p.note += "\n" + ctx.textQuote;
    p.tags = p.tags.concat(["heading"]);
  } else if (mode === "link") {
    if (ctx.link) p.url = ctx.link;
    p.tags = p.tags.concat(["link"]);
  } else if (mode === "media") {
    if (ctx.media) {
      p.media_start_ms = ctx.media.media_start_ms;
      p.note = p.note || ("Media at " + fmtTime(ctx.media.currentTime) + " / " + fmtTime(ctx.media.duration));
      p.tags = p.tags.concat(["timepoint"]);
      p.type_hint = "timePoint";
      if (ctx.media.src) p.url = ctx.media.src;
    }
  } else {
    // page
    p.tags = p.tags.concat(["page"]);
  }
  return p;
}

function fmtTime(s) {
  if (!s || !isFinite(s)) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return m + ":" + String(sec).padStart(2, "0");
}

async function postCapture(payload) {
  const httpRes = await httpCapture(payload);
  if (httpRes.ok) return httpRes;
  // Bridge unreachable (not running / loopback blocked) -> native messaging host.
  const nat = await nativeSend(Object.assign({ type: "capture" }, payload));
  if (nat.ok) return nat;
  return httpRes; // surface the original HTTP error when native also fails
}

async function httpCapture(payload) {
  const { base, token } = await config();
  if (!token) {
    return { ok: false, error: "No bridge token set. Open extension Options." };
  }
  try {
    const r = await fetch(base + "/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-QuillBeacon-Token": token },
      body: JSON.stringify(payload)
    });
    return await r.json();
  } catch (e) {
    return { ok: false, error: "Cannot reach bridge at " + base + ". Is QuillBeacon running? " + e.message };
  }
}

// Native messaging fallback: the browser spawns the host as a stdio subprocess
// and enforces which extension may talk to it, so no bearer token is needed.
function nativeSend(message) {
  return new Promise((resolve) => {
    let settled = false;
    let port;
    try {
      port = chrome.runtime.connectNative(NATIVE_HOST);
    } catch (e) {
      resolve({ ok: false, error: "Native host unavailable: " + e.message });
      return;
    }
    const finish = (val) => {
      if (settled) return;
      settled = true;
      try { port.disconnect(); } catch (e) { /* already gone */ }
      resolve(val);
    };
    port.onMessage.addListener((resp) => finish(resp));
    port.onDisconnect.addListener(() => {
      const err = chrome.runtime.lastError;
      finish({ ok: false, error: err ? err.message : "native host disconnected" });
    });
    try {
      port.postMessage(message);
    } catch (e) {
      finish({ ok: false, error: "native postMessage failed: " + e.message });
    }
  });
}

async function captureActive(mode, extra) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return { ok: false, error: "No active tab." };
  const ctx = await gatherContext(tab.id);
  if (!ctx) return { ok: false, error: "Could not read page context." };
  return postCapture(buildPayload(mode, ctx, extra));
}

async function captureAllTabs(extra) {
  const tabs = await chrome.tabs.query({ currentWindow: true });
  const { base, token } = await config();
  if (!token) return { ok: false, error: "No bridge token set." };
  const items = [];
  for (const tab of tabs) {
    if (!tab.url || /^chrome:|edge:|about:/.test(tab.url)) continue;
    let ctx = null;
    try { ctx = await gatherContext(tab.id); } catch (e) { ctx = null; }
    if (!ctx) continue;
    items.push(buildPayload("page", ctx, extra));
  }
  try {
    const r = await fetch(base + "/capture-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-QuillBeacon-Token": token },
      body: JSON.stringify({ tabs: items })
    });
    return await r.json();
  } catch (e) {
    // Bridge unreachable -> native messaging fallback.
    const nat = await nativeSend({ type: "capture-batch", tabs: items });
    if (nat.ok) return nat;
    return { ok: false, error: "Cannot reach bridge: " + e.message };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    let res;
    if (msg.cmd === "capture") {
      res = await captureActive(msg.mode, { note: msg.note, tags: msg.tags, collection: msg.collection });
    } else if (msg.cmd === "capture-all") {
      res = await captureAllTabs({ tags: msg.tags, collection: msg.collection });
    } else if (msg.cmd === "health") {
      const { base, token } = await config();
      try {
        const r = await fetch(base + "/health");
        res = await r.json();
      } catch (e) {
        res = { ok: false, error: e.message };
      }
    } else if (msg.cmd === "open-search") {
      const { base } = await config();
      // The desktop app owns the search UI; the bridge exposes a health endpoint.
      // Opening search launches/focuses the app via a custom scheme fallback.
      chrome.tabs.create({ url: base + "/health" });
      res = { ok: true };
    } else {
      res = { ok: false, error: "unknown command" };
    }
    sendResponse(res);
  })();
  return true; // async response
});

// Context menu: right-click to capture a selection or link.
chrome.runtime.onInstalled.addListener(() => {
  try {
    chrome.contextMenus.create({ id: "qb-selection", title: "QuillBeacon: Capture selection", contexts: ["selection"] });
    chrome.contextMenus.create({ id: "qb-link", title: "QuillBeacon: Capture link", contexts: ["link"] });
    chrome.contextMenus.create({ id: "qb-page", title: "QuillBeacon: Capture page", contexts: ["page"] });
  } catch (e) { /* already exists */ }
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const mode = info.menuItemId === "qb-link" ? "link"
    : info.menuItemId === "qb-selection" ? "selection" : "page";
  (async () => {
    const ctx = await gatherContext(tab.id);
    if (mode === "link" && info.linkUrl) ctx.link = info.linkUrl;
    await postCapture(buildPayload(mode, ctx, {}));
  })();
});

// Keyboard commands.
chrome.commands.onCommand.addListener((cmd) => {
  if (cmd === "capture-page") captureActive("page", {});
  else if (cmd === "capture-selection") captureActive("selection", {});
});