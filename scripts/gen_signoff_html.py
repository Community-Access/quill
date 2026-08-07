"""Generate the interactive sign-off checklist pages.

Converts every ``docs/planning/signoff/SIGNOFF-*.md`` (plus the master
``QUILL-1.0.0-SIGNOFF.md``) into a self-contained HTML page whose checkboxes
REMEMBER their state: each box writes to ``localStorage`` as it is toggled, so
closing Edge (or any browser) and reopening the file restores every check.

State keys are content-derived (a hash of the item's own text), so checking
boxes survives regeneration of the pages and edits elsewhere in the file; only
rewording an item itself resets that item. Export/Import buttons round-trip
the whole state as a JSON file for backup or moving between machines.

Usage::

    python scripts/gen_signoff_html.py

Output: ``docs/planning/signoff/interactive/<name>.html`` + ``index.html``.
Accessible by construction: native checkboxes, real labels, one ``h1`` per
page, section headings preserved, a live progress line, no external assets.
"""

from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path

SIGNOFF_DIR = Path(__file__).resolve().parent.parent / "docs" / "planning" / "signoff"
OUT_DIR = SIGNOFF_DIR / "interactive"

_CHECKBOX = re.compile(r"\[( |x|X)\]")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")


def _inline(text: str) -> str:
    """Minimal inline markdown -> HTML (escape first, then code/bold)."""
    out = html.escape(text, quote=False)
    out = _INLINE_CODE.sub(r"<code>\1</code>", out)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    return out


def _item_key(slug: str, raw_line: str, seen: dict[str, int]) -> str:
    """Stable per-item key: content hash + occurrence counter for duplicates."""
    digest = hashlib.sha1(raw_line.strip().encode("utf-8")).hexdigest()[:12]
    n = seen.get(digest, 0)
    seen[digest] = n + 1
    return f"{slug}:{digest}:{n}"


def _convert_item(line: str, slug: str, seen: dict[str, int]) -> str | None:
    """One ``- [ ] ...`` list item -> HTML with persistent checkboxes."""
    stripped = line.lstrip()
    if not stripped.startswith("- ") or "[" not in stripped:
        return None
    body = stripped[2:]
    if not _CHECKBOX.search(body):
        return None
    item_key = _item_key(slug, line, seen)
    # Plain-text label for the aria-labels: the item with boxes/markup removed.
    plain = _CHECKBOX.sub("", body)
    plain = re.sub(r"[`*]", "", plain)
    plain = re.sub(r"\s+", " ", plain).strip(" -—·")
    parts: list[str] = []
    cursor = 0
    box_index = 0
    for match in _CHECKBOX.finditer(body):
        parts.append(_inline(body[cursor : match.start()]))
        # The aspect letter (W/S/A) usually follows the box; use it in the name.
        tail = body[match.end() :].lstrip()
        aspect = tail[0] if tail[:1] in ("W", "S", "A") else ""
        aspect_name = {"W": "Works", "S": "Surface-exact", "A": "Accessible"}.get(aspect, "Done")
        key = f"{item_key}:{box_index}"
        label = html.escape(f"{aspect_name}: {plain[:160]}", quote=True)
        parts.append(f'<input type="checkbox" class="so" data-key="{key}" aria-label="{label}">')
        cursor = match.end()
        box_index += 1
    parts.append(_inline(body[cursor:]))
    return f"<li>{''.join(parts)}</li>"


def _convert(md_path: Path) -> str:
    slug = md_path.stem
    seen: dict[str, int] = {}
    out: list[str] = []
    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped == "---":
            i += 1
            continue
        # Table -> a real <table> (the environment matrix must be readable as
        # tabular data by a screen reader, not "| E1 | ..." paragraphs).
        is_table = stripped.startswith("|") and i + 1 < n
        if is_table and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<div class="tablewrap"><table>')
            out.append(
                "<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header) + "</tr></thead>"
            )
            out.append("<tbody>")
            for row in rows:
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table></div>")
            continue
        # Any bullet list (checkbox items become persistent checkboxes; plain
        # bullets keep real list semantics instead of degrading to <p>- ...</p>).
        if stripped.startswith("- "):
            out.append("<ul>")
            while i < n and lines[i].strip().startswith("- "):
                item = _convert_item(lines[i], slug, seen)
                if item is not None:
                    out.append(item)
                else:
                    out.append(f"<li>{_inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("</ul>")
            continue
        if stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            out.append(f"<h{level}>{_inline(stripped.lstrip('#').strip())}</h{level}>")
        elif stripped.startswith(">"):
            out.append(f"<blockquote><p>{_inline(stripped.lstrip('> '))}</p></blockquote>")
        else:
            out.append(f"<p>{_inline(stripped)}</p>")
        i += 1
    return "\n".join(out)


_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} (interactive sign-off)</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 60em; margin: 0 auto;
         padding: 1em; line-height: 1.5; }}
  /* Keep a focus target clear of the sticky bar when scrolled to (WCAG 2.4.11
     Focus Not Obscured) -- matters now that hiding an item moves focus. */
  html {{ scroll-padding-top: 4em; }}
  li {{ margin: 0.35em 0; }}
  input.so {{ width: 1.1em; height: 1.1em; margin-right: 0.3em; }}
  .bar {{ position: sticky; top: 0; background: Canvas; padding: 0.5em 0;
          border-bottom: 1px solid GrayText; }}
  @media (prefers-color-scheme: dark) {{ body {{ background: #111; color: #eee; }}
    .bar {{ background: #111; }} }}
  .bar button, .bar a {{ margin-right: 0.5em; }}
  li[hidden] {{ display: none; }}
  .tablewrap {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; }}
  th, td {{ border: 1px solid GrayText; padding: 0.3em 0.6em; text-align: left; }}
  .visually-hidden {{ position: absolute; width: 1px; height: 1px; margin: -1px;
    padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }}
</style>
</head>
<body>
<div class="bar" role="group" aria-label="Sign-off progress and state">
  <span id="progress" role="status">Loading…</span>
  <button id="toggleHide" type="button" aria-pressed="false">Hide checked items</button>
  <button id="export">Export progress…</button>
  <button id="import">Import progress…</button>
  <input type="file" id="importFile" accept=".json" hidden>
  <a href="index.html">All checklists</a>
  <span id="hideStatus" class="visually-hidden" aria-live="polite"></span>
</div>
{body}
<script>
(function () {{
  var PREFIX = "quill-signoff:";
  var HIDE_KEY = PREFIX + "__hideChecked__";
  var boxes = document.querySelectorAll("input.so");
  var toggleBtn = document.getElementById("toggleHide");
  var hideStatus = document.getElementById("hideStatus");
  var checkItems = [];
  document.querySelectorAll("li").forEach(function (li) {{
    if (li.querySelector("input.so")) checkItems.push(li);
  }});
  function refresh() {{
    var done = 0;
    boxes.forEach(function (b) {{ if (b.checked) done++; }});
    document.getElementById("progress").textContent =
      done + " of " + boxes.length + " boxes checked";
  }}
  // An item is "checked off" only when every checkbox on it (Works / Surface /
  // Accessible) is ticked; a partly-done item stays visible.
  function itemDone(li) {{
    var bs = li.querySelectorAll("input.so");
    if (bs.length === 0) return false;
    for (var i = 0; i < bs.length; i++) {{ if (!bs[i].checked) return false; }}
    return true;
  }}
  function hideActive() {{ return localStorage.getItem(HIDE_KEY) === "1"; }}
  function applyHide() {{
    var on = hideActive();
    var hidden = 0;
    checkItems.forEach(function (li) {{
      li.hidden = on && itemDone(li);
      if (li.hidden) hidden++;
    }});
    if (toggleBtn) toggleBtn.setAttribute("aria-pressed", on ? "true" : "false");
    return hidden;
  }}
  // When ticking a box hides the item the user is standing on, move focus off
  // the now-hidden control to the next visible box (else the previous, else the
  // toggle) so keyboard/screen-reader focus is never stranded.
  function focusAfterHide(box) {{
    var arr = Array.prototype.slice.call(boxes);
    var start = arr.indexOf(box);
    for (var i = start + 1; i < arr.length; i++) {{
      if (!arr[i].closest("li").hidden) {{ arr[i].focus(); return; }}
    }}
    for (var j = start - 1; j >= 0; j--) {{
      if (!arr[j].closest("li").hidden) {{ arr[j].focus(); return; }}
    }}
    if (toggleBtn) toggleBtn.focus();
  }}
  boxes.forEach(function (b) {{
    var key = PREFIX + b.dataset.key;
    b.checked = localStorage.getItem(key) === "1";
    b.addEventListener("change", function () {{
      if (b.checked) localStorage.setItem(key, "1");
      else localStorage.removeItem(key);
      refresh();
      if (hideActive()) {{
        var li = b.closest("li");
        var willHide = b.checked && li && itemDone(li);
        applyHide();
        if (willHide && li.hidden) {{
          // The item the user just completed is vanishing; say so (brief), then
          // move focus off the now-hidden control.
          if (hideStatus) hideStatus.textContent = "Item completed and hidden.";
          focusAfterHide(b);
        }}
      }}
    }});
  }});
  refresh();
  if (toggleBtn && boxes.length > 0) {{
    applyHide();
    toggleBtn.addEventListener("click", function () {{
      localStorage.setItem(HIDE_KEY, hideActive() ? "0" : "1");
      var hidden = applyHide();
      if (hideStatus) {{
        hideStatus.textContent = hideActive()
          ? (hidden + (hidden === 1 ? " checked item hidden." : " checked items hidden."))
          : "Showing all items.";
      }}
    }});
  }} else if (toggleBtn) {{
    toggleBtn.hidden = true;  // no checkboxes on this page (e.g. the index)
  }}
  document.getElementById("export").addEventListener("click", function () {{
    var state = {{}};
    for (var i = 0; i < localStorage.length; i++) {{
      var k = localStorage.key(i);
      if (k.indexOf(PREFIX) === 0) state[k] = localStorage.getItem(k);
    }}
    var blob = new Blob([JSON.stringify(state, null, 1)],
                        {{ type: "application/json" }});
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "quill-signoff-progress.json";
    a.click();
  }});
  var fileInput = document.getElementById("importFile");
  document.getElementById("import").addEventListener("click", function () {{
    fileInput.click();
  }});
  fileInput.addEventListener("change", function () {{
    var f = fileInput.files[0];
    if (!f) return;
    f.text().then(function (text) {{
      var state;
      try {{
        state = JSON.parse(text);
      }} catch (e) {{
        if (hideStatus) hideStatus.textContent = "Import failed: not a valid progress file.";
        return;
      }}
      var applied = 0;
      Object.keys(state).forEach(function (k) {{
        if (k.indexOf(PREFIX) === 0) {{ localStorage.setItem(k, state[k]); applied++; }}
      }});
      if (!applied) {{
        if (hideStatus) hideStatus.textContent = "Import failed: no sign-off progress found.";
        return;
      }}
      boxes.forEach(function (b) {{
        b.checked = localStorage.getItem(PREFIX + b.dataset.key) === "1";
      }});
      refresh();
      if (boxes.length > 0) applyHide();
      if (hideStatus) hideStatus.textContent = "Progress imported.";
    }}, function () {{
      if (hideStatus) hideStatus.textContent = "Import failed: the file could not be read.";
    }});
  }});
}})();
</script>
</body>
</html>
"""


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    sources = sorted(SIGNOFF_DIR.glob("*.md"))
    links: list[str] = []
    for md in sources:
        body = _convert(md)
        page = _PAGE.format(title=html.escape(md.stem), body=body)
        out = OUT_DIR / f"{md.stem}.html"
        out.write_text(page, encoding="utf-8", newline="\n")
        boxes = page.count('class="so"')
        links.append(
            f'<li><a href="{md.stem}.html">{html.escape(md.stem)}</a> ({boxes} boxes)</li>'
        )
        print(f"{out.name}: {boxes} checkboxes")
    index_body = (
        "<h1>QUILL 1.0.0 sign-off — interactive checklists</h1>"
        "<p>Open a checklist, check boxes as you verify; state is saved in the "
        "browser (localStorage) the moment a box is toggled and restored when "
        "you come back — including after closing the browser. Use Export on "
        "each page to back up progress to a JSON file.</p>"
        f"<ul>{''.join(links)}</ul>"
    )
    (OUT_DIR / "index.html").write_text(
        _PAGE.format(title="QUILL sign-off index", body=index_body),
        encoding="utf-8",
        newline="\n",
    )
    print(f"index.html: {len(links)} checklists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
