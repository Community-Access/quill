# QuillBeacon Browser Extensions

Capture from the browser into QuillBeacon over a localhost bridge. No data
leaves the machine: the extension POSTs to `http://127.0.0.1:8752` on the
desktop app's capture bridge, authenticated with a shared bearer token.

## Two packages, one codebase

- `chromium/` -- Manifest V3 service-worker extension. Load it in **Chrome**
  (`chrome://extensions` > Developer mode > Load unpacked) and **Edge**
  (`edge://extensions` > Developer mode > Load unpacked).
- `firefox/` -- Manifest V3 with `background.scripts` and a `gecko` id. Load
  in **Firefox** (`about:debugging` > This Firefox > Load Temporary Add-on,
  pick `manifest.json`).

The content/background/popup/options JS is shared; only the manifest differs
(Firefox uses `background.scripts` + `browser_specific_settings.gecko`).

## Setup

1. In QuillBeacon, open **Tools > Capture Bridge** (or Ctrl+Shift+B). Copy the
   token shown.
2. Open the extension's **Options**, paste the token, set the bridge URL
   (default `http://127.0.0.1:8752`), and click **Test connection**.

## Capture modes

- **Page** -- capture the current page (title + URL).
- **Selection** -- capture the selected text as a note (tagged `selection`).
- **Heading** -- capture the nearest heading + the selection's text quote.
- **Link** -- capture the selected link's href.
- **Media time** -- capture the current `<video>`/`<audio>` position as a
  time-point bookmark (tagged `timepoint`), resumable in the built-in player.
- **All tabs** -- batch-capture every open tab in the window.
- Note, tags, and collection fields attach to any capture.

Right-click for context-menu captures (selection, link, page). Keyboard
shortcuts: `Alt+Shift+B` captures the page.

## Security

- The bridge binds to `127.0.0.1` only (PRD 46.4).
- Every request must carry the shared token (`X-QuillBeacon-Token`); the
  bridge rejects non-extension origins even with a token.
- The token is generated on first run and stored in the QuillBeacon data dir.