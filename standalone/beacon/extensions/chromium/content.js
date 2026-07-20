/* QuillBeacon content context gatherer.
 *
 * Runs in the page via chrome.scripting.executeScript. Returns everything the
 * popup might need for any capture mode; the background/popup selects fields
 * per mode. No external network access here -- the bridge POST happens in the
 * background, which already has the host_permissions for 127.0.0.1.
 */

function quillbeaconGatherContext() {
  const sel = window.getSelection();
  const selectionText = sel ? sel.toString().trim() : "";
  let rangeTextQuote = "";
  let heading = "";
  let linkHref = "";

  // Text quote (exact + context) from the selection range.
  if (sel && sel.rangeCount && selectionText) {
    try {
      const range = sel.getRangeAt(0);
      const node = range.commonAncestorContainer;
      const el = node.nodeType === 1 ? node : node.parentElement;
      if (el) {
        // Nearest preceding heading.
        let h = el.closest("h1,h2,h3,h4,h5,h6");
        let walker = el;
        while (!h && walker) {
          const prev = walker.previousElementSibling;
          if (prev) {
            h = prev.matches && prev.matches("h1,h2,h3,h4,h5,h6") ? prev
              : prev.querySelector && prev.querySelector("h1,h2,h3,h4,h5,h6");
          }
          if (h) break;
          walker = walker.parentElement;
        }
        if (h) heading = h.textContent.trim();
        // Link containing the selection.
        const a = el.closest("a");
        if (a) linkHref = a.href;
      }
      rangeTextQuote = range.toString().trim();
    } catch (e) { /* leave defaults */ }
  }

  // Media element (first video/audio on the page, prefer one that is playing).
  const mediaEls = Array.from(document.querySelectorAll("video, audio"));
  const mediaEl = mediaEls.find((m) => !m.paused) || mediaEls[0] || null;
  let mediaTime = null;
  if (mediaEl) {
    mediaTime = {
      currentTime: mediaEl.currentTime || 0,
      duration: mediaEl.duration || 0,
      paused: !!mediaEl.paused,
      src: mediaEl.currentSrc || mediaEl.src || "",
      media_start_ms: Math.round((mediaEl.currentTime || 0) * 1000)
    };
  }

  return {
    url: location.href,
    title: document.title || location.href,
    selection: selectionText,
    textQuote: rangeTextQuote,
    heading: heading,
    link: linkHref,
    media: mediaTime
  };
}

// expose for executeScript func injection
self.quillbeaconGatherContext = quillbeaconGatherContext;