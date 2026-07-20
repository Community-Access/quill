/* QuillBeacon popup: capture controls. Sends commands to the background. */

const status = document.getElementById("status");

function setStatus(text, ok) {
  status.textContent = text;
  status.className = ok ? "ok" : "err";
}

function extras() {
  const tags = document.getElementById("tags").value.trim();
  return {
    note: document.getElementById("note").value.trim(),
    tags: tags ? tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
    collection: document.getElementById("collection").value.trim()
  };
}

function send(cmd, extra) {
  setStatus("Working...", true);
  chrome.runtime.sendMessage(cmd, (res) => {
    if (chrome.runtime.lastError) {
      setStatus(chrome.runtime.lastError.message, false);
      return;
    }
    if (res && res.ok) {
      const n = res.count != null ? res.count + " captured" : "Captured";
      setStatus(n, true);
    } else {
      setStatus((res && res.error) || "Failed", false);
    }
  });
}

document.getElementById("b-page").addEventListener("click", () =>
  send({ cmd: "capture", mode: "page", ...extras() }));
document.getElementById("b-selection").addEventListener("click", () =>
  send({ cmd: "capture", mode: "selection", ...extras() }));
document.getElementById("b-heading").addEventListener("click", () =>
  send({ cmd: "capture", mode: "heading", ...extras() }));
document.getElementById("b-link").addEventListener("click", () =>
  send({ cmd: "capture", mode: "link", ...extras() }));
document.getElementById("b-media").addEventListener("click", () =>
  send({ cmd: "capture", mode: "media", ...extras() }));
document.getElementById("b-all").addEventListener("click", () =>
  send({ cmd: "capture-all", ...extras() }));
document.getElementById("b-search").addEventListener("click", () =>
  send({ cmd: "open-search" }));

document.getElementById("opts").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

// Quick health check on open so the user knows the bridge is reachable.
chrome.runtime.sendMessage({ cmd: "health" }, (res) => {
  if (res && res.ok) setStatus("Bridge connected.", true);
  else setStatus("Bridge not reachable. Open Options to set the token.", false);
});