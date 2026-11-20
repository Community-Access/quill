# AI choices and settings legibility audit, 2026-11 (partial)

Status: **paused, partial.** This covers part 1 of plan.md's "Make AI choices
and data flow legible" item: an inventory of AI entry points across the app
family. Nothing is fixed yet. Part 2 (settings whose effect is not obvious) has
not started.

The findings come from a read-only sweep of `main` at c3591ac2f on 2026-11-20.
**None has been checked by hand or covered by a test yet.** Each one needs to be
reproduced before anyone fixes it. File and line numbers are from that commit.

## How AI requests are routed

The family has two ways of deciding where an AI request goes.

- **Hosted AI.** Used by QUILL, QUILL Lite and every app's own AI menu
  (Weather, Converter, Player, Inkwell, Transcribe, Cast, Studio and
  WordPress). Every request goes through
  `ConnectionRouteMixin.request_connection` in
  `quill/ui/hosted_ai_connection_route.py`. That function reads the one stored
  choice, `ai_connection`, and does three things:
  - it refuses with a sentence when the chosen AI is not ready or cannot do the
    request (`connection_choice.py`, GATE-CAPS);
  - it asks "Send to a Different AI?", with No as the default, before a
    different company is used (`hosted_ai_route_guard.py`);
  - under Auto, it names the recipient before sending ("Auto chose X. Your
    request will go to Y."), and any retry is a Yes/No question.

  Which AI Am I Using and Choose Your AI describe this route accurately.
- **Advanced AI, QUILL only.** Used by spell check, grammar, translate,
  Document Q&A, thesaurus, metadata, rewrite, summarize, Describe Image and
  similar commands, plus agents, Ask Quill and Improve Reading Order. The route
  comes from `assistant_connection.json` and the legacy key, through
  `_ai_require_connection` (`main_frame.py` near 10536),
  `ProviderChatBackend()` or `make_default_backend()`. This route **never reads
  `ai_connection`**, and Which AI Am I Using does not describe it.

Most of the gaps below come from the second route, or from features that pick
a provider on their own.

## What the person can tell before using AI

The columns are what the person can tell before sending: (a) which provider
and model, (b) local or cloud, (c) what context is sent, (d) the limits,
(e) consent, (f) what happens on fallback. "Hosted" means the shared route
described above.

| Entry point | (a) provider and model | (b) local or cloud | (c) context sent | (d) limits | (e) consent | (f) fallback |
|---|---|---|---|---|---|---|
| Free AI Assistant, Ask About This Document, Chat, Prompt Library, Tidy Dictated Text (both editors) | Yes, through Ctrl+8, Choose Your AI and the status cell | Yes | The pad shows the size | Checks the free limit | Privacy Agreement, for the free AI only | Hosted |
| Ask About an Image (both editors) | **Wrong**: the text always says OpenAI and ChatGPT | Yes | The picture | Capability gate | **None** | Hosted |
| Do a Document Task, Propose Alt Text | Yes | Yes | Shown | Capability gate | Picture consent | Hosted |
| Ask Quill, Ask Quill by Voice | "Active provider, Model" | Yes | Shown | Shown | Share consent enforced | Asks "Use a Different AI Provider?" |
| Spell, grammar, translate, Q&A, thesaurus, metadata, rewrite, summarize, expand, table of contents (QUILL) | **No** | **No** | Partly; Summarize Selection also sends the whole document | No | **No share-consent check** | None; the command fails |
| Check Grammar with AI | Model only | No | Selection | No | No | None |
| Improve Reading Order | Names provider and host | Yes | Size shown | Page limit | Yes/No | **Sends through a cached assistant that may be another provider** (Gap 1) |
| Agents and Action Ring | No | No | Preview shows counts and redaction | No | Continue or Cancel | **Engine fallback is a status line only** (Gap 6) |
| AI Library, Transcript Actions | No | No | Not stated | No | No | None |
| Describe Image, AI alt text (QUILL) | No | No | The picture | No | **No picture consent** | None |
| Transcribe Audio File (QUILL) | Not named once a key exists; always OpenAI | No | The file | 25 MB, shown | No | None |
| Read Aloud, Export as Audio (cloud voices) | Provider and voice shown | Implied | Word count shown | Estimated cost shown | No | A missing setting defaults to OpenAI, announced |
| Picture Maker (WordPress, Studio) | Names company, model and endpoint | Yes | Shown | "Service charges may apply" | Yes/No | **Bypasses the chosen connection** (Gap 9) |
| WordPress: Suggest Alternative Text, Describe Image | "your chosen AI" | No | Announced | Capability gate | First-picture consent | Hosted |
| WordPress: In Short, Ask the Site, Ask About This Site | Named | Yes | Yes/No dialog; scope choice | 12,000-character cap, not stated | Yes/No | Hosted |
| WordPress: Visual Review, Suggest from Page Content | "your chosen AI" | No | Listed | — | Yes/No | Hosted |
| GitHub: Summarize Discussion, Explain Selected Change | **No** | **No** | Not stated | 24,000-character cap, not stated | Only the set-up offer | Legacy route (Gap 10) |
| GitHub: Assign to Copilot, Request Copilot Review | GitHub's own Copilot; QUILL sends no content | Cloud | — | — | Assign asks first; Review does not | — |
| Weather: Should I Go Out? | Ctrl+F8 | Yes | Forecast facts | — | Free AI only | Hosted |
| Converter: Will This Play | Ctrl+F8 | Yes | Probe text, never audio | — | Free AI only | Hosted |
| Player: Recap, Chapter Summary | Ctrl+F8 | Yes | A local 5-minute transcript | BARD content refused | Free AI only | Hosted, cached |
| Inkwell: Suggest Abbreviations | Ctrl+F8 | Yes | The document, said as "Reading file" | 12,000 characters, not stated | Free AI only | Hosted |
| Inkwell: Dictate Anywhere (cloud) | The tray says "Speech goes to OpenAI" | Yes | Speech | — | Recognizer consent | Local engine fallback, announced |
| Transcribe: Ask, Speakers, Sections, Summary | Ctrl+F8 | Yes | The transcript | — | Free AI only | Hosted |
| Transcribe: Transcribe a Recording (OpenAI model) | Yes | Yes | The recording | — | "Send this recording to OpenAI?" | Local fallback, announced |
| Review Dictation (Transcribe and the editors) | **Wrong under Auto** (Gap 11) | — | — | — | Consent names the wrong company | Hosted |
| Cast: AI verbs | Ctrl+F8 | Yes | — | — | — | Hosted; chapter cues stay local |
| Studio: Describe Folder, screenshots | Names provider, model and host | Yes | Yes | — | Yes/No | Hosted |
| Studio: Generate Captions (Offline) | **Can be cloud** (Gap 12) | **Says offline** | The whole audio file | — | **None** | Silent |
| Studio: chapter titles, Translated export | "your configured AI", "AI provider (cloud)" | Can be wrong | — | — | Generic | Legacy route |

## Suspected silent switches and gaps, not yet verified

The first ten are the ones where the person's data could go somewhere they did
not choose.

1. **Cached assistant keeps the old provider.** `_get_assistant` builds the
   assistant once (`main_frame.py` near 10026), and nothing resets it when the
   provider changes. After a switch from a cloud AI to Ollama, the old cloud
   provider keeps receiving requests until restart from:
   - Improve Reading Order, whose confirmation names the *new* provider;
   - watch-folder AI actions;
   - Train Writing Style;
   - chapter inference.
2. **`make_default_backend` ignores "Off".** At `assistant.py:184` there is no
   else branch, so the default provider is then used with no note. The watch
   folder only checks `load_ai_enabled`, so file text could reach a cloud
   provider after the person chose Off.
3. **Signing out of an Ollama own key moves requests to OpenAI.** This is a
   local-to-cloud switch. `hosted_ai_own_key_route.py:76-83` sets
   `ai_own_key_provider = OPENAI`, and `ai_connection` stays `own_key`. If an
   OpenAI key or `OPENAI_API_KEY` exists, `route_chosen()` records that as the
   person's choice, so the route guard never asks. Meanwhile the announcement
   says "No AI is in use".
4. **Ask About an Image names the wrong company and asks no consent.**
   `hosted_ai_image.py:57-61` always says OpenAI and ChatGPT, whatever the
   connection is. `cmd_ai_image` never calls `ask_picture_consent`.
5. **Share consent is enforced only in Ask Quill.** `_ai_require_connection`,
   `ProviderChatBackend` users and Describe Image skip
   `provider_consent_granted`. A key saved through Use My Own AI Key never
   gets that consent, yet the advanced commands send to it.
6. **Agent engine fallback is status-only.** In
   `agent_responder_selection.py:36-46`, "X is not set up; using Native." Native
   is the assistant provider, which may be a different company. There is no
   Yes/No.
7. **Advanced features do not follow Choose Your AI.** This is the second route
   described above. It is a design question as well as a defect; see the
   decisions section below.
8. **Signing out of an own key leaves the legacy key mirror.**
   `clear_provider_api_key` removes only the per-provider key. Advanced
   commands keep sending to that provider after "Signed out".
9. **Picture Maker bypasses the chosen connection.**
   `picture_maker.py:130-143` falls through to the advanced provider. The
   consent box does name the company, but the description step goes to
   `settings.host` while the box shows `DEFAULT_HOSTS`.
10. **GitHub Summarize Discussion and Explain Selected Change** use
    `_ai_require_connection`, which is the legacy route: the provider is not
    named and there is no per-request consent.
    - Explain Selected Change also wraps its prompt inside the "Summarize this
      GitHub discussion" prompt (`github_pr_diff_dialog.py:286` into
      `thread_summary.py:73`).
    - Its help text promises consent that does not happen.

Further gaps:

11. **Review Dictation under Auto names the wrong recipient** in its consent
    question (`windows_dictation_review.py:98-112`). Under Auto it falls through
    to "OpenAI, with your own key".
12. **Studio Generate Captions (Offline) can upload audio.**
    `studio.py:1667-1685` `_speech_provider` returns a cloud Quillin
    transcriber when one is chosen in Speech Hub. There is no
    `requires_network` check and no consent. QUILL has the same pattern at
    `main_frame_speech.py:42-54`.
13. **A legacy key can be sent to the wrong company.**
    `provider_backend.py:48` uses
    `load_provider_api_key(provider) or load_assistant_api_key()`, and the
    legacy store can hold another provider's key.
14. **A new app's first choice is made silently.** `migrate_choice` stores an
    own-key route, and the direct route then skips the privacy agreement. This
    is arguably by design.
15. **Low severity.**
    - `make_default_backend` runs on a worker thread while mutating module
      state that is documented as UI-thread only.
    - `resolve_dictation_provider` calls `_speech_provider(registry=...)`,
      which takes no arguments. That is a probable TypeError, but not a privacy
      issue.
    - The WordPress Ask the Site help says QUILL asks before an ability's
      result is sent back, and it does not.
    - Several WordPress commands say "your chosen AI" where `ai_name()` is
      available.

Already guarded, no change needed:

- `fallback.plan_fallback` and `plan_substitution` only build offers.
- The Ask Quill substitution hold (`backend_substitution`).
- The hosted route guard and Auto's announcement and retry question.
- Strict cloud-voice and diarization dispatch.
- Player recap, Cast chapter cues and Studio chapter-title transcription stay
  local.
- Voice-reply fallbacks are announced.
- Windows dictation asks before sending to OpenAI.

## Decisions for Jeff

- **Should the advanced route follow Choose Your AI?** If it should, gaps 1, 2,
  5, 7, 8, 9 and 10 mostly fall away. If it stays separate on purpose, Which AI
  Am I Using should describe both routes, and each advanced command should name
  its provider before sending.
- **Gap 14.** Should a new app's first AI request ask, rather than inherit the
  family's own key silently?

## Fixed

Nothing yet. The audit was paused before any fix.

## Part 2: settings legibility

Not started.
