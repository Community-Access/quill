"""Generate the interactive Acceptance Test Book runner.

Converts every Markdown file in ``docs/release/acceptance/`` into a
self-contained, screen-reader-first HTML page under
``docs/release/acceptance/interactive/``, plus an ``index.html`` dashboard.

What the pages add over the printed book:

- Every scenario (an ``## FILE-01 — ...`` block ending in a **Sign off** line)
  becomes a collapsible ``<details>`` region with a real sign-off control:
  a Pass / Fail / Blocked / N-A radio group, the three Works /
  Surface-exact / Accessible checkboxes, and a Notes field.
- Every ``- [ ]`` checklist line (the dialog contract pages) becomes a
  persistent checkbox, exactly like the sign-off checklists.
- All state persists to ``localStorage`` the moment it changes and is
  restored on reopen — including after closing the browser. Export/Import
  buttons round-trip the whole state as JSON for backup or another machine.
- A "Hide completed" toggle hides scenarios you have recorded (and fully
  checked checklist items/groups); "Show all" brings them back. Expand all /
  Collapse all drive the disclosure state of every section.
- The index shows live per-section and overall progress computed from the
  same saved state.

State keys are content-stable (scenario IDs like ``FILE-01`` and content
hashes for checklist lines), so progress survives regeneration; only
rewording a checklist line resets that line.

Usage::

    python scripts/gen_acceptance_html.py

Accessible by construction: native controls with real labels, one ``h1``
per page, headings preserved inside ``<summary>`` for heading navigation,
a live progress line, focus rescue when the item under focus hides, no
external assets, dark-mode aware, ASCII-only UI chrome.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

ACCEPT_DIR = Path(__file__).resolve().parent.parent / "docs" / "release" / "acceptance"
OUT_DIR = ACCEPT_DIR / "interactive"

# Recommended run order (README section 4). Files not listed sort after, alphabetically.
RUN_ORDER = [
    "README",
    "00-getting-started",
    "section-file",
    "section-edit",
    "section-navigate",
    "section-format",
    "section-view",
    "section-table",
    "section-editor-behaviors",
    "section-tools-ai",
    "section-tools-speech",
    "section-tools-misc",
    "section-power",
    "section-braille",
    "section-vault",
    "section-help",
    "section-github",
    "section-settings",
    "section-quillins",
    "section-whisperer",
    "section-app-adp",
    "section-accessibility",
    "app-radio",
    "app-weather",
    "gated-absence",
    "dialogs",
    "install-matrix",
]

_CHECKBOX = re.compile(r"\[( |x|X)\]")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_SCENARIO_ID = re.compile(r"^([A-Z][A-Z0-9]*-\d+[a-z]?)\b")
_SIGNOFF_LINE = re.compile(r"^\*\*Sign off\*\*")
_ASPECT_LINE = re.compile(r"^`?\[ \] Works`?")
_ORDERED = re.compile(r"^(\d+)\.\s+(.*)$")
_FOOTER_FIELD = re.compile(r"^- ([^:`]+):\s*(.*)$")


def _inline(text: str) -> str:
    """Minimal inline markdown -> HTML (escape first, then code/bold/italic/link)."""
    out = html.escape(text, quote=False)
    out = _INLINE_CODE.sub(r"<code>\1</code>", out)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    out = _ITALIC.sub(r"<em>\1</em>", out)
    out = _LINK.sub(r'<a href="\2">\1</a>', out)
    return out


def _hash_key(raw: str) -> str:
    return hashlib.sha1(raw.strip().encode("utf-8")).hexdigest()[:12]


class _Page:
    """Accumulates the converted body plus control counts for one page."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.parts: list[str] = []
        self.scenario_count = 0
        self.checkbox_count = 0
        self._seen_cb: dict[str, int] = {}
        self._seen_sid: dict[str, int] = {}
        self.title = slug

    # -- controls ----------------------------------------------------------

    def checklist_item(self, body: str) -> str:
        """One ``- [ ] ...`` line -> li with persistent checkbox(es)."""
        digest = _hash_key(body)
        n = self._seen_cb.get(digest, 0)
        self._seen_cb[digest] = n + 1
        base = f"{self.slug}:cb:{digest}:{n}"
        plain = _CHECKBOX.sub("", body)
        plain = re.sub(r"[`*]", "", plain)
        plain = re.sub(r"\s+", " ", plain).strip(" -.")
        parts: list[str] = []
        cursor = 0
        box_index = 0
        for match in _CHECKBOX.finditer(body):
            parts.append(_inline(body[cursor : match.start()]))
            key = base if box_index == 0 else f"{base}:{box_index}"
            label = html.escape(f"Done: {plain[:160]}", quote=True)
            parts.append(
                f'<input type="checkbox" class="cb" data-key="{key}" aria-label="{label}">'
            )
            self.checkbox_count += 1
            cursor = match.end()
            box_index += 1
        parts.append(_inline(body[cursor:]))
        return f'<li class="check">{"".join(parts)}</li>'

    def scenario_controls(self, sid: str, heading: str) -> str:
        """The persistent sign-off control block for one scenario."""
        n = self._seen_sid.get(sid, 0)
        self._seen_sid[sid] = n + 1
        if n:
            sid = f"{sid}.{n}"
        base = f"{self.slug}:scn:{sid}"
        self.scenario_count += 1
        short = html.escape(heading[:120], quote=True)
        radios = []
        for value, label in (
            ("", "Not run"),
            ("pass", "Pass"),
            ("fail", "Fail"),
            ("blocked", "Blocked"),
            ("na", "N/A"),
        ):
            checked = " checked" if value == "" else ""
            radios.append(
                f'<label><input type="radio" class="outcome" name="{base}:outcome" '
                f'value="{value}"{checked}> {label}</label>'
            )
        aspects = []
        aspect_defs = (("works", "Works"), ("surface", "Surface-exact"), ("access", "Accessible"))
        for akey, label in aspect_defs:
            aspects.append(
                f'<label><input type="checkbox" class="aspect" '
                f'data-key="{base}:{akey}"> {label}</label>'
            )
        return (
            f'<fieldset class="scn" data-base="{base}" data-sid="{html.escape(sid, quote=True)}">'
            f"<legend>Sign off - {short}</legend>"
            f'<div class="row" role="radiogroup" aria-label="Outcome for {short}">'
            f"{' '.join(radios)}</div>"
            f'<div class="row">{" ".join(aspects)}</div>'
            f'<div class="row"><label>Notes: <input type="text" class="notes" size="60" '
            f'data-key="{base}:notes"></label></div>'
            "</fieldset>"
        )

    def footer_field(self, label: str, value: str) -> str:
        key = f"{self.slug}:meta:{_hash_key(label)}"
        val = html.escape(value, quote=True)
        return (
            f'<li><label>{_inline(label)}: <input type="text" class="meta" size="40" '
            f'data-key="{key}" value="{val}"></label></li>'
        )


def _render_lines(lines: list[str], page: _Page, *, in_footer: bool = False) -> list[str]:
    """Line-based Markdown -> HTML with fence, table, list, quote handling."""
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Fenced code block: emit literally, never convert checkboxes inside.
        if stripped.startswith("```"):
            fence: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                fence.append(lines[i])
                i += 1
            i += 1  # closing fence
            code = html.escape("\n".join(fence), quote=False)
            out.append(f"<pre><code>{code}</code></pre>")
            continue

        if not stripped:
            i += 1
            continue

        if stripped == "---":
            i += 1
            continue

        # Table.
        is_table = stripped.startswith("|") and i + 1 < n
        if is_table and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<div class="tablewrap"><table>')
            head_cells = "".join(f"<th>{_inline(c)}</th>" for c in header)
            out.append(f"<thead><tr>{head_cells}</tr></thead>")
            out.append("<tbody>")
            for row in rows:
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table></div>")
            continue

        # Blockquote.
        if stripped.startswith(">"):
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            body = " ".join(q for q in quote if q)
            out.append(f"<blockquote><p>{_inline(body)}</p></blockquote>")
            continue

        # Sign-off scenario control lines are handled by the caller; if one
        # slips through (unexpected layout), render it as a paragraph.

        # Unordered list (with one level of nesting and checkbox conversion).
        if stripped.startswith("- "):
            out.append("<ul>")
            while i < n:
                cur = lines[i]
                curs = cur.strip()
                if not curs.startswith("- "):
                    # wrapped continuation of the previous item
                    indented = cur.startswith("  ") or cur.startswith("\t")
                    if curs and indented and out[-1].endswith("</li>"):
                        out[-1] = out[-1][: -len("</li>")] + " " + _inline(curs) + "</li>"
                        i += 1
                        continue
                    break
                body = curs[2:]
                if in_footer:
                    m = _FOOTER_FIELD.match(curs)
                    if m:
                        out.append(page.footer_field(m.group(1).strip(), m.group(2).strip()))
                        i += 1
                        continue
                if _CHECKBOX.search(body):
                    out.append(page.checklist_item(body))
                else:
                    out.append(f"<li>{_inline(body)}</li>")
                i += 1
            out.append("</ul>")
            continue

        # Ordered list.
        if _ORDERED.match(stripped):
            out.append("<ol>")
            while i < n:
                m = _ORDERED.match(lines[i].strip())
                if not m:
                    curs = lines[i].strip()
                    indented = lines[i].startswith("   ") or lines[i].startswith("\t")
                    if curs and indented and out[-1].endswith("</li>"):
                        out[-1] = out[-1][: -len("</li>")] + " " + _inline(curs) + "</li>"
                        i += 1
                        continue
                    break
                out.append(f"<li>{_inline(m.group(2))}</li>")
                i += 1
            out.append("</ol>")
            continue

        # Headings (h3+ inside a block; h1/h2 handled by the caller).
        if stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            out.append(f"<h{level}>{_inline(stripped.lstrip('#').strip())}</h{level}>")
            i += 1
            continue

        # Paragraph: join consecutive plain lines.
        para = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (
                not nxt
                or nxt.startswith(("- ", ">", "#", "|", "```"))
                or nxt == "---"
                or _ORDERED.match(nxt)
                or _SIGNOFF_LINE.match(nxt)
            ):
                break
            para.append(nxt)
            i += 1
        out.append(f"<p>{_inline(' '.join(para))}</p>")
    return out


def _split_signoff(block_lines: list[str]) -> tuple[list[str], bool]:
    """Remove the two printed sign-off lines from a scenario block.

    Returns (lines-without-signoff, had_signoff).
    """
    kept: list[str] = []
    had = False
    skip_next_aspect = False
    for line in block_lines:
        s = line.strip()
        if _SIGNOFF_LINE.match(s):
            had = True
            skip_next_aspect = True
            continue
        if skip_next_aspect and _ASPECT_LINE.match(s):
            skip_next_aspect = False
            continue
        kept.append(line)
    return kept, had


def _convert(md_path: Path) -> tuple[str, _Page]:
    page = _Page(md_path.stem)
    lines = md_path.read_text(encoding="utf-8").splitlines()

    # Pull the h1 title.
    title = md_path.stem
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    page.title = re.sub(r"[`*]", "", title)

    # Split into preamble and h2 blocks, fence-aware.
    blocks: list[tuple[str | None, list[str]]] = []
    current_head: str | None = None
    current: list[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            blocks.append((current_head, current))
            current_head = line[3:].strip()
            current = []
            continue
        if not in_fence and line.startswith("# "):
            continue  # h1 handled separately
        current.append(line)
    blocks.append((current_head, current))

    body: list[str] = [f"<h1>{_inline(page.title)}</h1>"]
    for head, block in blocks:
        if head is None:
            body.extend(_render_lines(block, page))
            continue
        content, had_signoff = _split_signoff(block)
        is_footer = head.strip().lower() == "section sign-off"
        # Split out a trailing "### Section sign-off" footer inside this block.
        footer_idx = None
        for idx, bl in enumerate(content):
            if bl.strip().lower() == "### section sign-off":
                footer_idx = idx
                break
        footer_lines: list[str] = []
        if footer_idx is not None:
            footer_lines = content[footer_idx + 1 :]
            content = content[:footer_idx]

        sid_match = _SCENARIO_ID.match(head)
        head_html = _inline(head)
        if had_signoff:
            sid = sid_match.group(1) if sid_match else f"X-{_hash_key(head)}"
            inner = _render_lines(content, page)
            controls = page.scenario_controls(sid, re.sub(r"[`*]", "", head))
            badge = '<span class="st"></span>'
            body.append(
                f'<details class="sec scenario" open data-kind="scenario">'
                f"<summary><h2>{head_html}</h2>{badge}</summary>"
                f'<div class="secbody">{"".join(inner)}{controls}</div></details>'
            )
        else:
            has_boxes_before = page.checkbox_count
            inner = _render_lines(content, page, in_footer=is_footer)
            kind = "checklist" if page.checkbox_count > has_boxes_before else "plain"
            open_attr = " open"
            badge = '<span class="st"></span>'
            body.append(
                f'<details class="sec"{open_attr} data-kind="{kind}">'
                f"<summary><h2>{head_html}</h2>{badge}</summary>"
                f'<div class="secbody">{"".join(inner)}</div></details>'
            )
        if footer_lines:
            body.append('<section class="footerblock"><h3>Section sign-off</h3>')
            body.extend(_render_lines(footer_lines, page, in_footer=True))
            body.append("</section>")
    return "\n".join(body), page


_CSS = """
  body { font-family: system-ui, sans-serif; max-width: 62em; margin: 0 auto;
         padding: 1em; line-height: 1.5; }
  html { scroll-padding-top: 5em; }
  li { margin: 0.3em 0; }
  input.cb, input.aspect { width: 1.1em; height: 1.1em; margin-right: 0.3em; }
  .bar { position: sticky; top: 0; background: Canvas; padding: 0.5em 0;
         border-bottom: 1px solid GrayText; z-index: 2; }
  @media (prefers-color-scheme: dark) { body { background: #111; color: #eee; }
    .bar { background: #111; }
    input.notes, input.meta { background: #222; color: #eee; border: 1px solid #666; } }
  .bar button, .bar a { margin-right: 0.5em; }
  details.sec { border: 1px solid GrayText; border-radius: 6px;
                margin: 0.8em 0; padding: 0 0.8em; }
  details.sec > summary { cursor: pointer; padding: 0.4em 0; }
  details.sec > summary h2 { display: inline; font-size: 1.1em; margin: 0; }
  .st { margin-left: 0.6em; font-weight: bold; }
  .secbody { padding-bottom: 0.8em; }
  fieldset.scn { margin-top: 0.8em; border: 1px solid GrayText; border-radius: 6px; }
  fieldset.scn .row { margin: 0.35em 0; }
  fieldset.scn label { margin-right: 0.9em; }
  body.hidedone details.sec[data-done="1"] { display: none; }
  body.hidedone li.check[data-done="1"] { display: none; }
  blockquote { border-left: 3px solid GrayText; margin-left: 0; padding-left: 1em; }
  .tablewrap { overflow-x: auto; }
  table { border-collapse: collapse; }
  th, td { border: 1px solid GrayText; padding: 0.3em 0.6em; text-align: left; }
  .visually-hidden { position: absolute; width: 1px; height: 1px; margin: -1px;
    padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
"""

_TOOLBAR = """
<div class="bar" role="group" aria-label="Progress and controls">
  <span id="progress" role="status">Loading...</span><br>
  <button id="toggleHide" type="button" aria-pressed="false">Hide completed</button>
  <button id="expandAll" type="button">Expand all</button>
  <button id="collapseAll" type="button">Collapse all</button>
  <button id="export" type="button">Export progress...</button>
  <button id="import" type="button">Import progress...</button>
  <input type="file" id="importFile" accept=".json" hidden>
  <a href="index.html">All sections</a>
  <span id="live" class="visually-hidden" aria-live="polite"></span>
</div>
"""

_PAGE_JS = """
(function () {
  var PREFIX = "quill-acceptance:";
  var HIDE_KEY = PREFIX + "__hideCompleted__";
  var live = document.getElementById("live");
  var toggleBtn = document.getElementById("toggleHide");
  var cbs = Array.prototype.slice.call(document.querySelectorAll("input.cb"));
  var aspects = Array.prototype.slice.call(document.querySelectorAll("input.aspect"));
  var notes = Array.prototype.slice.call(
    document.querySelectorAll("input.notes, input.meta"));
  var scns = Array.prototype.slice.call(document.querySelectorAll("fieldset.scn"));
  var secs = Array.prototype.slice.call(document.querySelectorAll("details.sec"));

  function outcomeOf(scn) {
    var r = scn.querySelector('input.outcome:checked');
    return r ? r.value : "";
  }
  function setStatusBadge(scn) {
    var det = scn.closest("details.sec");
    if (!det) return;
    var st = det.querySelector(".st");
    var labels = { pass: "PASS", fail: "FAIL", blocked: "BLOCKED", na: "N/A", "": "" };
    if (st) st.textContent = labels[outcomeOf(scn)] || "";
  }
  function secDone(det) {
    var kind = det.getAttribute("data-kind");
    if (kind === "scenario") {
      var fs = det.querySelectorAll("fieldset.scn");
      for (var i = 0; i < fs.length; i++) {
        if (!outcomeOf(fs[i])) return false;
      }
      return fs.length > 0;
    }
    if (kind === "checklist") {
      var bs = det.querySelectorAll("input.cb");
      for (var j = 0; j < bs.length; j++) { if (!bs[j].checked) return false; }
      return bs.length > 0;
    }
    return false;
  }
  function itemDone(li) {
    var bs = li.querySelectorAll("input.cb");
    for (var i = 0; i < bs.length; i++) { if (!bs[i].checked) return false; }
    return bs.length > 0;
  }
  function hideActive() { return localStorage.getItem(HIDE_KEY) === "1"; }
  function markDone() {
    secs.forEach(function (d) {
      d.setAttribute("data-done", secDone(d) ? "1" : "0");
    });
    document.querySelectorAll("li.check").forEach(function (li) {
      li.setAttribute("data-done", itemDone(li) ? "1" : "0");
    });
  }
  function applyHide() {
    document.body.classList.toggle("hidedone", hideActive());
    if (toggleBtn) toggleBtn.setAttribute("aria-pressed", hideActive() ? "true" : "false");
  }
  function refresh() {
    var counts = { pass: 0, fail: 0, blocked: 0, na: 0 };
    var recorded = 0;
    scns.forEach(function (s) {
      var o = outcomeOf(s);
      if (o) { recorded++; counts[o]++; }
    });
    var done = 0;
    cbs.forEach(function (b) { if (b.checked) done++; });
    var bits = [];
    if (scns.length) {
      bits.push(recorded + " of " + scns.length + " scenarios recorded (" +
        counts.pass + " pass, " + counts.fail + " fail, " +
        counts.blocked + " blocked, " + counts.na + " n/a)");
    }
    if (cbs.length) { bits.push(done + " of " + cbs.length + " boxes checked"); }
    document.getElementById("progress").textContent =
      bits.length ? bits.join("; ") : "Nothing to sign off on this page.";
  }
  // Focus rescue: when hiding removes the element under focus, land on the
  // next visible section summary (else previous, else the toggle button).
  function rescueFocus(fromEl) {
    var det = fromEl && fromEl.closest ? fromEl.closest("details.sec") : null;
    if (det && getComputedStyle(det).display !== "none") return; // still visible
    var idx = det ? secs.indexOf(det) : -1;
    for (var j = idx + 1; j < secs.length; j++) {
      if (getComputedStyle(secs[j]).display !== "none") {
        secs[j].querySelector("summary").focus(); return;
      }
    }
    for (var k = idx - 1; k >= 0; k--) {
      if (getComputedStyle(secs[k]).display !== "none") {
        secs[k].querySelector("summary").focus(); return;
      }
    }
    if (toggleBtn) toggleBtn.focus();
  }

  // Restore + wire checkboxes (checklist and aspect boxes share persistence).
  cbs.concat(aspects).forEach(function (b) {
    var key = PREFIX + b.dataset.key;
    b.checked = localStorage.getItem(key) === "1";
    b.addEventListener("change", function () {
      if (b.checked) localStorage.setItem(key, "1");
      else localStorage.removeItem(key);
      markDone(); refresh();
      if (hideActive()) {
        var li = b.closest("li.check");
        var det = b.closest("details.sec");
        var hid = (li && li.getAttribute("data-done") === "1") ||
                  (det && det.getAttribute("data-done") === "1");
        if (hid) {
          if (live) live.textContent = "Completed and hidden.";
          rescueFocus(b);
        }
      }
    });
  });

  // Restore + wire outcome radios.
  scns.forEach(function (scn) {
    var base = PREFIX + scn.dataset.base + ":outcome";
    var saved = localStorage.getItem(base) || "";
    var radios = scn.querySelectorAll("input.outcome");
    radios.forEach(function (r) {
      r.checked = (r.value === saved);
      r.addEventListener("change", function () {
        if (!r.checked) return;
        if (r.value) localStorage.setItem(base, r.value);
        else localStorage.removeItem(base);
        setStatusBadge(scn); markDone(); refresh();
        var det = scn.closest("details.sec");
        if (hideActive() && det && det.getAttribute("data-done") === "1") {
          if (live) live.textContent =
            "Scenario recorded as " + (r.value || "not run") + " and hidden.";
          rescueFocus(scn);
        } else if (live) {
          live.textContent = "Recorded: " + (r.value || "not run") + ".";
        }
      });
    });
    if (!saved) {
      var nr = scn.querySelector('input.outcome[value=""]');
      if (nr) nr.checked = true;
    }
    setStatusBadge(scn);
  });

  // Restore + wire text fields (notes, section sign-off metadata).
  notes.forEach(function (t) {
    var key = PREFIX + t.dataset.key;
    var saved = localStorage.getItem(key);
    if (saved !== null) t.value = saved;
    var timer = null;
    t.addEventListener("input", function () {
      if (timer) clearTimeout(timer);
      timer = setTimeout(function () {
        if (t.value) localStorage.setItem(key, t.value);
        else localStorage.removeItem(key);
      }, 250);
    });
  });

  markDone(); refresh(); applyHide();

  if (toggleBtn) {
    if (scns.length === 0 && cbs.length === 0) {
      toggleBtn.hidden = true;
    } else {
      toggleBtn.addEventListener("click", function () {
        localStorage.setItem(HIDE_KEY, hideActive() ? "0" : "1");
        applyHide();
        var hidden = secs.filter(function (d) {
          return getComputedStyle(d).display === "none";
        }).length;
        if (live) live.textContent = hideActive()
          ? (hidden + " completed section" + (hidden === 1 ? "" : "s") + " hidden.")
          : "Showing all sections.";
      });
    }
  }
  var ex = document.getElementById("expandAll");
  var co = document.getElementById("collapseAll");
  if (ex) ex.addEventListener("click", function () {
    secs.forEach(function (d) { d.open = true; });
    if (live) live.textContent = "All sections expanded.";
  });
  if (co) co.addEventListener("click", function () {
    secs.forEach(function (d) { d.open = false; });
    if (live) live.textContent = "All sections collapsed.";
  });

  document.getElementById("export").addEventListener("click", function () {
    var state = {};
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k.indexOf(PREFIX) === 0) state[k] = localStorage.getItem(k);
    }
    var blob = new Blob([JSON.stringify(state, null, 1)],
                        { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "quill-acceptance-progress.json";
    a.click();
  });
  var fileInput = document.getElementById("importFile");
  document.getElementById("import").addEventListener("click", function () {
    fileInput.click();
  });
  fileInput.addEventListener("change", function () {
    var f = fileInput.files[0];
    if (!f) return;
    f.text().then(function (text) {
      var state = JSON.parse(text);
      Object.keys(state).forEach(function (k) {
        if (k.indexOf(PREFIX) === 0) localStorage.setItem(k, state[k]);
      });
      location.reload();
    });
  });
})();
"""

_INDEX_JS = """
(function () {
  var PREFIX = "quill-acceptance:";
  var HIDE_KEY = PREFIX + "__hideCompleted__";
  var live = document.getElementById("live");
  var toggleBtn = document.getElementById("toggleHide");
  var rows = Array.prototype.slice.call(document.querySelectorAll("li[data-slug]"));

  function pageProgress(slug) {
    var scn = 0, cb = 0;
    var scnPrefix = PREFIX + slug + ":scn:";
    var cbPrefix = PREFIX + slug + ":cb:";
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k.indexOf(scnPrefix) === 0 && k.slice(-8) === ":outcome") scn++;
      else if (k.indexOf(cbPrefix) === 0 && localStorage.getItem(k) === "1") cb++;
    }
    return { scn: scn, cb: cb };
  }
  function hideActive() { return localStorage.getItem(HIDE_KEY) === "1"; }
  function refresh() {
    var tScn = 0, tScnDone = 0, tCb = 0, tCbDone = 0, hidden = 0;
    rows.forEach(function (li) {
      var slug = li.dataset.slug;
      var scnTotal = parseInt(li.dataset.scn || "0", 10);
      var cbTotal = parseInt(li.dataset.cb || "0", 10);
      var p = pageProgress(slug);
      var bits = [];
      if (scnTotal) bits.push(Math.min(p.scn, scnTotal) + " of " + scnTotal + " scenarios");
      if (cbTotal) bits.push(Math.min(p.cb, cbTotal) + " of " + cbTotal + " boxes");
      var done = (scnTotal + cbTotal) > 0 &&
                 p.scn >= scnTotal && p.cb >= cbTotal;
      var span = li.querySelector(".prog");
      if (span) span.textContent = bits.length
        ? " - " + bits.join(", ") + (done ? " - COMPLETE" : "")
        : "";
      tScn += scnTotal; tScnDone += Math.min(p.scn, scnTotal);
      tCb += cbTotal; tCbDone += Math.min(p.cb, cbTotal);
      li.hidden = hideActive() && done;
      if (li.hidden) hidden++;
    });
    document.getElementById("progress").textContent =
      "Overall: " + tScnDone + " of " + tScn + " scenarios recorded, " +
      tCbDone + " of " + tCb + " checklist boxes checked.";
    if (toggleBtn) toggleBtn.setAttribute("aria-pressed", hideActive() ? "true" : "false");
    return hidden;
  }
  refresh();
  window.addEventListener("storage", refresh);
  window.addEventListener("focus", refresh);
  if (toggleBtn) toggleBtn.addEventListener("click", function () {
    localStorage.setItem(HIDE_KEY, hideActive() ? "0" : "1");
    var hidden = refresh();
    if (live) live.textContent = hideActive()
      ? (hidden + " completed section" + (hidden === 1 ? "" : "s") + " hidden.")
      : "Showing all sections.";
  });
  var ex = document.getElementById("expandAll");
  var co = document.getElementById("collapseAll");
  if (ex) ex.hidden = true;
  if (co) co.hidden = true;
  document.getElementById("export").addEventListener("click", function () {
    var state = {};
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k.indexOf(PREFIX) === 0) state[k] = localStorage.getItem(k);
    }
    var blob = new Blob([JSON.stringify(state, null, 1)],
                        { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "quill-acceptance-progress.json";
    a.click();
  });
  var fileInput = document.getElementById("importFile");
  document.getElementById("import").addEventListener("click", function () {
    fileInput.click();
  });
  fileInput.addEventListener("change", function () {
    var f = fileInput.files[0];
    if (!f) return;
    f.text().then(function (text) {
      var state = JSON.parse(text);
      Object.keys(state).forEach(function (k) {
        if (k.indexOf(PREFIX) === 0) localStorage.setItem(k, state[k]);
      });
      location.reload();
    });
  });
})();
"""

_PAGE_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} (interactive acceptance)</title>
<style>{css}</style>
</head>
<body>
{toolbar}
{body}
<script>{js}</script>
</body>
</html>
"""


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    pages: list[_Page] = []
    for md in sorted(ACCEPT_DIR.glob("*.md")):
        body, page = _convert(md)
        out = OUT_DIR / f"{md.stem}.html"
        out.write_text(
            _PAGE_TMPL.format(
                title=html.escape(page.title),
                css=_CSS,
                toolbar=_TOOLBAR,
                body=body,
                js=_PAGE_JS,
            ),
            encoding="utf-8",
            newline="\n",
        )
        pages.append(page)
        print(f"{out.name}: {page.scenario_count} scenarios, {page.checkbox_count} boxes")

    order = {slug: i for i, slug in enumerate(RUN_ORDER)}
    pages.sort(key=lambda p: (order.get(p.slug, len(RUN_ORDER)), p.slug))
    items: list[str] = []
    for p in pages:
        detail_bits = []
        if p.scenario_count:
            detail_bits.append(f"{p.scenario_count} scenarios")
        if p.checkbox_count:
            detail_bits.append(f"{p.checkbox_count} boxes")
        detail = f" ({', '.join(detail_bits)})" if detail_bits else " (read first; no boxes)"
        items.append(
            f'<li data-slug="{p.slug}" data-scn="{p.scenario_count}" data-cb="{p.checkbox_count}">'
            f'<a href="{p.slug}.html">{html.escape(p.title)}</a>{detail}'
            f'<span class="prog" role="status"></span></li>'
        )
    total_scn = sum(p.scenario_count for p in pages)
    total_cb = sum(p.checkbox_count for p in pages)
    index_body = (
        "<h1>QUILL 1.0.0 Acceptance Test Book - interactive runner</h1>"
        "<p>This is the run-order dashboard for the hand-held acceptance book. "
        "Open a section, follow each scenario step by step, and record the "
        "outcome with the Pass / Fail / Blocked / N-A controls. Everything you "
        "record is saved in this browser the moment you change it and restored "
        "when you come back - including after closing the browser. Use Export "
        "to back your progress up to a JSON file, and Import to restore it or "
        "move it to another machine.</p>"
        "<p>Hide completed hides every fully recorded section and scenario so "
        "you always see only what is left; Show all brings everything back. "
        "The printed Markdown book in the parent folder is the source of "
        "truth; these pages are generated from it by "
        "<code>scripts/gen_acceptance_html.py</code>.</p>"
        f"<p>Total: {total_scn} scenarios and {total_cb} checklist boxes "
        "across all sections, in the recommended run order:</p>"
        f"<ol>{''.join(items)}</ol>"
        '<p>Companion checklists: the <a href="../../../planning/signoff/'
        'interactive/index.html">machine-generated sign-off inventories</a> '
        "(every command, dialog, and app surface, one line each).</p>"
    )
    (OUT_DIR / "index.html").write_text(
        _PAGE_TMPL.format(
            title="QUILL acceptance index",
            css=_CSS,
            toolbar=_TOOLBAR,
            body=index_body,
            js=_INDEX_JS,
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(f"index.html: {len(pages)} sections, {total_scn} scenarios, {total_cb} boxes")

    # Machine-readable manifest for the README coverage table and any tooling.
    manifest = {p.slug: {"scenarios": p.scenario_count, "boxes": p.checkbox_count} for p in pages}
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
