# AI features: general questions, own-key limits, and Leasey parity

Written 2026-09-26. A working note, not committed (the root layout gate does not
sanction extra root files).

## 1. What shipped in PR #1567 (`feat/ai-ask-anything`)

### General questions, the sixth free feature

- "Ask a general question" in the AI pad (both editors, shared pad). Only the
  question is sent: nothing from the document, no history, no reasoning.
- Gateway feature id `ask`, in `SHIPPED_FEATURES` (`quill-ai-gateway/app/prompts.py`).
- Its own answer ceiling, `max_ask_output_tokens`: seed 1,000 tokens (about 750
  words), fail-safe 500. Admin-tunable and cost-relevant on the Limits page.
- `feature_cap.ask` = 60 of the 100 monthly requests.
- Per-person cost fence `monthly_cost_cap_usd` seeded at $0.10 (was $0.08):
  60 general questions at the full answer plus 40 other requests reach about
  $0.07 at the 3,000-token passage limit.
- Cost projections now price every request at the longer answer ceiling.
- Migration `007_general_questions.sql` for the running deployment: flag on,
  the two new rows, the $0.10 fence, and a reworded chat flag reason.
- **Deploy needed:** apply migration 007 and redeploy the gateway. Until then
  the pad reports the feature unavailable and nothing is charged.

### Own OpenAI key: no limits, warnings instead

- No size ceiling, no answer ceiling (`max_tokens=None`, the model's own
  maximum), no excerpt picking: a question about the document sends the whole
  document.
- The pad's "About to send" line warns instead of refusing: word count,
  estimated cost with the chosen model (an estimate, not OpenAI's bill), that the
  answer is extra, that the text is more than the free service would accept
  (when true), and that it may exceed the model's context (over about 100,000
  tokens; OpenAI then refuses and charges nothing).
- Code: `quill/core/ai/own_key.py` (`size_warning`, `UNLIMITED`),
  `quill/ui/hosted_ai_pad.py`, `quill/ui/hosted_ai_service.py` (`free_limits`),
  `quill/core/assistant_ai.py` (`build_chat_body(max_tokens=None)`).

### Release placement

- QUILL Lite changelog lists both under **1.2.0 -- unreleased**. The built
  1.1.0 installer and portable zip do not include them.

## 2. Leasey 11.5 text AI versus QUILL Lite

Sources: `S:\code\LEASEY 11.5 Extracted\` (docs 01-16, extract strings) and
`S:\leasey\` (help). Capabilities only; nothing copied.

How Leasey delivers AI: the JAWS layer goes through Hartgen's PHP proxy
(server picks the model, keeps conversation history server-side); the Python
apps call OpenAI's Responses API directly with a key Hartgen provisions. Models
seen: gpt-5.2 for text, gpt-5.5 for JSON extraction, gpt-4o-mini for older
explain tools, Claude Sonnet 4.6 for podcast summaries. Almost no caps.

| Leasey capability | QUILL Lite | Full QUILL |
|---|---|---|
| Chat Key: ask from any app | Missing | Missing (typing plumbing exists in `text_injector.py`) |
| Multi-turn chat, context toggle | Missing (chat deferred) | Has (`chat_session.py`, compaction) |
| Named saved conversations | Missing | Has (`sessions.py`) |
| Answer delivery: speak, type into focused app, viewer, append clipboard, open in app | Partial (Replace, Insert Below, Copy) | Partial (spoken replies, export) |
| Saved prompt library | Missing | Has (`prompt_library_dialog.py`) |
| About 20 text tools (tone, simplify, key points, action items, email, meeting summary, social post, paraphrase, FAQs, speech, feedback, dictionary, thesaurus) | Partial (summarize, rewrite, proofread, explain) | Partial to has |
| One-off general question | Has (PR #1567) | Has |
| Ask about documents, spreadsheets, slides (file search, code interpreter) | Partial (3 excerpts, open document only) | Has (`document_qa.py`) |
| Word-level review of AI changes | Missing | Has (`diff_review.py`) |
| Cleanup of badly extracted PDF text | Missing | Probably has |
| Web search | Missing | Partial (agent tool, provider inactive) |
| Model and provider switching | Partial (own-key model picker) | Has |
| Translate | Missing | Has (`translation.py`) |
| Structured extraction (JSON) | Not applicable | Similar |

Out of scope here: image generation, vision and alt text, transcription, TTS
voices, song recognition.

Priority gaps for QUILL Lite: chat (own key or free), saved conversations,
prompt library, more text tools, translate, answer delivery modes, word-level
review, web search, PDF cleanup, system-wide Chat Key. Saved conversations,
the prompt library, translate and word-level review already exist in QUILL and
can be shared (the "QUILL Lite may never be ahead of QUILL" rule runs the other
way here, so sharing is the natural route).

## 3. Cost of each addition

Prices: Luna 6, $0.10 per million tokens in, $0.50 out. Limits: 3,000 tokens
in, 100 requests per person per month.

| Addition | Worst cost per request | Budget effect |
|---|---|---|
| More text tools (tone, simplify, email, and so on) | $0.00055 | None: same shape as Rewrite, inside the allowance |
| Dictionary, thesaurus | under $0.0001 | None |
| Translate | about $0.0012 (1,500 in, 2,000 out) | Needs its own answer ceiling and feature cap (about 20 a month) |
| Chat with history | $0.0008 per turn (history kept inside the 3,000 limit) | Per request unchanged; each turn is one request, so allowances drain faster and utilization rises |
| Web search | about 1 cent per search plus retrieved text (estimate; verify OpenAI's current price) | About 12 times a question; needs its own small cap (about 10 a month) and a higher per-person fence |
| Other files, code interpreter, PDF cleanup (up to 30,000 in and out) | $0.02 and up | Own key only |
| Chat Key anywhere, type into focused app, speak, append to clipboard, word diff, saved prompts, saved conversations | $0 | Runs on the computer |

At 1,000 people:

- Everything except web search: about $80 a month at full use, about $24 at
  typical (30%) use.
- With web search capped at 10 a month: about $180 at full use, about $54 at
  typical use.
- The global cap is $40 today; reaching it pauses the free AI for everyone.
- Actual usage is reported to be well below projections, so these scale down
  in proportion to real active users.

## 4. Gating: what exists and what is missing

Already server-controlled, no client release needed:

- Per-feature on/off flag with a reason people see (console Feature flags page).
- Per-feature monthly cap (`feature_cap.<feature>`).
- Per-person cost fence and the global budget cap with auto-pause.
- Per-feature answer ceiling pattern (now used by `ask`).

Missing: the pad's list of choices is compiled into the app, so a new text
tool still needs a client release.

Recommendation: have `/v1/config` send a feature catalogue (id, label, help
sentence, input kind: selection, question, or passage plus language). Templates
stay server-side, as now. The client renders the catalogue with a built-in
fallback. After that, a new text tool is a server deploy plus a flag flip, and
features can be widened slowly and switched off again the same way.

## 5. Open questions

1. How many active devices, and how much spending, does last month show in the
   console? That decides whether the $40 cap changes.
2. Order: text tools and translate first (cheap), then chat (drains
   allowances), then web search (real money)?
3. Chat on the free service, or own key only?
4. Build the server-sent feature catalogue first?
5. Fold PR #1567 into QUILL Lite 1.1.0 and rebuild the installers, or ship it
   as 1.2.0?
