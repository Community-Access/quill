"""Build an accessible in-browser read-aloud page (Web Speech API).

QUILL's embedded WebView2 only exposes the local SAPI voices; a *real* browser
exposes its full voice set — including Edge's "Online (Natural)" voices — to
``speechSynthesis``. So to let the user read a document with those better voices
we generate a small, self-contained, accessible HTML page carrying the document
text plus a voice picker and Play / Pause / Stop controls, and open it in the
user's browser (reusing QUILL's existing browser-preview open path). The browser
does the speaking and no audio file is produced.

Privacy note: QUILL itself makes no network call — but the whole point of this
page is to reach voices the embedded engine cannot, and Edge's "Online (Natural)"
voices synthesize *in Microsoft's cloud*. When the user picks an online voice the
browser sends the selected text to that service. On-device voices (labelled "(on
this device)") stay local. This is why the feature is opt-in under Experimental,
why the settings copy says availability varies with network, and why the network
egress audit and docs/legal/PRIVACY.md carry an entry for it.

This module is pure and wx-free (unit-tested): :func:`build_reader_html` returns
the page as a string. The caller writes it out and opens it.
"""

from __future__ import annotations

import contextlib
import html
import json
from pathlib import Path

_STYLE = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 1rem/1.6 system-ui, Segoe UI, Arial, sans-serif; margin: 0;
  padding: 1rem clamp(1rem, 5vw, 4rem); }
h1 { font-size: 1.4rem; margin: 0 0 .75rem; }
.toolbar { position: sticky; top: 0; padding: .75rem 0; margin-bottom: 1rem;
  border-bottom: 1px solid; display: flex; flex-wrap: wrap; gap: .75rem 1rem;
  align-items: end; background: Canvas; }
.field { display: flex; flex-direction: column; gap: .25rem; }
.field label { font-size: .85rem; }
.field label.check { display: flex; flex-direction: row; align-items: center;
  gap: .35rem; font-size: .9rem; }
select, button, input[type=range] { font: inherit; padding: .4rem .6rem; }
button { cursor: pointer; min-width: 6rem; }
button:disabled { cursor: default; opacity: .55; }
.status { margin: 0 0 1rem; font-weight: 600; }
article { white-space: pre-wrap; word-wrap: break-word; max-width: 70ch; }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }
""".strip()


def remove_reader_pages(reader_dir: Path) -> None:
    """Delete the generated read-aloud page(s) from *reader_dir*.

    The reader page carries the full document text as plaintext; the caller
    removes it on exit so a confidential document read once does not linger in
    app-data. Best-effort and non-raising: a locked or absent file is skipped so
    this can be called from a shutdown path without ever blocking exit.
    """
    if not reader_dir.exists():
        return
    for pattern in ("*.html", "*.tmp"):
        for candidate in reader_dir.glob(pattern):
            with contextlib.suppress(OSError):
                candidate.unlink()


def build_reader_html(title: str, text: str, *, lang: str = "en", chunk_chars: int = 240) -> str:
    """Return a self-contained accessible read-aloud page for ``text``.

    The page enumerates the browser's voices (labelling online vs on-device),
    remembers the chosen voice and rate in ``localStorage``, chunks the text into
    sentence-sized utterances (smooth playback, prompt Stop, and it dodges the
    Chromium long-utterance cutoff), and exposes keyboard-operable Play/Pause
    (one toggle) and Stop, with an ``aria-live`` status. Nothing auto-plays —
    browsers require a gesture — so Play is focused on load.

    ``lang`` is the user's language tag (e.g. ``"en"``, ``"fr-CA"``); only its
    base subtag is used, and the voice picker is filtered to matching voices so
    the user is not scrolling past dozens of foreign voices. A "Show all
    languages" checkbox reveals the full set, and if no voice matches the page
    falls back to showing everything.
    """
    safe_title = html.escape(title or "Document")
    body_text = html.escape(text or "")
    data = json.dumps(text or "")  # embedded as a JS string literal
    base_lang = (lang or "").replace("_", "-").split("-", 1)[0].strip().lower()
    lang_data = json.dumps(base_lang)  # "" means no filtering
    # The page chrome (title, controls) is English; the document text carries the
    # document's own language so a screen reader pronounces it correctly. When we
    # have no document language, fall back to English on the article too.
    doc_lang = html.escape(base_lang or "en", quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title} — Read Aloud</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>{safe_title}</h1>
<div class="toolbar" role="group" aria-label="Read aloud controls">
  <div class="field">
    <label for="voice">Voice</label>
    <select id="voice" aria-describedby="voicehint"></select>
  </div>
  <div class="field">
    <label for="rate">Speed</label>
    <input id="rate" type="range" min="0.5" max="2" step="0.1" value="1"
      aria-valuetext="Normal speed">
  </div>
  <div class="field">
    <label for="alllangs">Voices</label>
    <label class="check"><input id="alllangs" type="checkbox"> Show all languages</label>
  </div>
  <button id="play" type="button">Play</button>
  <button id="stop" type="button" disabled>Stop</button>
</div>
<p id="voicehint" class="status" hidden>The best online voices may take a moment
  to appear and need a network connection.</p>
<p id="status" class="status" role="status" aria-live="polite">Press Play to start
  reading. Escape stops.</p>
<article id="doc" lang="{doc_lang}" aria-label="Document text">{body_text}</article>
<script>
(function(){{
  var synth = window.speechSynthesis;
  var TEXT = {data};
  var MAX = {chunk_chars};
  var LANG = {lang_data};
  var voiceSel = document.getElementById('voice');
  var rate = document.getElementById('rate');
  var allLangs = document.getElementById('alllangs');
  var play = document.getElementById('play');
  var stop = document.getElementById('stop');
  var status = document.getElementById('status');
  var state = 'idle';
  // Chunk-by-chunk playback state: chunks are spoken one at a time (advancing on
  // onend), not all queued up front. This keeps memory small and the browser's
  // speech queue reliable for book-length documents, and lets Pause report the
  // position and keep the reader's place (resume-from-position). idx is the next
  // chunk to speak.
  var chunks = [];
  var idx = 0;
  if(!synth){{ status.textContent = 'This browser has no speech support.'; return; }}
  if(!LANG) allLangs.checked = true;
  if(localStorage.getItem('quillReaderAllLangs')==='1') allLangs.checked = true;
  function say(msg){{ status.textContent = msg; }}
  function voices(){{ return (synth.getVoices()||[]); }}
  function langMatches(v){{
    var vl = (v.lang||'').toLowerCase().replace('_','-');
    return vl===LANG || vl.indexOf(LANG+'-')===0;
  }}
  // Edge's "Multilingual" online voices routinely abort speechSynthesis with a
  // synthesis-failed error, so they are excluded from the picker entirely.
  function usable(v){{ return !/multilingual/i.test(v.name||''); }}
  function fillVoices(){{
    var vs = voices().filter(usable);
    var saved = localStorage.getItem('quillReaderVoice');
    var cur = voiceSel.value;
    var show = vs;
    if(LANG && !allLangs.checked){{
      var filtered = vs.filter(langMatches);
      if(filtered.length) show = filtered;  // fall back to all if none match
    }}
    voiceSel.innerHTML = '';
    for(var i=0;i<show.length;i++){{
      var o = document.createElement('option');
      o.value = show[i].voiceURI;
      o.textContent = show[i].name + (show[i].lang ? ' — '+show[i].lang : '') +
        (show[i].localService ? ' (on this device)' : ' (online)');
      voiceSel.appendChild(o);
    }}
    if(saved && [].some.call(voiceSel.options,function(o){{return o.value===saved;}})){{
      voiceSel.value = saved;
    }} else if(cur && [].some.call(voiceSel.options,function(o){{return o.value===cur;}})){{
      voiceSel.value = cur;
    }}
  }}
  allLangs.addEventListener('change', function(){{
    localStorage.setItem('quillReaderAllLangs', allLangs.checked ? '1' : '0');
    fillVoices();
  }});
  synth.onvoiceschanged = fillVoices; fillVoices();
  var savedRate = parseFloat(localStorage.getItem('quillReaderRate'));
  if(savedRate>=0.5 && savedRate<=2){{ rate.value = savedRate; }}
  // Reflect the restored rate in the accessible value text immediately, rather
  // than leaving the initial "Normal speed" until the slider is first moved.
  rate.setAttribute('aria-valuetext', (parseFloat(rate.value)||1).toFixed(1)+' times speed');
  function findVoice(uri){{ var vs=voices(); for(var i=0;i<vs.length;i++){{
    if(vs[i].voiceURI===uri) return vs[i]; }} return null; }}
  function chunk(t){{ var parts=t.split(/(?<=[.!?\\u2026])\\s+/), out=[], cur='';
    for(var i=0;i<parts.length;i++){{ var p=parts[i]; if(!p) continue;
      if((cur+' '+p).length>MAX && cur){{ out.push(cur); cur=p; }}
      else {{ cur = cur ? cur+' '+p : p; }}
      while(cur.length>MAX){{ out.push(cur.slice(0,MAX)); cur=cur.slice(MAX); }} }}
    if(cur) out.push(cur); return out; }}
  function setState(s){{ state=s;
    play.textContent = (s==='playing') ? 'Pause' : (s==='paused' ? 'Resume' : 'Play');
    stop.disabled = (s==='idle'); }}
  function speakNext(){{
    if(idx >= chunks.length){{ setState('idle'); idx=0; say('Finished.'); return; }}
    var v = findVoice(voiceSel.value);
    var u = new SpeechSynthesisUtterance(chunks[idx]);
    if(v) u.voice = v; u.rate = parseFloat(rate.value)||1;
    u.onend = function(){{
      // Only advance while actively playing, so a pause between chunks does not
      // race ahead. idx points at the *next* chunk, so it is the resume point.
      if(state !== 'playing') return;
      idx++;
      speakNext();
    }};
    u.onerror = function(e){{
      // Stop/cancel surface as 'interrupted'/'canceled' on the active utterance;
      // that is expected teardown, not a fault to announce (announcing it would
      // spam the live region after Stop). Any other error: skip this chunk so
      // playback can still continue.
      var err = (e && e.error) || 'unknown';
      if(err === 'interrupted' || err === 'canceled'){{ return; }}
      say('Speech error: ' + err);
      if(state === 'playing'){{ idx++; speakNext(); }}
    }};
    synth.speak(u);
  }}
  function start(){{
    synth.cancel();
    var text=(TEXT||'').trim();
    if(!text){{ say('Nothing to read.'); return; }}
    chunks = chunk(text);
    if(idx >= chunks.length) idx = 0;
    localStorage.setItem('quillReaderVoice', voiceSel.value);
    localStorage.setItem('quillReaderRate', rate.value);
    setState('playing');
    say(idx > 0
      ? ('Resuming at section ' + (idx+1) + ' of ' + chunks.length + '.')
      : 'Reading.');
    speakNext();
  }}
  play.addEventListener('click', function(){{
    if(state==='playing'){{
      // Pause keeps the place and reports it, so the reader knows where they are.
      synth.pause(); setState('paused');
      say('Paused at section ' + (idx+1) + ' of ' + chunks.length + '.');
    }}
    else if(state==='paused'){{ synth.resume(); setState('playing'); say('Reading.'); }}
    else {{ start(); }}
  }});
  stop.addEventListener('click', function(){{
    // Stop is a full reset (back to the top); Pause is the place-keeping control.
    synth.cancel(); idx=0; setState('idle'); say('Stopped.'); }});
  rate.addEventListener('input', function(){{
    rate.setAttribute('aria-valuetext', (parseFloat(rate.value)||1).toFixed(1)+' times speed'); }});
  document.addEventListener('keydown', function(e){{
    if(e.key==='Escape'){{ synth.cancel(); setState('idle'); say('Stopped.'); }} }});
  window.addEventListener('pagehide', function(){{ synth.cancel(); }});
  play.focus();
}})();
</script>
</body>
</html>
"""
