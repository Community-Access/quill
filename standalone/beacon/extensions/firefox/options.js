/* QuillBeacon options: persist bridge URL + token, test connection. */

const status = document.getElementById("status");

function setStatus(text, ok) {
  status.textContent = text;
  status.className = ok ? "ok" : "err";
}

async function load() {
  const cfg = await chrome.storage.sync.get(["base", "token"]);
  document.getElementById("base").value = cfg.base || "http://127.0.0.1:8752";
  document.getElementById("token").value = cfg.token || "";
}

document.getElementById("save").addEventListener("click", async () => {
  const base = document.getElementById("base").value.trim().replace(/\/$/, "");
  const token = document.getElementById("token").value.trim();
  await chrome.storage.sync.set({ base, token });
  setStatus("Saved.", true);
});

document.getElementById("test").addEventListener("click", async () => {
  const base = document.getElementById("base").value.trim().replace(/\/$/, "");
  const token = document.getElementById("token").value.trim();
  await chrome.storage.sync.set({ base, token });
  try {
    const r = await fetch(base + "/health", { headers: { "X-QuillBeacon-Token": token } });
    const j = await r.json();
    if (j.ok) setStatus("Bridge reachable: " + (j.service || "ok"), true);
    else setStatus("Bridge responded but not ok: " + JSON.stringify(j), false);
  } catch (e) {
    setStatus("Cannot reach bridge: " + e.message, false);
  }
});

load();