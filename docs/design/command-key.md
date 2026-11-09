# Say or Type a Command: one key for every QUILL family app

Plan of record, third revision, 2026-11-08; kept here since 2026-11-08 (it was `S:\wt\jev-natural-language-control-spec.md`, and the 2026-11-07 draft is still beside that file). Code cites it by section as `command-key.md <section>`, and those citations resolve in this file. Section 20.1 records the decisions, section 21 is the remaining work, and section 22 is the progress log.

## 1. The short version

- **One Command Key in every app: F11.** Tap it to type what you want, or hold it and say it. It works the same in QUILL, QUILL Lite, Radio, Cast, Studio, Weather, Inkwell, Converter, Player, Beacon and Transcribe.
- **Commanding and dictating never share a key or a phrase.**
  - F11 is commands only. It never starts, stops or pauses dictation, in any app.
  - Dictation keeps its own keys: Ctrl+F11 in the editors, Dictate Here in Radio and Cast, and Transcribe's system-wide Alt+Shift+\ with its other dictation keys.
  - Spoken, "Quill dictate" writes, and a separate command phrase ("Hey Quill" is proposed) acts.
- **A system-wide Command Key, separate from dictation's.** It ships with speech. As with every system-wide key in the family, it is registered only once the person picks it. The picker suggests Ctrl+Alt+PageDown, which clashes with no family key, dictation's included. From anywhere, a command goes to the family app in front, or to the app you name ("Radio, pause"). Anything else is declined in one sentence.
- **It only listens for what it can do.** Every request is matched against one list: the commands this window has, that are switched on and can run right now. Nothing outside that list can be chosen, by any matcher or any engine. Anything else gets a plain "I can't do that here", with a pointer to where it can be done when that is known.
- **One family command catalogue.** Every app publishes its commands once: a name, aliases, example phrases, a description, arguments, when it can run, and whether it is safe to do without asking. The Command Palette, the Command Key, Key Describer, F1, "What can I say here", voice, Jev and the AI agents all read it. Nothing is listed twice.
- **Matching, cheapest first; then Jev as the core assist.**
  - Exact and fuzzy matching go first, because they are free and instant.
  - Anything they can't settle with confidence goes to **Jev**, TypeSafe's decision model. It picks the command, fills in the arguments, checks whether the request fits anything on the list at all, and turns a split decision into one short question.
  - When Jev isn't available (offline, credit spent, or the person turned cloud help off), the AI chosen in Choose Your AI is the fallback. That includes local Ollama, which works offline. When none of those is available, the offline answer stands.
- **Rich ways to command.** Arguments (numbers, durations, times, dates, names, stations, files), relative commands ("louder", "do that again", "undo that"), questions answered from the app ("what's playing"), short multi-step requests ("open my last document and read it aloud"), corrections ("no, the other one") and requests to another app ("Radio, pause"). Section 8 gives example phrases and the Jev question for each.
- **"What can I say here?"** typed or spoken, or from What Can I Say Here in every Help menu, lists only what this window can do right now. It is read in short pages, can be browsed and filtered, and gives an example for each command. "What can I say while dictating" lists the dictation phrases separately.
- **Tested hard.** There is a corpus of tens of thousands of phrasings with their expected results, a scripted fake Jev and a fake Choose Your AI engine so every tier and threshold runs offline in CI, and property tests for the safety rules (never outside the list, never a NEVER-class command, CONFIRM always asks). A recorded live Jev suite runs nightly or by hand, never in PR CI. Coverage gates run over all of it. Section 14 sets the targets.
- **Order.** The first shippable release is typed, offline, free and needs no account: QUILL and QUILL Lite together (QUILL Lite is never ahead of QUILL), plus Radio. Jev comes in the next phase, then speech and the system-wide key.
- **Who pays.** Jev is pay-per-use. People using QUILL pay nothing, because requests go through the Community Access gateway, which holds the TypeSafe key. Jeff pays the bill, and a daily cap on the server sets the most it can ever cost. At the expected sizes that is cents a day (section 17).

## 2. What changed in this revision

### 2.1 Third pass, 2026-11-08 (Jev, rich commanding, testing)

- **Jev is now the core assist, not an optional extra.** It is the default engine for whatever exact and fuzzy matching can't settle: picking the command, filling arguments, the fit check that enforces "only what it can act on", and a short question when its confidence is split. Choose Your AI becomes the fallback. Section 7 designs the request within Jev's limits.
- **A rich catalogue of ways to command** (section 8): arguments, relative commands, questions about app state, multi-step requests, corrections and cross-app requests, each with examples and its Jev question.
- **A testing strategy that drives the phases** (section 14): the corpus, fakes, property tests, context-gating tests, a recorded live suite, coverage gates, announcement tests, and target numbers.
- **Jev moves from phase 7 to phase 3,** directly after the free offline release. The gateway route `/v1/decide`, the consent, the egress rows, the error codes, the caps and the out-of-credit behaviour are all specified.
- **Multi-step requests are now allowed,** up to three steps with a preview. The earlier "one thing at a time" rule is replaced (section 8.6).

### 2.2 Second pass, 2026-11-08 (separate keys, discoverability)

- **Commanding and dictating are fully separate,** in keys and in spoken phrases. F11 is commands only and never touches dictation. Section 9.2 audits every key in the family into one table, dictation on one side and commands on the other.
- **A system-wide Command Key arrives with speech.** Transcribe's existing Command Key becomes that route. The picker suggests Ctrl+Alt+PageDown, and section 9.5 says how that was checked.
- **Separate spoken phrases,** each with its own setting: "Quill dictate" writes, "Hey Quill" commands. There are targeting rules for a spoken command from anywhere.
- **One listening switch and one privacy notice** cover dictation and commands together.
- **Discoverability** (section 11): "What can I say here", the dictation equivalent, an `examples` field in every catalogue row, a What Can I Say Here row in every Help menu, "I can't do that here, but you can..." answers, and a generated reference.

### 2.3 First pass, 2026-11-08 (from an engine to a key and a catalogue)

- The plan is built around one key and one family command catalogue, with section 4 mapping the existing command and control code it unifies.
- Free and offline come first.
- Transcribe and the GitHub Workbench were added to the per-app scope.
- A phased attack layout replaced the prototype list.
- Kept from the 2026-11-07 draft: gent's lessons, the thresholds, the undo-or-opposite rule, the "what would you do" preview, the never-exposed lists, the privacy rules, the TypeSafe cost figures and the evaluation targets.

## 3. The idea

### 3.1 Ways in

- **Type it.** Tap F11. A one-line box opens, titled "Say or Type a Command". Type "a lot slower" or "play favourite 3" and press Enter.
- **Say it.** Hold F11, speak, then let go. What you said goes through exactly the same matching as typed text.
- **From anywhere in Windows.** The system-wide Command Key does the same, once you have picked one. So does the spoken command phrase, once it is turned on.
- **Ask what you can say.** "What can I say here?" through any of the above, or Help, What Can I Say Here.

### 3.2 Only what this window can do right now

The list a request is matched against is built fresh each time from four things:

- the app;
- the window or surface that has focus;
- the commands enabled there, using the same check the menu and palette use;
- the commands allowed to run from a sentence at all (their risk class, section 5.3).

"Next favourite" is not on the list when you have no favourites. "Make that bold" is not on it in a plain text document. No Radio command is on it while you are in Weather.

### 3.3 Commanding and dictating never mix

| | Dictation | Commands |
|---|---|---|
| Does | writes words where you are | runs one of this window's commands |
| Keys | its own (section 9.2) | F11, and the system-wide Command Key |
| Spoken phrase | "Quill dictate" to start, "stop dictation" to stop | "Hey Quill" (proposed) |
| Phrases while dictating | "scratch that", "caps on", "select the cat", after the "QUILL" command word or on their own | none; hold F11 instead |
| Help | "what can I say while dictating" | "what can I say here" |

While you are dictating, F11 still means a command. A tap opens the box. While you hold it, what you say is a command and is not written. Dictation stays on and goes back to writing when you let go. F11 never starts, stops or pauses dictation.

Today's F11, Speak a Command, made the next dictated phrase a *dictation* command. Under this plan it is simply a command. The dictation phrases are still reached through the "QUILL" command word, exactly as now (section 9.3).

## 4. What already exists

Every path in this section is in `S:\QUILL`.

### 4.1 The command registry and keymaps

- **The registry,** `quill/core/commands.py`:
  - `Command` (lines 14 to 19) holds `id`, `title`, `keybinding`, `handler` and `feature_id`. `CommandRegistry` starts at line 22.
  - `set_availability_probe` (line 194) and `unavailable_reason` (line 199) say why a command can't run. `run` (line 214) is the single dispatch path.
  - It has no aliases, descriptions, arguments, risk class or per-command enabled check.
- **Enabled state is coarse.**
  - `quill/ui/app_availability.py` (lines 21 to 57) and the editor's probe (`quill/ui/main_frame.py`, around lines 1266 to 1270) check only feature locks, Safe Mode and whether the feature is on.
  - Per-document dimming is written by hand: QUILL Lite in `lite_window_menus.py` (lines 335 to 358), Studio in `_on_studio_menu_open` (`studio.py`, line 1176), and Cast in one `EVT_UPDATE_UI` (`podcasts_menu.py`, line 280).
  - Cast has the richest probe, `_cast_command_unavailable_reason` (`podcasts_routes.py`, line 342).
- **The keymaps:**
  - `quill/core/keymap.py`: `DEFAULT_KEYMAP` (line 72) has about 570 ids, about 440 of them with a chord. The QUILL key leader is Ctrl+Shift+Grave.
  - `quill/core/app_keymaps.py`: `APP_KEYMAPS` has entries for studio, transcribe, radio, cast and weather. Converter, player, inkwell and beacon have AI rows only, through `app_keymaps_ai.py`.
  - `quill/core/lite/keymap.py` is QUILL Lite's.
  - `quill/core/data/family_menu_chords.json` lists every menu chord in the family.
  - `quill/core/family_chords.py` holds `SHOW_HIDE_DEFAULTS` (line 66), `default_system_wide_keys` (line 135) and `show_hide_key_problem` (line 368), which is the family key picker's own check.

### 4.2 The Command Palette

- **Ctrl+Shift+P** (`app.command_palette`, `keymap.py` line 155). `open_command_palette` is at `quill/ui/app_shell.py` line 822.
- **Ranking** is `rank_commands` (`quill/core/palette.py` line 65), with `COMMAND_ALIASES` (line 92) covering 22 commands and a usage memory (line 50). It is the best offline matcher in the tree.
- **Apps with no registry** use the menu-walking palette, `quill/ui/menu_palette.py` (`MenuRow`, line 28).
- **Beacon** has its own `Command` class and palette (`quill/apps/beacon/commands.py`, lines 20 to 31).

### 4.3 QUILL Lite's command table

- **The rows.** `COMMANDS` (`quill/core/lite/commands.py`, from line 77) is a list of `(menu, label, key, handler, kind)` rows, with more in the `commands_*.py` tables.
- **Areas.** `command_areas.py` decides which areas are shown (`visible_commands`, line 250).
- **The palette.** It builds a fresh registry on each call (`command_registry`, `quill/apps/lite_services.py`, line 186), so the list matches the document in front of you.
- **The join to QUILL.** `COMMAND_EQUIVALENTS` (`quill/core/lite/parity.py`, line 172) maps 186 QUILL Lite handlers to QUILL ids. It is the ready-made join for the catalogue.

### 4.4 Each app's commands

| App | Defined today | Ids | APP_KEYMAPS |
|---|---|---|---|
| Radio | `quill/ui/radio/palette_commands.py` lines 94 to 398, plus transport | `radio.*` | yes |
| Cast | `quill/ui/podcasts/palette_commands.py` lines 27 to 157 | `podcasts.*` | yes |
| Studio | `quill/apps/studio.py` lines 1220 to 1269, plus capture and demo | `studio.*` | yes |
| Weather | `quill/apps/weather_commands.py` lines 17 to 80 | `weather.*` | yes |
| Inkwell | menu labels in `inkwell.py`, `inkwell_keys.py` | none | AI rows only |
| Converter | `converter_menu.py` lines 43 to 158 | none | AI rows only |
| Player | `player_menus.py` lines 27 to 134 | AI rows only | AI rows only |
| Beacon | its own `Command` class | display names | AI rows only |
| Transcribe | `transcribe_menus.py` line 37; `quill/core/transcribe/parity.py` | partly | yes |
| GitHub (editors) | `main_frame_github.py` lines 63 to 77; `main_frame_github_admin.py` from line 557 | `github.*` | mostly keyless |

The GitHub Workbench branch, `feat/github-workbench-menu`, currently holds the Sign In with GitHub work rather than a new menu shape. Its commands are registered like any other, so the catalogue covers them without special handling.

### 4.5 Speech, dictation and voice

- **Push-to-talk voice commands** (`tools.voice_command`, no key).
  - `quill/core/speech/voice_commands.py` has an alias table (`_ALIASES`, line 39), a 0.6 threshold (line 71) and `match_command` (line 133). It works only over `SAFE_TOOL_IDS`.
  - Dispatch is in `main_frame_speech_voice.py` (lines 195 to 209) and never confirms.
  - `voice_routing.classify` (line 58) sorts what was said into cancel, question or command.
- **Dictation's command word and today's F11.**
  - The command word "QUILL" (`DEFAULT_COMMAND_PREFIX`, `quill/core/windows_dictation/command_mode.py` line 66) starts a dictation phrase, as in "QUILL scratch that".
  - Today's F11, Speak a Command (`quill/ui/windows_dictation_command_key.py`, `keymap.py` line 610), makes the next dictated phrase one of those phrases.
  - The dictation grammar is the 81-member `Command` enum (`vocabulary_types.py`, line 46).
  - Its "What can I say?" list is already generated from the table (`quill/core/windows_dictation/reference.py`).
- **The wake and stop phrases.** "Quill dictate" and "stop dictation" in English, "Quill dicta" and "deja de dictar" in Spanish (`quill/core/windows_dictation/wake.py`).
- **Transcribe's system-wide keys** (`quill/apps/transcribe_keys.py`).
  - Start and stop defaults to Alt+Shift+\ (`quill/core/transcribe/settings.py`, line 56).
  - The Command Key, Status, Resume and Discard keys are all empty until the person chooses them. The Command Key is set from File, Command Key... (Ctrl+Alt+Shift+K).
  - Holding a registered key is followed by asking Windows whether it is still down (`quill/platform/windows/key_state.py`, `HoldToTalk` in `quill/core/windows_dictation/hold.py` line 53).
  - `KeyHeldGate` (`quill/core/transcribe/talk.py`) holds words while a modifier key is down.
- **The Player's typed voice commands.** `parse_voice_command` (`quill/core/media/voice.py`, line 118) produces `VoiceIntent(action, value)`. It is the only matcher in the tree with arguments.
- **Dictate Here** in Radio and Cast (`quill/ui/dictate_here_ui.py`, Ctrl+F11) asks Transcribe to type into the focused field. It goes through the family microphone (`MicrophoneLock`, `quill/core/dictation_owner.py` line 183) and a request file (`send_request` and `take_requests`, lines 352 and 366). That request file is also the route for a command to reach another app.
- **The wake word.** `quill/core/speech/wakeword.py` (`WakeController`) and Ask's voice mode (Alt+Shift+Q).

### 4.6 The AI agents and Ask

- **The safe list.** `SAFE_TOOL_IDS` (`quill/core/ai/agent.py`, lines 17 to 42) holds 24 editor ids.
  - `family_tools.py` (line 446) turns it into a closed `enum` for agents.
  - `permissions.py` (lines 238 to 249) refuses any other id.
  - `approvals.py` asks before every write.
- **Ask can already choose a command.** `Assistant.decide` (`assistant.py`, line 539) chooses from the allowed ids, then asks "Run ...?". Only the llama.cpp backend (`llama_cpp_backend.py`, lines 168 to 215) and Apple's on-device model implement it.
- **Choose Your AI.**
  - `AiService.ask` (`quill/ui/hosted_ai_service.py`, lines 205 to 283) reaches the free hosted AI, ChatGPT, Copilot, Codex or an own key, with local Ollama as an own-key provider.
  - The gateway accepts only fixed server templates (`own_key.py`, line 109), and no route has JSON mode.
- **The gateway,** `quill/core/ai/gateway_client.py` (`https://ai.community-access.org`):
  - routes `/v1/chat`, `/v1/config` and `/v1/quota`, plus device tokens;
  - caps of 1,500 input and 500 output tokens a request;
  - daily and monthly quotas.
- **"What can I do here?"** (`family_prompt_catalogue.py`, line 218) is answered on the computer from F1 and the menu chords. QUILL has it as Help, What Can I Do Here? on Ctrl+Alt+Shift+F1 (`help.what_can_i_do_here`, `keymap.py` line 464).

### 4.7 Names, help and dates

- **Key Describer titles:** `_CHORD_COMMAND_TITLES` (`quill/core/quill_key_help.py`, line 245), about 140 rows.
- **Menu labels:** `_menu_label` (`main_frame.py` line 4161, `app_shell.py` line 306).
- **F1:** each app's `surface_help` catalogue, keyed by window title, through `quill/core/control_help.py`. These are the catalogue's surface names.
- **Quillin smart triggers** (`quill/core/quillins/smart_triggers.py`) and Inkwell's abbreviations are exact typed triggers. They stay as they are.
- **Dates:** `quill/core/date_parse.py` already reads dates, so the argument reader uses it.

### 4.8 What is missing

- One place that holds a command's description, aliases, examples, arguments and risk.
- A per-command "can it run here, now" answer for every app.
- One resolver and one confirmation policy. Voice never confirms today, and Ask always does.
- Command ids in Inkwell, Converter, Player, Beacon and Transcribe.
- A way to send a candidate list to any engine and get one checked id back.

## 5. One family command catalogue

### 5.1 The decision

The catalogue has two halves, joined by command id:

- **The static half** is new, wx-free and strict-typed: `quill/core/command_catalogue/`, one module per app. It records what a command is.
- **The runtime half** is the existing `CommandRegistry`. It records what a command can do right now. It gains one method, `set_command_probe(command_id, probe)`, where `probe(context)` returns "" or the reason the command can't run.

### 5.2 One row

```
CommandSpec(
    id="radio.volume_down",
    apps=("radio",),
    title="Volume Down",                       # spoken name; Key Describer title
    aliases=("quieter", "softer", "turn it down"),
    examples=("turn it down a bit", "much quieter", "it's too loud"),
    description="Make the radio quieter",      # what the person wants
    args=(Stepped(),),                         # see 5.4
    risk=Risk.SAFE,                            # SAFE, CONFIRM or NEVER
    kind=Kind.STEP,                            # ACTION, TOGGLE, OPENS_DIALOG, READOUT, STEP
    surfaces=("Quill Radio",),                 # F1 surface names; empty means app-wide
    group="Playback",                          # the menu it lives in, for help pages
    opposite="radio.volume_up",
    announces_itself=True,
    agent_ok=True,
)
```

A row shared by both editors is written once, under the QUILL id. QUILL Lite reaches it through `COMMAND_EQUIVALENTS`.

- **Aliases** are short keys the matcher scores against.
- **Examples** are whole sentences a person might say. They are shown in help, F1 and the generated docs, sent to Jev, and every one is a test (section 14.5).

### 5.3 Risk classes

| Class | From a sentence | Examples |
|---|---|---|
| SAFE | runs when the match is confident | play, louder, next heading, word count, open a dialog |
| CONFIRM | always asks first, at any confidence | close, stop recording, mark all played, convert, anything that spends hosted AI |
| NEVER | not offered; stays in the palette and on its key | sign-in, keys, sending, publishing, deleting, Safe Mode, updates, privacy settings |

### 5.4 Arguments

| Type | Examples | Read by |
|---|---|---|
| Stepped | "a bit", "a lot", "much" | Jev `size`; tier 1 words |
| Number | "favourite 3", "line 120", "the third one" | the local reader |
| Duration | "30 seconds", "an hour and a half", "20 minutes" | the local reader, lifted from `media/voice.py` |
| Time and date | "at 7", "tomorrow morning", "next Friday" | `quill/core/date_parse.py` |
| Choice (closed set) | "as MP3", "the Spanish voice", "tornado alerts" | local match, then Jev `choice` over app constants |
| Name (person's data) | "WNYC", "my podcast about history", "the heading Budget" | matched locally against the app's own list, never sent |
| File | "my last document", "the report from yesterday" | the recent-files list, matched locally |

### 5.5 Who reads the catalogue

| Reader | What it takes | What it replaces |
|---|---|---|
| Command Key | everything | new |
| Command Palette | title, aliases, examples, description | `COMMAND_ALIASES` |
| Key Describer | title | duplicated `_CHORD_COMMAND_TITLES` rows |
| Push-to-talk voice | aliases, risk | `voice_commands._ALIASES`; retired into F11 in phase 4 |
| AI agents, Ask's `decide` | `agent_ok` ids, descriptions | `SAFE_TOOL_IDS`, now a view of the catalogue |
| Player typed voice | aliases, arguments | the intent table in `media/voice.py` |
| "What can I say here", F1 | titles, examples, chords, groups | the menu-chord list in `what_can_i_do_here` |
| Jev and Choose Your AI | descriptions, examples, argument shapes | new |
| Generated docs | everything | new `docs/command-catalogue.md` |

The dictation grammar stays dictation's own table. It is a different job, and keeping it separate is what keeps commanding and dictating apart.

### 5.6 Seeding

A one-time script seeds the catalogue from:

- the registry titles;
- `_CHORD_COMMAND_TITLES`;
- `COMMAND_ALIASES` and `_ALIASES`;
- `SAFE_TOOL_IDS`;
- `COMMAND_FEATURE_MAP`;
- `COMMAND_EQUIVALENTS`;
- the per-app tables in section 13.

Every other row starts NEVER, marked "unreviewed", so nothing becomes reachable by sentence until a person has classified it.

## 6. Matching in tiers

### 6.1 The candidate list

Every tier is given the same list, built per request:

1. this app's catalogue rows;
2. narrowed to the focused surface, plus the app-wide rows;
3. narrowed again to the rows the registry and the command probe say can run now;
4. with NEVER rows dropped;
5. plus the shared rows: undo that, do that again, what can I say here, ask instead, another app, and none of these.

### 6.2 How "only what it can act on" is enforced, in every tier

- **Input.** An engine sees the candidate list and nothing else.
- **Fit.** Jev's yes or no `fits` question must pass as well as its `action` choice (section 7.3). An engine answering "none of these" means none.
- **Output.** An answer that is not a candidate id is discarded, logged as a defect (`QUILL-CORE-COMMAND-NOT-OFFERED`) and never run.
- **Run time.** The command is checked again just before it runs. If it became unavailable while the engine was working, it isn't run.
- **Path.** The run is always `registry.run(id)`, the same call the menu makes.
- **Words.** Everything the person hears is the app's own string. No engine's text is ever spoken.

### 6.3 The tiers in order

| Tier | What | Cost and network | Settles |
|---|---|---|---|
| 1 | Exact: titles, aliases, "press control s", numbered rows, shared rows | free, offline, under 5 ms | "louder", "next heading", "favourite 3" |
| 2 | Fuzzy: the palette ranker merged with the push-to-talk matcher, stemming, a synonym table, edit distance on words, the local argument reader | free, offline, under 50 ms | "turn it down", "go to line 120" |
| 3 | **Jev**: command, arguments, fit, splits, steps, corrections | gateway, capped, about 0.3 to 0.6 s | "it's way too loud in here", "open my last document and read it aloud" |
| 4 | **Choose Your AI**, the fallback when Jev is unavailable | the person's AI; local Ollama is free and offline | the same, less calibrated |

- A request leaves tier 2 for tier 3 only when tier 2 is not confident: the top score is below its act threshold, or doesn't beat the runner-up by a clear margin.
- Tier 4 is used only when Jev is unavailable: offline, the gateway's limit or credit is spent, a timeout, or the person said no to cloud help.
- When no engine can be reached, the offline answer stands: act if it was confident, "Did you mean" if it was close, otherwise "I can't do that here".

### 6.4 Thresholds

Starting values, tuned on the test set and pinned with the Jev model version:

| Risk | Act without asking | Ask | Say it can't |
|---|---|---|---|
| SAFE | tier 1 single hit; tier 2 confident with a margin; Jev confidence 0.7 or more, fits 0.7 or more, margin 0.2 or more | Jev's top two within 0.2 of each other, or confidence between 0.4 and 0.7 | fits below 0.3, or confidence below 0.4 |
| CONFIRM | never | always, as one line | as for SAFE |
| NEVER | not in the list | - | - |

- **Jev's confidence depends on the list.** It is `(p_max - 1/n) / (1 - 1/n)`, so the policy also reads the top probability directly and records n with every decision.
- **Tier 4 has no calibrated confidence.** Its answer acts without asking only when it is SAFE and agrees with tier 2's best guess. Otherwise it asks.
- **gent's rule stays.** A split between "undo that" and the opposite of the last change counts as agreement.

### 6.5 The spoken route

Speech only turns sound into text. The text then goes through the tiers above.

- **QUILL, QUILL Lite and Transcribe** use their own dictation controller and the person's chosen engine, for F11 held.
- **Every other app** uses Dictate Here into the command box. Transcribe types the words into the box, and the box submits them when F11 comes up.
- **Engines that accept a phrase list or a prompt** are given the candidate titles and examples while F11 is held. Whether that helps is measured.
- **A recogniser that returns several guesses** has its top three sent through tiers 1 and 2 (and, as one state field, to Jev), so a misheard word can still land.

## 7. Jev as the core assist

### 7.1 What Jev is asked

Jev answers typed questions about one `state`: choice, score (ordered levels), and noul (the probability that a yes or no statement is true). It has no number type, as of the 2026-11-07 docs. So numbers, durations and dates are read on the computer, and Jev only decides which slot they belong to and whether the request carries one. All questions in a request run in parallel against the same state, for almost no extra time.

### 7.2 The state

```
state = {
  "request": "<what was typed or heard, up to 300 characters>",
  "heard_alternatives": ["<second guess>", "<third guess>"],   # spoken only
  "app": "radio",
  "surface": "player",
  "recent": [{"id": "radio.volume_up", "result": "ok"}, ...],  # up to five
  "last_offer": ["radio.play_favorite", "radio.play_last"],     # for corrections, 30 s
  "local_matches": {"name": true, "number": 3, "duration": null}
}
```

- **What is never in it:** document text, the selection, file names, station or episode names, locations, account names, or anything a Quillin contributes.
- **What `local_matches` says** is only whether the computer found a name, and the values of any numbers. It never contains the name itself.

### 7.3 The questions, in one request

| Question | Type | Options | Read when |
|---|---|---|---|
| `fits` | noul | "The request asks this app to do one of the listed actions, or asks what it can do" | always |
| `action` | choice | the candidates, each with its description and one example, plus the shared rows | always |
| `steps` | choice | one, two, three | always; a second action is read only if steps is more than one |
| `action_2`, `action_3` | choice | the candidates again | steps is two or three |
| `size` | choice | small, large | the chosen command is stepped |
| `direction` | choice | forward, back | the chosen command has a direction and none was said |
| `slot_<arg>` | choice | the argument's closed set, or "a name from the person's list", "none" | the chosen command takes that argument |
| `correction` | noul | "The request corrects or rejects the previous result" | `last_offer` or `recent` is not empty |
| `correction_pick` | choice | the last offer's ids | correction is likely |
| `target_app` | choice | the family apps, plus "this app" and "none" | system-wide, with no family app in front and none named |
| `is_question` | noul | "The request asks for information, not an action" | always, to route questions to readouts or to Ask |

The gateway decides which questions a request carries. The client asks for a catalogue version and a question set (for example `basic`, `with_args` or `system_wide`), never for free-form questions.

### 7.4 The candidate list, within Jev's limits

- **Size.** Jev takes up to 255 options a choice and 64k tokens a request (32k a question). We send at most 60 candidates and the six shared rows. Each candidate is a description of under 20 words plus one example, so about 2,000 to 3,000 tokens a request.
- **When an app has more than 60 eligible candidates** (the editor can), the gateway uses Jev's speculative fan-out in one request:
  - a `group` choice over the menu groups;
  - an `action_<group>` choice for each of the top groups that tier 2 found;
  - the app reads the action for whichever group won.
- **Versions.** Candidate descriptions are versioned with the catalogue. The gateway keeps its own copy of each version, so a client can only name ids the server knows. An older client is never handed a command it doesn't have.
- **Narrowing first.** Tier 2's ranking orders the list, so the right answer is usually near the top. The list is never cut to tier 2's top few, because Jev exists for the cases tier 2 misjudges.

### 7.5 Reading the answer

1. Is `fits` below 0.3? Then the answer is "I can't do that here", with the section 11.5 pointer if one exists.
2. Is `is_question` high and the top action a READOUT? Then run the readout. If no readout fits, hand the request to Ask with the text filled in.
3. Is the top action confident with a margin (section 6.4)? Then act, or confirm if it is CONFIRM.
4. Are the top two split? Then ask "Did you mean X or Y?", using the two titles and chords, then "Something else". The answer goes back as `last_offer`.
5. Is `correction` high? Then undo the last action if it can be undone, and run `correction_pick` (section 8.7).
6. Is `steps` more than one? Then build the plan of up to three steps and preview it (section 8.6).
7. Fill any arguments from the local reader and the `slot_` answers. If a name is needed and the computer found none, open the command's dialog with the words filled in.

### 7.6 Where it runs

- **The default route** is the gateway, `POST https://ai.community-access.org/v1/decide`, with the person's existing QUILL device token.
  - The client sends `{app, catalogue_version, question_set, state}`.
  - The server builds the Jev request from its own copy of that catalogue version and calls `POST https://api.typesafe.ai/v1/systemone` with the pinned model (`jev-1.14.0` today) and the TypeSafe key.
  - It returns `{probabilities, confidence, fits, size, steps, ..., model, usage}`.
  - The key never ships in an app. Callers cannot send their own questions, so the route can't be used for anything else.
- **An optional own-key route.** A person can store their own TypeSafe key, encrypted with DPAPI like every other own key. The client then calls TypeSafe directly with the same request the gateway would build: the request builder is shared wx-free code (`quill/core/command_catalogue/jev_request.py`), and the gateway runs a copy of it.
- **Limits.** Three seconds total from the client. A 429 is honoured with its `retry-after`, but never by waiting more than the three seconds. One request in flight at a time.

### 7.7 Caps, credit and failure

- **Caps on the server:**
  - per device, 20 a minute;
  - per IP address, 60 a minute;
  - for everyone, a daily request cap (20,000 to start);
  - a monthly dollar ceiling Jeff sets.

  All are server settings, so changing them needs no new build.
- **When the cap is reached, the credit runs out or Jeff turns Jev off:**
  - The gateway answers `limit_reached`, `no_credit` or `disabled`.
  - The app says one line, once: "Jev's daily limit is reached, so I'm using your AI", or "... so I matched it here".
  - It uses tier 4, or the offline answer, until the next day. It does not ask the server again on every sentence.
- **Automatic refill** on the TypeSafe account is off, or capped at the monthly ceiling.
- **The server logs no request bodies.** It keeps aggregate counts only: requests, latency, chosen id and confidence band.

### 7.8 Consent wording

The first time Jev would be used (proposed):

> To understand requests the quick matcher can't, QUILL can send the words you typed or said, the name of this app, and the names of the commands it can do right now to Community Access's service, which asks TypeSafe, a company in San Francisco, to pick one. Nothing else is sent: no document text, file names, stations, places or accounts. TypeSafe say they do not train on it. You can change this at any time in Settings.
>
> [Use Jev] [Use my own AI instead] [Match on this computer only]

The choice is a setting, `command_understanding` (`jev`, `my_ai` or `local`), shared by both editors and every app.

### 7.9 Egress rows and error codes

- **Egress.** One reviewed site for the gateway's `/v1/decide` call, and one for the own-key TypeSafe call. Each is a `_REVIEWED_EGRESS` entry in `quill/tools/network_egress_entries.py` saying what is sent, that it is user-initiated, the consent setting, TLS and Safe Mode. The egress gate test is what counts, because the audit's command-line entry point does nothing.
- **Error codes,** all `CodedError` (GATE-EC):

| Code | When |
|---|---|
| `QUILL-AI-DECIDE-FAILED` | network or server failure |
| `QUILL-AI-DECIDE-LIMIT` | daily cap reached |
| `QUILL-AI-DECIDE-NO-CREDIT` | TypeSafe credit spent |
| `QUILL-AI-DECIDE-DISABLED` | turned off on the server |
| `QUILL-AI-DECIDE-BAD-ANSWER` | a malformed answer, or a version mismatch |
| `QUILL-AI-COMMANDPICK-FAILED` | tier 4 failed |
| `QUILL-CORE-COMMAND-NOT-OFFERED` | any engine named an id outside the list |
| `QUILL-CORE-COMMAND-NO-LONGER-AVAILABLE` | the command became unavailable before it ran |

### 7.10 Tier 4, Choose Your AI

- **One more `AiService` feature, `command_pick`.** It needs a fixed template on the gateway for the free hosted AI, and the matching `INSTRUCTIONS` row in `own_key.py` for own key, ChatGPT and Copilot.
- **Local Ollama and llama.cpp** reuse llama.cpp's `decide` pattern.
- **One question per request.** It asks only the `action` and `steps` questions, as "reply with one id from this list, or none".
- **Checking the answer.** The answer is parsed on the computer and checked against the list.

## 8. Rich ways to command

Each pattern below lists example phrases, which tier usually settles it, and the Jev question shape when Jev is needed. Every example becomes a corpus row (section 14).

### 8.1 Plain commands

- **Examples:** "save", "next heading", "what's playing", "mute".
- **Settled by:** tier 1.

### 8.2 Loose phrasing

- **Examples:** "I can't hear it", "this voice is like a chipmunk", "the radio is way too loud", "get me out of this window".
- **Settled by:** Jev, using `fits`, `action` and `size`.

### 8.3 Arguments

| Kind | Examples | Settled by | Jev shape |
|---|---|---|---|
| Number | "favourite 3", "go to line 120", "bookmark 2", "the third one" | tier 1 or 2 | `action` only; the number is local |
| Duration | "skip back 30 seconds", "sleep in 20 minutes", "an hour and a half from now" | tier 2 | `action`, `direction` |
| Time, date | "wake me at 7 tomorrow", "remind me next Friday", "alerts for this weekend" | tier 2 plus `date_parse` | `action`, `slot_when` (now, a time, a date) |
| Name | "play WNYC", "play that history podcast", "go to the Budget heading" | local name match | `action`; `slot_name` = "a name from the person's list" |
| Station or episode | "play the latest episode of my news podcast", "record the jazz station" | local match | `action`, `slot_which` (latest, next, by name) |
| File | "open my last document", "open the report from yesterday" | the recent-files list | `action`, `slot_which` (last, by name, by date) |
| Closed set | "convert these to MP3", "read with the Spanish voice", "only tornado alerts" | local, then Jev | `action`, `slot_<set>` choice over the app's constants |

### 8.4 Relative commands

- **Examples:**
  - "louder", "a lot faster", "more", "less";
  - "go back", "do that again", "again but bigger";
  - "undo that", "put it back", "how it was before".
- **Settled by:** tier 1 for the plain words. Jev reads `recent` for "more", "again" and "how it was".
- **Jev shape:** `action` with `undo_last` and `repeat_last` among the options, plus `size`.
- **Context decides "go back":** in Radio the list holds rewind, and in the editor it holds the previous position.

### 8.5 Questions answered from the app

- **Examples:**
  - "what's playing", "how long is left";
  - "how long is this document", "how many words";
  - "what's the weather like", "are there any alerts";
  - "is it recording", "where am I".
- **Settled by:** a READOUT row. The answer comes from the command's own handler, and never from Jev's text.
- **Jev shape:** `is_question` plus `action`. A question no readout answers ("why is the sky blue") goes to Ask, with the text filled in and not sent.

### 8.6 Multi-step requests

- **Examples:**
  - "open my last document and read it aloud";
  - "pause the radio and tell me the weather" (two apps, system-wide only);
  - "save and close";
  - "go to the Budget heading and select the paragraph".
- **Settled by:** a local split on "and", "then" and "and then", with each part resolved separately. Jev's `steps` question decides whether the split is real ("rock and roll" is one station).
- **The rules:**
  - at most three steps;
  - before running, a one-line preview: "Open Report.docx, then read it aloud. Enter to go." A chain of SAFE steps can skip the preview once the person turns off "Preview multi-step requests" (open decision 9);
  - a CONFIRM step anywhere makes the preview mandatory;
  - steps run in order and stop at the first failure, saying which step failed;
  - "undo that" undoes the chain step by step, newest first;
  - each step is checked against the list again just before it runs, because an earlier step can change what is available (opening a document enables Read Aloud).

### 8.7 Corrections

- **Examples:** "no, the other one", "not that", "no, louder", "I meant the second one", "wrong one".
- **Settled by:** tier 1 for "no" and "wrong", and Jev for the rest.
- **Jev shape:** `correction` plus `correction_pick` over `last_offer`, plus `action` for "no, louder".
- **The rule:**
  - When the last action ran and can be undone, undo it and run the correction.
  - When it can't be undone, ask first.
  - When the correction's target is unclear, show the last offer again as "Did you mean".
  - A correction is accepted only within 30 seconds of the last result.

### 8.8 Cross-app requests

- **Examples:** "Radio, pause", "Weather, any alerts", "pause the radio", "Cast, play the next episode", "open Quill Radio".
- **Settled by:** a local match on the app name at the start ("Radio", "the radio", "podcasts" for Cast). Jev's `target_app` is used only when no app is named and none is in front.
- **The route:** the request goes to the target app through the request file Dictate Here already uses. The target app builds its own candidate list and resolves the request itself (section 9.7).

### 8.9 Discoverability phrases

- **Examples:**
  - "what can I say", "what can I ask", "help", "what can I do here";
  - "what can I say about bookmarks";
  - "what can I say while dictating".
- **Settled by:** tier 1, from the shared rows (section 11).

### 8.10 Things it refuses, and how

| Request | Answer |
|---|---|
| "delete all my recordings" | "I won't do that from a sentence. It's in the Recordings window." |
| "write me a poem" | "That's a question for Ask. Press Alt+Shift+Q." The text is filled in, not sent. |
| "make this bold", in a plain text file | "Bold needs a rich document. This one is plain text." |
| "clone a repository", without Workbench mode | "Clone is in the GitHub menu, which Workbench mode turns on." |
| "sign me in to ChatGPT" | "Sign-in is done in Choose Your AI." |
| "flibbertigibbet" | "I can't do that here. Say 'what can I say' for ideas." |

## 9. Keys and phrases

### 9.1 F11 is the in-app Command Key

| What you do | Any time, dictating or not |
|---|---|
| Tap F11 | opens the Say or Type a Command box |
| Hold F11 | speak a command; it runs when you let go |
| Hold F11 in the box | speak into the box |

F11 never starts, stops or pauses dictation. While you are dictating and hold F11, the same microphone hears a command and nothing is written. Writing resumes when you let go. It is the same microphone (`MicrophoneLock`), not the same key.

Why F11:

- It already means "command" in both editors (rule 2).
- It is free in both as a plain key (rule 5).
- It is not on QUILL's leader (rule 6).
- Word's F11 is Next Field, which no family app has (rule 1).
- It is free in every `APP_KEYMAPS` entry and every menu chord, apart from the Radio video window.
- It is not a JAWS or NVDA key.

### 9.2 Every key, dictation on one side and commands on the other

This audit covers `keymap.py`, `app_keymaps.py`, QUILL Lite's tables, `transcribe_keys.py`, the Dictate Here binding, Inkwell's settings and `family_chords.default_system_wide_keys`.

| Where | Dictation (writes) | Commands (acts) |
|---|---|---|
| QUILL and QUILL Lite | Ctrl+F11 Dictation On (hold to talk, as set); Shift+F11 Recent Phrases; Ctrl+Shift+F11 Switch Language; Alt+Shift+F6 Dictation Settings; Alt+Shift+F10 My Words; Shift+F5 Transcribe a File; Shift+F4 Review; Alt+F9 Dictation Status; Ctrl+F3 Tidy; Ctrl+Alt+Shift+PageDown Live Transcript; Ctrl+Alt+Shift+PageUp Context | F11 Command Key; Ctrl+Shift+P Command Palette; Ctrl+Alt+Shift+F1 What Can I Say Here |
| QUILL only | Ctrl+Shift+Grave, D and Ctrl+Shift+Grave, Shift+D (older dictation); Ctrl+F9 Locked Dictation; Ctrl+Shift+F9 pause; Escape and Shift+Escape while recording | Voice Command (Offline), no key, retired into F11 |
| Radio, Cast | Ctrl+F11 Dictate Here | F11 (Radio's video window keeps F11 for Full Screen, section 9.4); Ctrl+Shift+P |
| Studio, Weather, Converter, Player, Beacon, Inkwell | Dictate Here on Ctrl+F11 (phase 4) | F11; Ctrl+Shift+P; Ctrl+Alt+Shift+F1 |
| Transcribe window | Ctrl+F11 and the editors' dictation keys | F11; Command Key... (Ctrl+Alt+Shift+K) picks the system-wide Command Key |
| System-wide | Transcribe start and stop, Alt+Shift+\ (default); Status, Resume and Discard Held Words (empty until chosen); Inkwell Dictate Anywhere (empty until chosen) | the system-wide Command Key (empty until chosen; the picker suggests Ctrl+Alt+PageDown) |
| Spoken | "Quill dictate", "stop dictation"; the "QUILL" command word for dictation phrases | "Hey Quill" (proposed) |

Overlaps found and fixed:

1. **F11 while dictating** made the next phrase a dictation command. Now it is a command.
2. **F11 while not dictating** started dictation. It no longer does.
3. **Transcribe's system-wide Command Key** armed the dictation command word. It becomes the system-wide *command* key. Anyone who already chose one keeps the key, and is told once what it now does (open decision 4).
4. **The first pass had dictation phrases fall through to the catalogue.** That is removed; the two tables never mix.
5. **Speak a Command lives in the Tools, Dictation submenu** in both editors (`commands_dictation.py`, line 84). It moves out, as Say or Type a Command.

Not changed:

- Push-to-talk and hold-to-talk on Ctrl+F11 stay dictation.
- Inkwell's Quick Insert and Expand keys aren't dictation, and stay where they are.

### 9.3 The keyboard way to a dictation phrase

Today, F11 then "scratch that" was the keyboard way into the dictation grammar. With F11 now commands only, the dictation grammar is still reached by the command word ("QUILL scratch that") and by its bare phrases.

**Recommendation:** keep a dictation-side command, "Next Phrase Is a Dictation Command". Give it no key, with a written reason (rule 8): the command word does the same job, and a key beside F11 would bring back the confusion this plan removes. Open decision 5.

### 9.4 Conflicts and fallbacks

- **The one in-app conflict is the Radio video window,** where F11 is Full Screen (`radio_video_menu.py`, line 132), as browsers do it.
  - Keep it there (rule 1). The Command Key is reached from the player window.
  - Record it with a `keymap.py` comment and a parity row (rule 11).
- **Fallbacks if F11 is refused:**
  - Ctrl+Grave. It is free everywhere, but it is a dead key on many layouts and easy to confuse with QUILL's leader.
  - The palette acting on a confident sentence. The palette gets the matcher anyway.
- **Already taken:**
  - Ctrl+Shift+Space is Say Windows Open in both editors.
  - Ctrl+Alt+Shift+K is taken in eight apps.

### 9.5 The system-wide Command Key

- **The route.** Transcribe's existing Command Key setting (`command_hotkey`) becomes the system-wide Command Key, offered beside the Record Key in setup and on File, Command Key....
- **Registered only once chosen.** It stays empty until the person picks one, as the family rule requires.
- **Tap and hold.** A tap opens a small Command box from Transcribe, wherever you are. Holding it speaks a command, using Transcribe's held-key reading. Words wait until the modifiers are up, through `KeyHeldGate`.
- **The suggestion.** The picker suggests **Ctrl+Alt+PageDown**, and the person can take it or choose another.

How it was checked:

1. Every Alt+Shift, Ctrl+Alt and Ctrl+Alt+Shift chord with a letter, digit, F1 to F12, punctuation or navigation key was run through `family_chords.show_hide_key_problem`. That is the picker's own check against every family app's menus, keymaps and system-wide keys. 14 chords passed, not counting Alt+Shift+\, which is dictation's own key:
   - Alt+Shift+F4, Alt+Shift+Backspace;
   - Ctrl+Alt+8, Ctrl+Alt+F4, Ctrl+Alt+\, Ctrl+Alt+;, Ctrl+Alt+', Ctrl+Alt+[, Ctrl+Alt+];
   - Ctrl+Alt+PageUp, Ctrl+Alt+PageDown, Ctrl+Alt+Delete;
   - Ctrl+Alt+Shift+Left, Ctrl+Alt+Shift+Right.
2. Then they were filtered by hand:
   - **Ctrl+Alt with a digit or punctuation** is AltGr on many European layouts. A system-wide one would stop people typing characters, so 8, \, ;, ', [ and ] are out.
   - **Ctrl+Alt+Delete** is Windows'.
   - **Alt+Shift+F4 and Ctrl+Alt+F4** are one slip from closing a window.
   - **Alt+Shift+Backspace** is next to the input-language switch and to Alt+Backspace, which is undo.
   - **Ctrl+Alt+Shift with the arrows** is one slip from the screen readers' table keys, Ctrl+Alt with the arrows.
3. That left Ctrl+Alt+PageDown and Ctrl+Alt+PageUp.
   - Neither types a character, and neither is a JAWS or NVDA default as far as we know.
   - Neither is near dictation's Alt+Shift+\ or Inkwell's keys, which are empty by default.
   - PageDown reads as "go in".
   - The cost: while registered, Word loses Ctrl+Alt+PageDown, "bottom of window". That is acceptable for an opt-in key.
4. **Still to check:** JAWS, NVDA, Narrator, Magnifier and ZoomText key lists, and common laptop vendor utilities, before phase 4.

The alternative suggestion is Ctrl+Alt+PageUp.

### 9.6 Spoken phrases

- **"Quill dictate"** (setting `windows_dictation_wake_phrase`, unchanged) starts dictation. "Stop dictation" stops it.
- **The command phrase** (new setting `command_wake_phrase`, off by default). Saying it, then the request, runs a command, from the target window's list only. Options:

| Phrase | For | Against |
|---|---|---|
| **"Hey Quill"** (recommended) | It doesn't start with "Quill", so the dictation command-word parser (which matches "QUILL" as the first word after a pause) never sees it. It sounds nothing like "Quill dictate" after the first syllable. It is two words, as the wake rule requires. It matches the Hey QUILL plan of record. Spanish is "Oye Quill". | People may expect it to answer questions. Questions go to Ask with the text filled in, as section 8.5 says. |
| "Quill do" | short, and Jeff's example | It starts with the dictation command word, so the two parsers would have to share a boundary. "Do" is often heard as "to", "two" or "due", and it shares its first sound with "dictate". |
| "Okay Quill" | the same separation as "Hey Quill" | "Okay" begins many dictated sentences |
| "Quill command" | clear | collides with "QUILL command mode", which is already a dictation phrase |

- **Like the wake phrase,** the command phrase is listened for only while the shared listening switch is on (section 10.9), and nothing heard before it is kept or sent.

### 9.7 Targeting from anywhere

For the system-wide key or the command phrase:

1. **A family app is in front.** That app and its focused window's list.
2. **Otherwise, the request starts with an app's name.** "Radio, pause" and "Weather, any alerts" go to that app's main window list, if the app is running. If it isn't, the only command offered is "open Quill Radio".
3. **Otherwise,** one sentence: "Say which app, for example 'Radio, pause'."

Transcribe only hears and routes. It sends the text to the target app through the request file (`send_request`, with a new `command` request kind), and the target app resolves it against its own list. Transcribe never resolves another app's commands, so the list is always the target window's. The result is spoken by the target app through its announcement service.

## 10. The user experience

This section is written for a screen-reader user throughout, under GATE-13 (speak only what the reader doesn't already say) and GATE-BRAILLE (everything spoken is brailled).

### 10.1 Typed

1. **Tap F11.** The reader says the box's title. The app says nothing, except a one-time hint the very first time (section 11.4).
2. **Type and press Enter.**
3. **One result line,** in the command's words with the new value: "Reading speed 40". It is silent if the handler announces its own result. `action_feedback` applies; counts and failures are always spoken.
4. **Focus returns.** The reader says where.

### 10.2 Spoken in an app

1. **Hold F11.** The listening sound plays and nothing is said.
2. **Speak and let go.** The words are shown in the status bar for braille.
3. **One result line.**
4. **When something goes wrong:** "Didn't catch that" when nothing usable was heard, and "I can't do that here" when nothing fits.

### 10.3 From anywhere

1. **Press the system-wide Command Key,** or say "Hey Quill".
2. **The result line comes from the target app.**
3. **When there is no target,** one sentence says which app to name.

### 10.4 Clarification

- **The list.** "Did you mean" holds two or three commands, each with its title and chord, then "Something else".
- **The keys.** Arrows move, Enter runs and Escape leaves.
- **Announcements.** The reader reads the list, so the app announces nothing.
- **Spoken.** In the spoken route, the question is said once ("Pause, or stop?"). Holding F11 and answering, or saying "the first one", picks.

### 10.5 Corrections, undo and preview

- **Corrections** follow section 8.7.
- **Undo that** puts back the last five changes made from the box, each with its old value. Document edits use the editor's own undo, so Ctrl+Z works too.
- **"What would you do if I said..."**, or the "Tell me, don't do it" check box, describes what would happen and runs nothing.

### 10.6 Confirmation

- **CONFIRM commands always ask,** in one line: "Stop every recording? Enter to stop, Escape to cancel."
- **The dialog.** It is shown through `_show_modal_dialog`, with `bind_close_button`. OK and Cancel carry no access key.
- **Multi-step.** A preview for a request with several steps is a confirmation of the same kind.

### 10.7 Offline

- **Without a network,** tiers 1 and 2 still work, and so does a local tier 4.
- **When Jev can't be reached,** the app says one line, once, and uses the next tier. The fallback is visible, never silent.

### 10.8 Speed

- **Tiers 1 and 2** answer at once.
- **Jev or tier 4** plays the thinking sound once at 600 ms, and gives up at 3 seconds.
- **Escape** cancels.

### 10.9 One listening switch and one privacy notice

- **One switch: Listening On or Off.**
  - It is a family setting, kept beside the family microphone lock in `dictation_owner`. Every app's Tools menu has it, and so does Transcribe's tray.
  - Off stops everything that listens: dictation, Dictate Here, the wake phrase, the command phrase, and F11 held.
  - Turning it off says "Listening off", once. F11 held while it is off says "Listening is off", and a tap still opens the typed box.
  - Its key is open decision 11.
- **One privacy notice for listening,** shown the first time anything in the family listens, whether for dictation or for commands. It covers:
  - when the microphone is used (only while dictating, while a key is held, or while waiting for a phrase you turned on);
  - which speech engine hears you, and whether that engine is on this computer or a named cloud service;
  - that nothing heard before a wake or command phrase is kept or sent;
  - where to turn listening off.

  It replaces the separate first-use notes. It is shown once, and can be read again from Help.
- **Text sent to an engine is a separate question,** because it is not about listening: the Jev consent in section 7.8.
- **Safe Mode** turns the whole feature off, along with listening for commands.

## 11. Finding out what you can say

### 11.1 "What can I say here?"

- **The phrases:** "what can I say", "what can I ask", "what can I do here" and "help", typed or spoken through the Command Key. Also Help, What Can I Say Here.
- **What it answers from:** the catalogue, for this window, right now, and only enabled commands. It uses exactly the candidate list a request would get.
- **How it is ordered:** most used first (from the palette's usage memory), then by menu group.
- **Each entry has** a spoken name, one short example and its key if it has one: "Volume Down. Say 'turn it down'. Control Down."
- **Typed:** the box becomes a browsable list, with group headings as the first item of each group. Arrows move, Enter runs the command, Escape leaves. The reader reads the items, and the app says only the count when the list opens ("12 things you can do here"), because only the app knows it.
- **Spoken:** it is read in pages, never as one long announcement.
  1. The count and the groups first: "12 things you can do here, in 3 groups: Playback, Favourites, Recording."
  2. Then the first group, up to five entries.
  3. "Next", "previous", "repeat" or "stop", said with F11 held within 30 seconds, moves on. So does F11 tapped, which opens the list at that page.
- **Filters:** "what can I say about bookmarks" narrows by words in titles, aliases, examples and group names. With no hits, it says "Nothing about bookmarks here" and offers the whole list.

### 11.2 "What can I say while dictating?"

- **It answers dictation's list,** from the existing generated reference (`quill/core/windows_dictation/reference.py`): scratch that, caps on, select the cat, and the rest.
- **It is titled "While dictating, you can say"** and shown in its own list, never mixed with commands, to match the separate keys.
- **It is reached** through the Command Key, through the dictation command word ("QUILL what can I say", which dictation already understands), and from Dictation Settings' Commands button.

### 11.3 Examples in the catalogue

- **The field.** Every SAFE and CONFIRM row has an `examples` tuple. The gate requires at least one, and the target is three.
- **What the examples feed:** this help, F1, `docs/command-catalogue.md`, Jev's candidate descriptions, and the corpus. Every example must resolve to its own command through tiers 1 and 2, or through Jev in the recorded suite.

### 11.4 Other ways in

- **The Help menu.** Every app gets a What Can I Say Here? row in its Help menu, on Ctrl+Alt+Shift+F1.
  - In QUILL it replaces What Can I Do Here? (`help.what_can_i_do_here`), keeping the id and the key, so nobody's binding breaks.
  - The F-row comment in `app_keymaps.py` already reserves Ctrl+Alt+Shift+F1 for it across the family.
  - Ask's "What can I do here?" prompt gives the same answer, from the same rows.
- **A one-time hint** the first time the box ever opens, in any app: "Type what you want, or say 'what can I say'." It is never repeated (GATE-13). Whether it has been shown is a family setting.

### 11.5 "I can't do that here, but you can..."

When nothing in the candidate list fits, the request is matched locally against the whole catalogue, including disabled commands and other apps. That wider match is only used to explain. It never runs anything, and no engine sees it.

| Case | Answer |
|---|---|
| Disabled here | the command probe's reason: "Bold needs a rich document. This one is plain text." |
| In another window of this app | "That's in the Recordings window. Ctrl+Shift+R opens it." |
| In another app | "That's in Quill Radio. Say 'Radio, play'." |
| Behind a mode or feature | "Clone is in the GitHub menu, which Workbench mode turns on." |
| NEVER | "I won't do that from a sentence. It's in File, Accounts." |

### 11.6 The generated reference

`docs/command-catalogue.md` ("What you can say in each app") lists every command per app, with its examples, key and group. It is generated and drift-gated (GATE-CATREF), like the keyboard reference. Dictation's list stays in its own generated document.

## 12. Safety

- **Never offered by sentence:**
  - sign-in, sign-out and account removal;
  - keys, tokens and passwords;
  - updates, installs and downloads;
  - Safe Mode and diagnostics;
  - outside code, shells, Quillin commands, agents, and Codex and Copilot sessions;
  - sending, publishing, uploading and pushing;
  - deleting files, recordings or episodes;
  - editing keys and keymaps;
  - network and privacy settings, including this feature's own consent;
  - choosing or registering system-wide keys.
- **Always confirm:**
  - discarding unsaved work, closing and exiting;
  - stopping a recording;
  - overwriting or writing many files;
  - marking many items;
  - spending hosted-AI quota;
  - anything that can't be undone;
  - multi-step chains that include any of these.
- **Validation** follows section 6.2.
- **Agents.** `agent_ok` is false on every CONFIRM and NEVER row, and `SAFE_TOOL_IDS` becomes the catalogue's `agent_ok` view.
- **Push-to-talk** gets the shared policy, so it confirms CONFIRM rows. Today it never confirms.
- **Quillins** can't add catalogue rows until a reviewed manifest field for descriptions and risk exists. A Quillin command is NEVER by default.

## 13. Per-app scope

The tables below list the commands each app offers by sentence. Chords are today's defaults. "Confirm" means CONFIRM class. Every app also has the shared rows. Examples come in phase 1's review, at least one and ideally three per row.

- **QUILL has no faster or slower command for Read Aloud.** `tools.read_aloud_faster` and `tools.read_aloud_slower` are added, with keys, in the shared package (rules 8 and 10).
- **Inkwell, Converter, Player, Beacon and Transcribe** get command ids in phase 6.

### 13.1 QUILL

| Command id | Chord | What the person wants | Confirm |
|---|---|---|---|
| `tools.read_aloud_start_pause` | Ctrl+Shift+Grave, R | Read the document aloud, or pause | No |
| `tools.read_aloud_stop` | Ctrl+Shift+Grave, Shift+R | Stop reading aloud | No |
| `tools.read_aloud_faster` / `slower` (new) | to be chosen | Faster or slower reading voice | No |
| `tools.read_aloud_voice` | none | Choose a reading voice ("the Spanish voice" picks it) | No |
| `edit.say_selected` | Ctrl+Shift+Y | Read out what is selected | No |
| `navigate.say_time` | Alt+Shift+Space | The time and date | No |
| `navigate.speak_status_summary` | Ctrl+Shift+Grave, Q | Where am I, and the document's state | No |
| `verbosity.toggle_quiet` / `toggle_meeting` | Ctrl+Shift+Grave, Shift+Q / Shift+M | Talk less; I'm in a meeting | No |
| `tools.sound_toggle` | Alt+Shift+M | Sounds on or off | No |
| `edit.undo` / `edit.redo` | Ctrl+Z / Ctrl+Y | Undo, redo | No |
| `edit.find` | Ctrl+F | Find (the words fill the box) | No |
| `navigate.go_to_line` | Ctrl+G | Go to line 120 | No |
| `navigate.next_heading` / `previous_heading` | Ctrl+Alt+H / Ctrl+Alt+Shift+H | Next or previous heading | No |
| `navigate.outline_navigator` | Ctrl+Shift+O | Show the headings; "go to the Budget heading" matches locally | No |
| `navigate.next_bookmark` / `set_numbered_bookmark` | F2 / Ctrl+Shift+B | Next bookmark; bookmark this spot | No |
| `format.bold` / `format.italic` | Ctrl+B / Ctrl+I | Bold or italic (rich documents only) | No |
| `format.grow_font` / `shrink_font` | Ctrl+Shift+. / Ctrl+Shift+, | Bigger or smaller text | No |
| `tools.word_count` | Ctrl+Shift+G | How many words; how long is this document | No |
| `tools.spell_check_dialog` / `next_misspelling` | F7 / Ctrl+F7 | Spelling | No |
| `file.recent_documents` | Alt+Shift+0 | Open my last document (a name matches locally) | No |
| `file.save` | Ctrl+S | Save | No |
| `file.close_document` | Ctrl+W | Close this document | Yes |
| `app.command_palette` | Ctrl+Shift+P | Show me every command | No |

Never by sentence in QUILL:

- `app.exit`, `tools.check_updates`, and every `tools.hosted_ai_*` sign-in, key and account command;
- `file.save_to_remote` and `file.github_save_back`;
- the `project.*` agent commands;
- every dictation command, which is dictation's side.

### 13.2 QUILL Lite

These are the same rows as QUILL wherever `COMMAND_EQUIVALENTS` maps them. QUILL Lite has no Read Aloud, and it gains no row that QUILL lacks.

| QUILL Lite handler | Chord | What the person wants | Confirm |
|---|---|---|---|
| `cmd_say_selection`, `cmd_say_time` | Ctrl+Shift+Y, Alt+Shift+Space | Read the selection; time and date | No |
| `cmd_word_summary` | Ctrl+Alt+Shift+[ | How many words | No |
| `cmd_undo`, `cmd_redo` | Ctrl+Z, Ctrl+Y | Undo, redo | No |
| `cmd_find`, `cmd_find_next` | Ctrl+F, F3 | Find, find next | No |
| `cmd_goto_line`, `cmd_go_to_anything` | Ctrl+G, Ctrl+Alt+Shift+A | Go to a line; go to anything | No |
| `cmd_next_heading`, `cmd_previous_heading`, `cmd_list_headings` | Ctrl+Alt+H, Ctrl+Alt+Shift+H, Ctrl+Alt+L | Headings | No |
| `cmd_toggle_heading_announcements` | Ctrl+Alt+F3 | Say headings as I move | No |
| `cmd_set_bookmark`, `cmd_next_bookmark` | Ctrl+Shift+B, F2 | Bookmarks | No |
| `cmd_zoom_in`, `cmd_zoom_out`, `cmd_zoom_reset` | Ctrl+=, Ctrl+-, Ctrl+0 | Text size | No |
| `cmd_spell_review`, `cmd_toggle_live_spelling` | F7, Ctrl+Alt+F7 | Spelling | No |
| `cmd_toggle_quiet_mode` | Alt+Shift+M | Sounds on or off | No |
| `cmd_save` | Ctrl+S | Save | No |
| `cmd_close` | Ctrl+W | Close this window | Yes |
| `cmd_clear_bookmarks` | Ctrl+Alt+B | Clear all bookmarks | Yes |

Never by sentence in QUILL Lite: `cmd_exit`, `cmd_toggle_read_only`, `cmd_close_project`, `cmd_undo_agent_turn`, `cmd_github_manage_accounts` and the dictation commands.

### 13.3 Radio

| Command id | Chord | What the person wants | Confirm |
|---|---|---|---|
| `radio.play_pause`, `radio.stop`, `radio.play_last` | Ctrl+P, Ctrl+., Ctrl+L | Play or pause, stop, the last station | No |
| `radio.play_favorite` | Alt+Shift+F | Play a favourite, by number or by name (local) | No |
| `radio.toggle_playing_favorite` | Ctrl+Shift+F | Add to favourites, or take off | No |
| `radio.volume_up`, `volume_down`, `mute_toggle` | Ctrl+Up, Ctrl+Down, Ctrl+M | Louder, quieter, mute | No |
| `radio.volume_boost` | Ctrl+Shift+B | Boost a quiet station | No |
| `radio.rewind`, `radio.forward`, `radio.jump_to_live` | Ctrl+Shift+Left, Ctrl+Shift+Right, Ctrl+Shift+L | Back, forward ("back 30 seconds"), live | No |
| `radio.identify_song`, `whats_playing_details`, `song_history` | Ctrl+K, Ctrl+T, Ctrl+Shift+H | What's this song; what's playing; what played earlier | No |
| `radio.lyrics`, `browse`, `find_streams`, `on_now` | Ctrl+Alt+B, Ctrl+B, Ctrl+Alt+S, Ctrl+Alt+H | Lyrics, browse, find a station, what's on | No |
| `radio.record_station`, `record_toggle`, `stop_all_recordings` | Ctrl+Alt+R, Ctrl+R, Ctrl+Alt+X | Recording | Yes |
| `radio.recordings` | Ctrl+Shift+R | My recordings | No |
| `radio.wake_timer`, `media.sleep_timer` | Ctrl+Alt+Z, Ctrl+Shift+Z | "Wake me at 7"; "sleep in 20 minutes" | No |
| `radio.transport.speed_up`, `speed_down`, `speed_reset` | Ctrl+Shift+Up, Ctrl+Shift+Down, Ctrl+Shift+0 | Faster, slower, normal | No |
| `radio.toggle_title_announcements` | Ctrl+Alt+T | Say song titles, or stop | No |
| `app.undo_last` | Ctrl+Z | Undo the last thing I did | No |

Never by sentence in Radio:

- `radio.forget_station_volumes`, `radio.update_catalog` and `radio.download_preferences`;
- `app.import_setup` and `app.export_setup`;
- `radio.chatgpt_account`, and every hosted AI account, key and privacy command;
- the YouTube imports;
- `radio.suggest_pick`.

### 13.4 Cast

| Command id | Chord | What the person wants | Confirm |
|---|---|---|---|
| `podcasts.say_now_playing`, `time_remaining`, `player_information` | Ctrl+T, Ctrl+Shift+T, Ctrl+I | What's playing, how long is left, about this episode | No |
| `podcasts.skip_silence` | Ctrl+Shift+9 | Skip silences | No |
| `podcasts.go_to_position` | Ctrl+Alt+J | "Go to 12 minutes" | No |
| `podcasts.mark_played_and_next` | Ctrl+Alt+Shift+Down | Mark played, play next | No |
| `podcasts.bookmark_note`, `episode_bookmarks`, `app.bookmark_moment` | Ctrl+Shift+D, Ctrl+Shift+J, Ctrl+Alt+A | Bookmarks | No |
| `podcasts.refresh_feed`, `media.refresh_podcasts` | F5, Ctrl+F5 | Check for new episodes | No |
| `podcasts.now_playing`, `podcasts.lineups` | Ctrl+Alt+2, Ctrl+U | What's playing; lineups | No |
| `podcasts.new_folder`, `move_to_folder` | Ctrl+Shift+E, Ctrl+Shift+V | Folders | No |
| `podcasts.mark_all_played` | Alt+Shift+E | Mark everything played | Yes |
| `app.repeat_last_result`, `app.quiet_hours`, `app.undo_last` | F9, Ctrl+Alt+Shift+Z, Ctrl+Z | Say that again; quiet hours; undo | No |

Never by sentence in Cast:

- backup, restore, and import or export of setup;
- `media.sync_places`;
- every hosted AI account command.

Cast's `_cast_command_unavailable_reason` becomes its command probes.

### 13.5 Studio

| Command id | Chord | What the person wants | Confirm |
|---|---|---|---|
| `studio.capture`, `capture_active`, `capture_desktop` | Ctrl+Alt+Shift+S, Ctrl+Alt+Shift+F5, Ctrl+Alt+Shift+F6 | Screenshots | No |
| `studio.inspect_capture` | Ctrl+Alt+Shift+I | About the last screenshot | No |
| `studio.describe_picture` | Ctrl+F5 | Describe this picture (spends hosted AI) | Yes |
| `studio.record_demo` | Ctrl+Alt+Shift+V | Start recording a demo | Yes |
| `studio.record_pause`, `record_marker`, `record_mute`, `record_status` | Ctrl+Alt+Shift+P, Ctrl+Alt+Shift+B, Ctrl+Alt+Shift+U, Ctrl+Alt+Shift+T | Pause, marker, mute, status | No |
| `studio.camera_check`, `studio.mixer` | Ctrl+Alt+Shift+C, Ctrl+Alt+Shift+M | Camera check, mixer | No |
| `studio.broadcast_mute` | Ctrl+Alt+Shift+Z | Mute the broadcast | No |
| `studio.broadcast_stop` | Ctrl+Alt+Shift+E | Stop broadcasting | Yes |

Never by sentence in Studio: `record_discard`, `record_emergency_stop`, `record_recover`, `broadcast`, `chatgpt_account` and `tools.hosted_ai_privacy`.

### 13.6 Weather

| Command id | Chord | What the person wants | Confirm |
|---|---|---|---|
| `weather.now`, `quick`, `alerts` | Ctrl+Shift+W, Ctrl+Shift+Q, Ctrl+Shift+Alt+A | Weather now; short version; any alerts | No |
| `weather.monitor_toggle`, `monitor_pause`, `test_alert` | Ctrl+Alt+Shift+M, Ctrl+Alt+Shift+P, Ctrl+Alt+Shift+T | Alerts on or off; "pause alerts for an hour"; test | No |
| `weather.noaa_listen` | Ctrl+Alt+N | NOAA weather radio (when installed) | No |
| `weather.add_location`, `weather.settings` | Ctrl+Alt+Shift+L, Ctrl+Alt+Shift+F | Add a place (typed in the dialog); settings | No |

Never by sentence in Weather: `weather.noaa_update`. Locations are matched locally, never sent.

### 13.7 Inkwell (ids in phase 6)

| Command | Chord | What the person wants | Confirm |
|---|---|---|---|
| Manage Abbreviations | Ctrl+M | Show my abbreviations | No |
| Quick Insert | Ctrl+K | Insert an abbreviation (a name matches locally) | No |
| Expand the Word I Just Typed | Ctrl+Alt+E | Expand what I typed | No |
| Expand in other applications | Ctrl+Shift+E | Expansion in other programs on or off | Yes |
| Excluded Applications | Ctrl+Alt+X | Stop expanding in a program | No |

Never by sentence in Inkwell: Start with Windows, Insert by Pasting, the key pickers, Exit and Check for Updates.

### 13.8 Converter (ids in phase 6)

| Command | Chord | What the person wants | Confirm |
|---|---|---|---|
| Convert Now | Ctrl+Enter | Convert ("as MP3" picks the format) | Yes |
| Preview with Your Settings | Ctrl+P | Hear how it will sound | No |
| Paste Files, Convert from URL | Ctrl+V, Ctrl+U | Add copied files; convert from a web address | No |
| Join into One File, Split by Chapters | Ctrl+J, Ctrl+Shift+S | Join; split | Yes |
| Chapter Workbench, Edit Tags, Custom Effects | Ctrl+H, Ctrl+T, Ctrl+E | Chapters, tags, effects | No |
| Open Output Folder, Open Output Folder When Done | Ctrl+Shift+F, Ctrl+Shift+W | Where the files went | No |
| Conversion Report | Ctrl+R | How did it go | No |

Never by sentence in Converter: Upload to WordPress, every Auphonic command, Get FFmpeg and Exit.

### 13.9 Player (ids in phase 6)

The Player's `VoiceIntent` actions become catalogue rows, and Ctrl+Shift+V opens the Command box.

| Command | Chord | What the person wants | Confirm |
|---|---|---|---|
| toggle, play, pause, stop | player keys | Playback | No |
| faster, slower, volume up and down, mute | player keys | Speed, volume | No |
| skip, seek | player keys | "Skip back 30 seconds", "go to 1 hour 5" | No |
| next and previous chapter | player keys | Chapters | No |
| where am I | Shift+F6 | Where am I in the book | No |
| bookmark | Ctrl+Shift+B | Bookmark this spot | No |
| sleep, sleep at end of chapter | Sleep Timer submenu | "Stop in 20 minutes", "at the end of the chapter" | No |
| recap, summarize | Playback menu | What happened so far (hosted AI) | Yes |
| Go to Position, Bookmarks, Lyrics, Audio Output Device | Ctrl+G, Ctrl+Alt+M, Ctrl+Alt+L, Ctrl+Shift+K | Position, bookmarks, lyrics, sound card | No |

Never by sentence in Player: Import Sync Bundle, Check for Updates and Exit.

### 13.10 Beacon (ids in phase 6)

| Command | Chord | What the person wants | Confirm |
|---|---|---|---|
| New Bookmark, Build Search, Open Selected | Ctrl+N, Ctrl+Shift+F, Enter | Save, find, open | No |
| Toggle Favorite, Add to Collection | Ctrl+D, Ctrl+L | Favourite; collection | No |
| Archive Selected, Trash Selected | Ctrl+Shift+A, Delete | Archive; trash | Yes |
| Restore Selected, Undo | Shift+Delete, Ctrl+Z | Bring back; undo | No |
| Play in Player, Refresh Feeds, Sync Now | Ctrl+Shift+L, Ctrl+Shift+R, F9 | Play, check feeds, sync | No |
| Status Center, Where Am I? | Ctrl+Alt+I, Ctrl+F1 | How is everything; where am I | No |
| Suggest Tags, Summarize Note | Ctrl+Shift+T, Ctrl+Shift+M | Local suggestions | No |

Never by sentence in Beacon: every Bulk command, Import, Export, Sync Settings, Capture Bridge and Review Location Repair.

### 13.11 Transcribe (ids in phase 6)

Transcribe's window commands are commands. Its dictation keys stay on dictation's side.

| Command | Chord | What the person wants | Confirm |
|---|---|---|---|
| Dictation Status (readout) | chosen by the person | Is it listening, and where is it typing | No |
| Recent Phrases | Shift+F11 | What did I just say | No |
| Resume Held Words | chosen | Type the held words | No |
| Discard Held Words | chosen | Throw the held words away | Yes |
| Show or hide the window | chosen | Bring Transcribe up, or away | No |
| Open a family app | none | "Open Quill Radio" (system-wide) | No |

Never by sentence in Transcribe:

- starting or stopping dictation, which belongs to dictation's keys and phrase;
- choosing any system-wide key;
- the never-type list, model downloads and cloud sign-in;
- Exit and Check for Updates.

### 13.12 GitHub Workbench (both editors)

| Command | What the person wants | Class |
|---|---|---|
| Open the GitHub Workbench | Show my GitHub | SAFE |
| Open from GitHub, Open GitHub Reference | Open a file or the guide (a repository name matches locally) | SAFE |
| Notifications, issues, pull requests | What needs my attention | SAFE |
| Compare branches, workflow runs, artifacts | Show me | SAFE |
| Draft an issue | Start an issue (nothing is sent) | SAFE |
| Clone | Clone a repository (opens the dialog) | SAFE, Workbench mode only |
| Save back, push, merge, comment, create, fork, rename or delete a repository, branch protection, releases | Anything that changes GitHub | NEVER |
| Sign In with GitHub, Manage Accounts | Accounts | NEVER |

These rows join once the menu work settles the ids.

## 14. Testing strategy

Testing drives the phases. No phase ships without its corpus rows and the gates below passing.

### 14.1 The corpus

There is one file per app, `tests/fixtures/command_key/<app>.jsonl`. Each row holds:

```
{"text": "turn it down a bit", "mode": "typed|dictated|misheard",
 "heard_alternatives": [], "app": "radio", "surface": "Quill Radio",
 "enabled": ["...ids, or 'default'"], "recent": [], "last_offer": [],
 "expect": {"id": "radio.volume_down", "args": {"size": "small"}}
           | {"refuse": "not_here|never|ask|other_app|disabled", "pointer": "radio"}
 , "tier_max": 2, "set": "train|held_out"}
```

What goes in it, for every offered command:

- at least 20 typed phrasings: plain, terse, indirect, complaints, typos and other people's words;
- at least 5 dictated phrasings, recorded through the default offline engine;
- at least 5 misheard ones, including common misrecognitions ("quill" as "quilt", "favourite" as "favour it");
- every catalogue example, each expected to resolve to its own command.

What goes in it, for every app:

- 25 percent or more negatives: NEVER commands, questions for Ask, other apps' commands and nonsense;
- 10 percent or more disabled-here rows: the right command, but the `enabled` field leaves it out, so the expected answer is a refusal with the right reason.

Each pattern in section 8 has its own rows: arguments, relative, questions, multi-step, corrections, cross-app and discoverability.

Sizes:

- **Phase 2:** about 2,500 rows for QUILL, QUILL Lite and Radio.
- **Phase 3:** 6,000 rows.
- **Full scope:** about 20,000 rows family-wide. QUILL around 5,000, QUILL Lite 3,000, Radio 2,500, and every other app 800 to 1,500.
- **Held out:** a fifth of the rows, including every blind tester's phrasing. It is never used for tuning.

### 14.2 Fakes, so everything runs offline in CI

- **`FakeJevClient`** takes scripted probabilities, confidence and `fits` for each request, chosen per test or by a rule. It can also:
  - raise a 429 with `retry-after`, a timeout, `no_credit`, `limit_reached` or `disabled`;
  - return a malformed answer, an id outside the list, or an older catalogue version.

  It records every request, so tests can assert what was and wasn't sent.
- **`FakeCommandPickEngine`**, for Choose Your AI, returns scripted text: a clean id, an id wrapped in prose, JSON-like text, an id not in the list, an empty answer, or a failure.
- **`FakeRecognizer`** feeds transcripts, n-best lists and misrecognitions, and can time out.
- **`FakeContext` and `FakeRegistry`** script the app, the surface, the availability probes, and changes between asking and running.
- **`FakeAnnouncer`** captures every spoken and brailled string.
- **`FakeClock`** controls the 30-second correction window, the 600 ms thinking sound and the 3-second timeout.
- **`FakeRequestFile`** carries cross-app routing.

All live in `tests/unit/core/command_catalogue/fakes.py`, wx-free.

### 14.3 Property tests (Hypothesis, already a dev dependency)

These are generated over random catalogues, contexts, enabled sets, engine answers and phrasings.

- **No command runs outside the candidate list** handed to the policy, whatever any engine returns.
- **No NEVER command runs,** and none is ever sent to any engine.
- **Every CONFIRM command, and every chain containing one, confirms** before running, at any confidence.
- **A command unavailable at run time never runs,** even if it was available when asked.
- **No local name, document text or file name** ever appears in a Jev or tier-4 request payload.
- **At most one engine request is in flight,** and every request ends in a result, a question, a refusal or a fallback. Nothing hangs.
- **Undo after any sequence of up to five actions** restores the recorded values in reverse order.
- **The words a person hears** come only from the app's strings, never from an engine's text.

### 14.4 Context gating tests

- For every corpus row, run the resolver with the row's `enabled` set and assert the expected id or refusal.
- Then rerun with the expected command removed from `enabled`, and assert a refusal with the probe's reason. The command must not be swapped for a near miss.
- Surface tests: a Radio recording command is never chosen while the focus is in Settings. Bold is never chosen in a plain text document.
- Cross-app: a request routed to Radio is resolved against Radio's list only, never the sender's.
- Separation: no dictation phrase ever resolves to a command, no command phrase ever writes text, and F11 never changes dictation's state.

### 14.5 Coverage gates

- **GATE-CORPUS.** Every SAFE and CONFIRM catalogue row has at least the section 14.1 minimums in the corpus. Every example resolves to its own command in tiers 1 and 2, or is marked `needs_jev` and passes in the recorded suite.
- **GATE-CATALOGUE.** Every registered command is classified (section 15).
- **Line and branch coverage** of `quill/core/command_catalogue/` is at least 95 percent, and the policy module is at 100 percent.
- **Every Jev question** in section 7.3 has a test where it decides the outcome.

### 14.6 Announcement tests (GATE-13, GATE-BRAILLE)

- The box's title, what was typed, the list's items and focus changes are never announced.
- Every result line goes through the announcement service, and the `FakeAnnouncer` sees the same string in speech and braille.
- The one-time hint is spoken once, ever. The help count is spoken once a list.
- No result line is longer than 12 words. A spoken help page has no more than five entries.

### 14.7 The recorded live suite

- **Where it lives.** `tests/live/test_jev_live.py`, marked `live_jev`. It needs a gateway token or a TypeSafe key, and is skipped without one.
- **When it runs.** By hand or nightly, never in PR CI.
- **What it does.**
  - It sends the held-out set and the `needs_jev` rows through the real gateway, with the model version pinned.
  - It records each request and answer as a cassette under `tests/fixtures/command_key/cassettes/`, which PR CI then replays offline as a regression test.
  - It writes a report: accuracy, calibration by confidence band, latency (median and 95th percentile), tokens, and dollars per 1,000 requests, by app and by pattern.
- **A new Jev version** runs the whole suite before the pin moves.

### 14.8 Targets

| Measure | Target |
|---|---|
| Wrong act, all tiers | under 1 percent of positives |
| Wrong act on CONFIRM, and any NEVER run | zero (property-tested) |
| Correct act or correct clarification | 95 percent or more |
| Clarifications | under 10 percent of positives |
| Negatives that act | under 2 percent |
| Disabled-here rows refused with the right reason | 98 percent or more |
| Tiers 1 and 2 alone, terse and plain phrasings | 90 percent correct acts |
| Jev over tiers 1 and 2, loose phrasing | 15 points more correct acts, or better |
| Jev calibration error (expected calibration error) | under 0.05 |
| Dictated against typed | within 10 points |
| Multi-step plans correct | 90 percent, with every CONFIRM previewed |
| Latency, tiers 1 and 2 | under 50 ms |
| Latency, Jev from the client | median under 700 ms, 95th percentile under 1.5 s |
| Jev cost | under $0.15 per 1,000 Jev requests |
| Whole offline suite in CI | under 90 seconds |

## 15. Gates

- **GATE-CATALOGUE** (`tests/unit/core/test_command_catalogue.py`, plus `quill/tools/command_catalogue_audit.py` in `platform_report`):
  - Every registered command is a row, or is classified in `tests/unit/core/fixtures/command_catalogue.json` as `reviewed`, `unreviewed` (meaning NEVER) or `internal`. The `unreviewed` list may only shrink.
  - Senders, deleters, overwriters and exits must be CONFIRM or NEVER.
  - No CONFIRM or NEVER row has `agent_ok`.
  - Aliases are unique on a surface.
  - Every QUILL Lite row maps to a QUILL row (rule 10).
  - Every SAFE and CONFIRM row has a description and at least one example.
  - No catalogue row is a dictation phrase, and no dictation phrase is a catalogue alias.
- **GATE-CORPUS** (section 14.5).
- **GATE-CATREF:** `docs/command-catalogue.md` is generated and drift-gated.
- **Documentation chords and GATE-DOCKEY** read catalogue titles.
- **The engine boundary:** only the policy module may call `registry.run`, which a source test checks.
- **Existing gates that apply:**
  - menu accelerators, for F11, What Can I Say Here and Listening On or Off;
  - the bound-command gate, rules 8 and 11, including the Radio video window row;
  - GATE-14 access keys;
  - dialogs through `_show_modal_dialog`, with `bind_close_button`;
  - GATE-13 and GATE-BRAILLE;
  - F1 in every app;
  - GATE-REACH;
  - GATE-DPI;
  - GATE-DESCRIBE and GATE-KEYREF;
  - settings vocabulary and GATE-SETDOC, for `command_understanding`, `command_wake_phrase`, the listening switch, the hint-shown flag and multi-step preview;
  - GATE-LITE-COVER;
  - GATE-EC, for the codes in section 7.9;
  - network egress, for the rows in section 7.9;
  - GATE-11 module size: one catalogue module per app, and the editor side in a mixin (`main_frame_command_key.py`), never in `main_frame.py`;
  - the system-wide key checks (`show_hide_key_problem`), for the Command Key picker.

## 16. The attack layout

### 16.1 Phases at a glance

| Phase | What ships | Size | Depends on | Beside |
|---|---|---|---|---|
| 0 | Decisions only | small | none | none |
| 1 | Catalogue with examples, GATE-CATALOGUE, the fakes, the corpus format, the palette and Key Describer reading it | large | 0 | 6 |
| 2 | Typed F11 with tiers 1 and 2, policy, undo, preview, typed discoverability, the generated reference, for QUILL, QUILL Lite and Radio; about 2,500 corpus rows | medium to large | 1 | 3's gateway half, 6 |
| 3 | Jev: `/v1/decide`, the request builder, all section 7.3 questions, consent, caps, egress, error codes, the recorded suite; then Choose Your AI as tier 4 | large | 2 | 4, 6 |
| 4 | Speech: hold F11, the system-wide Command Key, the command phrase, targeting, the listening switch and privacy notice, spoken help and dictation help | large | 2 (and 3 for the best results) | 3, 6 |
| 5 | Rich commanding: arguments, multi-step, corrections, cross-app, "you can do that in..." | medium to large | 3, 4 | 6 |
| 6 | Command ids for Inkwell, Converter, Player, Beacon and Transcribe; Cast, Studio and Weather reviewed; their corpora | large, one PR per app | 1 | 2 to 5 |
| 7 | GitHub Workbench rows; push-to-talk retired into F11; Hey QUILL handing questions to Ask's conversation | medium | 4, 6 | none |

- **The first shippable phase is 2:** typed, offline, free, no account.
- **Jev arrives in phase 3,** behind its consent. A person who says no keeps phases 2 and 4 in full.
- **QUILL and QUILL Lite** get every phase in the same PR.

### 16.2 Phase 0: decisions

Jeff answers section 20. The plan of record moves to `docs/design/command-key.md`, with a progress log and its own remaining tasks.

**Go or no-go:** the key, the phrase, the catalogue shape and the Jev budget are agreed.

### 16.3 Phase 1: the catalogue (large)

- **PR 1a:**
  - the schema, with `examples` and `group`;
  - `set_command_probe`;
  - GATE-CATALOGUE, with everything `unreviewed`;
  - the corpus format and loader;
  - every fake in section 14.2.
- **PR 1b:**
  - the seed script;
  - QUILL, QUILL Lite and Radio rows reviewed, with examples;
  - `SAFE_TOOL_IDS` as a catalogue view, with a test that it is unchanged.
- **PR 1c:**
  - the palette, Key Describer and push-to-talk read the catalogue;
  - `COMMAND_ALIASES` and `_ALIASES` deleted;
  - `docs/command-catalogue.md` generated.
- **Tests:** the gate; palette golden rankings before and after; GATE-DESCRIBE; the agent allowlist.

**Go or no-go:** no palette search gets worse.

### 16.4 Phase 2: the typed key (medium to large, first shippable)

- **PR 2a:**
  - the resolver (tiers 1 and 2) and the local argument reader for numbers and durations;
  - the policy, the undo ring and the property tests in section 14.3.
- **PR 2b:**
  - the box, "Did you mean" and the confirmation;
  - the QUILL mixin, QUILL Lite's adapter (with no commands of its own, which a test checks) and Radio's adapter;
  - F11 in each app, with the Radio video window row;
  - Speak a Command moved out of the Dictation submenu.
- **PR 2c,** the typed half of discoverability:
  - the "what can I say here" list with groups, filter and examples;
  - What Can I Say Here on Ctrl+Alt+Shift+F1 in the three apps' Help menus;
  - the one-time hint;
  - "I can't do that here, but you can...";
  - GATE-CATREF.
- **PR 2d:** the 2,500-row corpus, the context-gating tests and GATE-CORPUS for the three apps. Blind testers' phrasings are collected before any tuning.

**Go or no-go:**

- the tier 1 and 2 targets in section 14.8 are met on the held-out set;
- two blind testers (JAWS and NVDA) use it for a week and don't find it chatty;
- there are zero property-test failures.

### 16.5 Phase 3: Jev (large)

- **PR 3a, on the gateway:**
  - `/v1/decide`;
  - the server copy of the request builder and catalogue versions;
  - the question sets;
  - the caps, the monthly ceiling, and the `limit_reached`, `no_credit` and `disabled` answers;
  - no body logging.
- **PR 3b, on the client:**
  - `jev_request.py`, shared with the gateway;
  - the Jev engine, the policy's Jev thresholds and the fan-out for large lists;
  - the consent and the `command_understanding` setting;
  - the egress rows and the error codes;
  - the own-key route.
- **PR 3c:** the recorded live suite, the cassettes and the nightly job.
- **PR 3d,** tier 4:
  - the gateway's `command_pick` template and `INSTRUCTIONS`;
  - `AiService` support, plus local Ollama and llama.cpp;
  - the fallback rules.
- **Tests:**
  - every section 7.3 question decides at least one test through `FakeJevClient`;
  - every failure code falls back as specified;
  - the property tests rerun with Jev answers generated at random.

**Go or no-go:**

- Jev meets its section 14.8 targets on the held-out set, with the model pinned;
- the measured cost per 1,000 requests is under target;
- TypeSafe's answers on retention and use are acceptable (section 17.6).

If not, Jev ships off by default, and tier 4 becomes the default assist.

### 16.6 Phase 4: speech, and the system-wide Command Key (large)

- **PR 4a, in the editors and Transcribe:**
  - hold F11 through `HoldToTalk` and the dictation controller;
  - F11 never changes dictation's state, which a test checks;
  - recogniser n-best and biasing, measured.
- **PR 4b:** Dictate Here into the box in Radio and Cast, then the other apps as phase 6 reaches them.
- **PR 4c:**
  - the system-wide Command Key, using Transcribe's `command_hotkey`;
  - the picker suggesting Ctrl+Alt+PageDown, after the screen-reader and Magnifier key check;
  - the migration line for anyone who already chose a key;
  - the `command` request kind and the targeting rules in section 9.7.
- **PR 4d:** the command phrase (`command_wake_phrase`, "Hey Quill") beside the unchanged "Quill dictate".
- **PR 4e:**
  - the shared Listening On or Off switch and the one privacy notice;
  - spoken help pages;
  - "what can I say while dictating".
- **Tests:**
  - the dictated and misheard corpus rows;
  - the separation tests in section 14.4;
  - targeting through `FakeRequestFile`;
  - the listening switch stops every listener.

**Go or no-go:** dictated within 10 points of typed; no dictation state change from F11 in any test; testers find the spoken help pages usable.

### 16.7 Phase 5: rich commanding (medium to large)

- **PR 5a:** arguments for time and date (`date_parse`), names, stations, episodes and files, all matched locally; closed sets through Jev `slot_` questions.
- **PR 5b:** multi-step plans, with preview, step-by-step checks and chain undo.
- **PR 5c:** corrections, with `last_offer`, the 30-second window and undo-then-redo.
- **PR 5d:** cross-app requests in the system-wide route, and the full section 11.5 pointers.
- **Tests:** the pattern rows from section 8, the payload-privacy property, and multi-step property tests.

**Go or no-go:** the multi-step and correction targets are met.

### 16.8 Phase 6: every app has ids (large, one PR per app, all parallel)

- **The new ids:** PR 6a Inkwell, 6b Converter, 6c Player (folding in `VoiceIntent`), 6d Beacon (replacing its own palette) and 6e Transcribe.
- **The review:** PR 6f reviews Cast, Studio and Weather.
- **What each PR does:**
  - registers its commands and moves its menus to `_menu_label`;
  - adds an `APP_KEYMAPS` entry, catalogue rows, examples and probes;
  - adds the box and What Can I Say Here;
  - adds its corpus of at least 800 rows.
- **When it starts:** as soon as PR 1a merges.

### 16.9 Phase 7: last pieces (medium)

- **PR 7a:** the GitHub Workbench rows.
- **PR 7b:** Voice Command (Offline) retired into F11, keeping its id as an alias.
- **PR 7c:** a question to "Hey Quill" can continue as an Ask conversation, with the person's consent, through Ask's existing voice mode.

### 16.10 Order and parallel work

- **The critical path** is 0, 1a, 1b, 2, 3 and 4. That gives typed and spoken commanding with Jev in QUILL, QUILL Lite and Radio.
- **Phase 6** runs beside everything from 1a, one app per person or agent.
- **The gateway half of phase 3** (PR 3a) can start during phase 2.
- **Phase 5** follows 3 and 4. Phase 7 comes last.

## 17. Costs

### 17.1 What is free

- **Free to everyone:** tiers 1 and 2, speech through the person's own dictation engine, local Ollama, the whole of phase 2, and everything when Jev is declined.
- **Choose Your AI:** the free hosted AI runs under the gateway's existing caps. Own keys, ChatGPT and Copilot are paid by their owners, as now.

### 17.2 Jev is not free

- **Price:** $42 per billion input tokens, which is $0.042 per million. Output tokens are free. `jev-1.14.0` and `jev-1.13.0` cost the same (docs.typesafe.ai, read 2026-11-07).
- **Prepaid credit.** Credit is bought in advance (Master Customer Agreement, typesafe.ai/legal/mca, section 8.2). It expires after 12 months, unused credit is not refunded, and requests stop when it runs out unless automatic refill is on.
- **No free tier was found.** Promotional credit is at TypeSafe's discretion.

### 17.3 Who pays

- **People using QUILL pay nothing,** and need no TypeSafe account.
- **Jeff pays,** through one Community Access TypeSafe account. The agreement (its section 2.2) allows building the API into our own applications for our users, and our gateway asks only its own fixed questions.
- **A person's own TypeSafe key** is optional, and that person pays for it.

### 17.4 Worked examples

A Jev request under this plan carries up to 60 candidates, each with a description and an example. That is about 2,000 to 3,000 input tokens, and the extra questions run against the same state for almost nothing more.

| What | At 2,000 tokens | At 3,000 tokens |
|---|---|---|
| One request | $0.000084 | $0.000126 |
| 1,000 requests | $0.084 | $0.126 |
| 1,000 people, 20 commands a day, all to Jev | $1.68 a day | $2.52 a day |
| The same, when tiers 1 and 2 settle 70 percent | $0.50 a day | $0.76 a day |
| That, for a 30-day month | $15.12 | $22.68 |

### 17.5 The cap

- **The daily cap.** It starts at 20,000 Jev requests a day, at most $2.52 a day or $75.60 a month at 3,000 tokens. Request 20,001 is refused, and the app falls back as in section 7.7.
- **The monthly ceiling** is a second guard, in dollars.
- **Both are server settings,** reviewed as use grows. 1,000 people at 20 Jev requests a day would reach the cap exactly.

### 17.6 Before phase 3 goes live

- [ ] Jeff has read the Master Customer Agreement. Still open: retention in days, named sub-processors, and whether the perpetual telemetry right can be narrowed in an order form.
- [ ] The acceptable use policy permits a consumer accessibility product.
- [ ] The price is checked again. TypeSafe have been asked about introductory pricing and nonprofit credit.
- [ ] The monthly ceiling is agreed, with automatic refill off or capped.
- [ ] The organisation's rate limits are known.
- [ ] The section 14.8 targets are met on the held-out set, with the model pinned.
- [ ] Turning Jev off on the server leaves every app working.

## 18. What Jev is, and what gent taught us

### 18.1 Jev

- **What it is.** TypeSafe's "System One" decision model. `POST https://api.typesafe.ai/v1/systemone`, with a bearer key.
- **Question types:** choice, score, noul and box.
- **Answers:** a probability for every option, and a confidence of `(p_max - 1/n) / (1 - 1/n)`.
- **Limits:** 255 options a choice, 64k tokens a request and 32k a question. Rate limits are per organisation; a 429 carries `retry-after`.
- **Models:** `jev-1.14.0` and `jev-1.13.0`, with moving aliases. Pin a version.
- **Advice from TypeSafe:**
  - a choice always picks something, so ask a companion yes or no "fits" question;
  - use parallel questions for arguments;
  - use speculative fan-out for big lists.
- **Privacy:** no training on input. Retention is "as long as reasonably necessary", and telemetry is kept "in perpetuity".

### 18.2 gent

gent is an NVDA add-on (github.com/Carrados/nvda-addons, GPL-2.0). You type "talk a bit faster" and NVDA does it, through a relay that holds the TypeSafe key, caps use and logs nothing. Its lessons:

- write each option as what the person wants;
- send the recent changes;
- act at 0.7 and ask below;
- treat a split between undo and the opposite of the last change as agreement;
- version the action table;
- send your own user agent, because Cloudflare blocks Python's default one.

Fourteen live phrases came back right in 0.3 to 0.6 seconds each. That is encouraging, and it is not evidence.

## 19. Risks

| Risk | What we do about it |
|---|---|
| Phase 6 is large | One PR per app, all parallel, each worth having for its palette alone |
| Mixing up commanding and dictating | Separate keys, phrases, tables and help; separation tests; a gate rule |
| A misheard sentence runs the wrong thing | Hold-to-talk, CONFIRM always asks, margins, n-best, corrections, undo |
| Jev's price or terms change | Caps, a ceiling, a server switch; tier 4 and the offline tiers carry on |
| Jev is wrong with confidence | Thresholds from the calibration table; a recorded suite on each new version; property tests make sure it can never reach outside the list |
| Personal data leaks into a request | Local name matching; a payload property test; no bodies logged |
| The catalogue rots | GATE-CATALOGUE and GATE-CORPUS; `unreviewed` is never offered |
| Chatty results or help | GATE-13 tests; paged help; testers before every go |
| A system-wide key steals another program's key | Opt-in only; the picker's family check; a screen-reader key check before phase 4 |
| Multi-step requests do too much | Three steps at most; a preview; re-checking before each step; chain undo |

## 20. Open decisions for Jeff

1. **The name.** *Recommendation:* "Say or Type a Command" for the menu and box; "the Command Key" for the key.
2. **The in-app key.** *Recommendation:* F11, commands only, everywhere, with Full Screen kept in Radio's video window.
3. **The system-wide Command Key.** *Recommendation:* Transcribe's Command Key setting, empty until chosen, with the picker suggesting Ctrl+Alt+PageDown (alternative Ctrl+Alt+PageUp).
4. **People who already chose a Transcribe Command Key.** *Recommendation:* keep their key, as the new Command Key, and tell them once.
5. **The keyboard way into dictation phrases.** *Recommendation:* "Next Phrase Is a Dictation Command" stays on dictation's side, with no key and a written reason. The command word does the job.
6. **The command phrase.** *Recommendation:* "Hey Quill" ("Oye Quill" in Spanish), off by default. "Quill do" is the alternative, with the risks in section 9.6.
7. **Jev as the default assist.** *Recommendation:* yes, once the person agrees in the section 7.8 question, with "my own AI" and "on this computer only" as equal choices. Never on without that answer.
8. **Jev's budget.** *Recommendation:* a daily cap of 20,000 requests and a monthly ceiling of $30 to start, reviewed monthly.
9. **Multi-step preview.** *Recommendation:* always preview at first. Let a person turn it off for chains of only SAFE steps.
10. **Remembering "Did you mean" picks as personal aliases** (local only). *Recommendation:* yes, with Forget My Command Words.
11. **The listening switch's key.** *Recommendation:* a menu row in every app and Transcribe's tray. No default key, with a written reason (rule 9: it is rarely used, and a system-wide key can be chosen).
12. **What Can I Say Here replacing What Can I Do Here in QUILL.** *Recommendation:* yes, keeping the same id and Ctrl+Alt+Shift+F1, and giving the row to every app.
13. **Sending favourites' names to Jev to match "play WNYC" better.** *Recommendation:* no. Match names locally, as planned.
14. **Quillins adding commands.** *Recommendation:* not until a reviewed manifest field exists.
15. **Push-to-talk Voice Command (Offline).** *Recommendation:* retire it into F11 in phase 7, keeping its id as an alias.

### 20.1 Decided, 2026-11-08

Every recommendation above was taken. None of Jeff's later words overrode one: "keys for commanding should be different then dictating" is decision 2 and 5, and "ways of asking 'what can I ask'" is decision 12.

1. The name: "Say or Type a Command" for the menu and box, "the Command Key" for the key.
2. F11, commands only, everywhere; Full Screen stays on F11 in Radio's video window.
3. The system-wide Command Key is Transcribe's Command Key setting, empty until chosen; the picker suggests Ctrl+Alt+PageDown, then Ctrl+Alt+PageUp.
4. Anyone who already chose a Transcribe Command Key keeps it as the new Command Key and is told once.
5. "Next Phrase Is a Dictation Command" stays on dictation's side, off F11. Amended in phase 2: it has a key, Ctrl+Alt+Shift+Q (Q for the command word), because the menu-accelerator rule allows no enabled row without one; it is nowhere near F11, which keeps the two apart as the decision intended.
6. "Hey Quill" ("Oye Quill"), off by default.
7. Jev is the default assist only after the person says yes to the section 7.8 question; "my own AI" and "on this computer only" are equal choices.
8. A daily cap of 20,000 Jev requests and a monthly ceiling of $30, reviewed monthly.
9. Multi-step requests always preview at first; a person may turn the preview off for chains of SAFE steps only.
10. "Did you mean" picks are remembered as personal aliases, on this computer only, with Forget My Command Words.
11. The listening switch is a menu row in every app and Transcribe's tray, with no default key (rule 9).
12. What Can I Say Here replaces What Can I Do Here in QUILL, keeping `help.what_can_i_do_here` and Ctrl+Alt+Shift+F1, and every app gets the row.
13. Favourites' names are never sent to Jev; names are matched on the computer.
14. Quillins cannot add catalogue rows until a reviewed manifest field exists.
15. Voice Command (Offline) retires into F11 in phase 7, keeping its id as an alias.

## 21. Remaining tasks

- [ ] Email TypeSafe: retention in days, sub-processors, order-form telemetry, acceptable use, price stability, nonprofit credit, and whether a number question type is planned.
- [ ] The section 14.2 fakes: each arrives with the phase that first uses it (the resolver's in phase 2, `FakeJevClient` and `FakeCommandPickEngine` in phase 3, `FakeRecognizer` and `FakeRequestFile` in phase 4).
- [ ] Review the 510 `unreviewed` QUILL and 84 Radio commands into rows; the list may only shrink.
- [ ] Add `tools.read_aloud_faster` and `tools.read_aloud_slower`, with keys, in both editors.
- [ ] Collect blind testers' phrasings for the held-out set before any tuning.
- [ ] Radio's Say or Type a Command is on Alt+F11, because Video > Full Screen holds F11 on the same menu bar. Move Full Screen to the video window's own keys so the player gets F11 too.
- [ ] Phase 2 follow-ups: the one-time hint as a family setting; Radio's own probes (playback commands while nothing plays); the corpus minimums raised to 20 typed rows a command as hand-written rows arrive; numbers and durations handed to the commands that take them (`run_with_args`) once each app exposes a way in.
- [ ] Phase 2 go or no-go with JAWS and NVDA testers.
- [ ] PR 3a: the relay's `/v1/decide`, caps, ceiling, out-of-credit answers. It goes on lp.csedesigns.com, which holds the TypeSafe key, not on Cloudflare (decided 2026-11-08); the client takes its base URL, so nothing in the apps changes.
- [ ] Phase 3 follow-ups: `command_understanding` as a real shared setting (settings vocabulary, GATE-SETDOC; it lives in `command-key.json` for now); tier 4 wired to `AiService.ask` once the gateway has a `command_pick` template and `own_key.py` its `INSTRUCTIONS` row; the recorded cassettes replayed in PR CI after a first live run; the speculative group fan-out for more than 60 candidates; `correction_pick`, `steps` and `slot_` questions (phase 5).
- [ ] Check Ctrl+Alt+PageDown and Ctrl+Alt+PageUp against JAWS, NVDA, Narrator, Magnifier, ZoomText and laptop utilities.
- [ ] PRs 4a to 4e: hold F11, Dictate Here into the box, the system-wide Command Key, "Hey Quill", the listening switch and privacy notice, spoken and dictation help.
- [ ] PRs 5a to 5d: arguments, multi-step, corrections, cross-app pointers.
- [ ] PRs 6a to 6f: ids, rows, examples, probes, box and corpus for every remaining app.
- [ ] PRs 7a to 7c: GitHub rows, push-to-talk retired, the hand-off to Ask's conversation.
- [ ] User guides for every app: one "Say or Type a Command" section in Jeff's voice, with lists generated from the catalogue.

## 22. Progress log

- **2026-11-08, phase 1 (the catalogue and its gate).** `quill/core/command_catalogue/` holds the rows: 68 for QUILL, which QUILL Lite reaches as 47 through `COMMAND_EQUIVALENTS`, and 37 for Radio. Every other command is `unreviewed` (NEVER) in `tests/unit/core/fixtures/command_catalogue.json`: 510 in QUILL and 84 in Radio. `CommandRegistry.set_command_probe` is the runtime half. `COMMAND_ALIASES` and `voice_commands._ALIASES` are gone, and `SAFE_TOOL_IDS` is the catalogue's `agent_ok` view, unchanged. The palette's alias words are all still found, apart from "search", which now leads to Find rather than Replace All. Key Describer falls back to the catalogue's title. GATE-CATALOGUE is `quill/tools/command_catalogue_audit.py`, on the platform report, and GATE-CATREF generates `docs/command-catalogue.md`. The corpus format and loader are `quill/core/command_catalogue/corpus.py`; the fakes arrive with the phases that use them.
- **2026-11-08, phase 2 (the typed Command Key).** F11 is Say or Type a Command in QUILL and QUILL Lite; Radio has it on Alt+F11 in its Help menu, because Video > Full Screen holds F11 on the same menu bar and wx cannot bind Ctrl+Grave, the 9.4 fallback. And What Can I Say Here (Ctrl+Alt+Shift+F1) replaces What Can I Do Here in QUILL, keeping its id and key, and is new in QUILL Lite and Radio's Help menus. Speak a Command is now Next Phrase Is a Dictation Command, on Ctrl+Alt+Shift+Q, in both editors and Transcribe (decision 5, amended: the menu rule needs a key on every enabled row). The wx-free pieces are `words.py` (normalising, a stemmer, synonyms, one typo in long words, checked against the written word as well as the stem), `args.py` (numbers, ordinals, durations, "a bit" and "a lot"), `resolver.py` (tier 1 word for word and on meaningful words, tier 2 as the harmonic mean of recall and precision, acting at 0.74 with a 0.15 margin), `policy.py` (the only code that runs a command for a sentence), `help_list.py` and `errors.py`. The windows are `quill/ui/command_key_ui.py`, and each app's four answers are `quill/ui/command_key_hosts.py`; a dimmed menu row is a command switched off here. The seed corpus (`tests/fixtures/command_key/`, generated by `generate_corpus.py`) has 2,129 rows: 631 of QUILL Lite's 637 positives act correctly, every disabled-here row is refused without a swap, and the misses left are two genuine ties that ask. Requests take 13 to 32 ms. The corpus found one real defect before shipping: with the right command switched off, tier 2 ran the next nearest one ("save all my documents" ran Save). Now a better-fitting command that is here but off, or NEVER, is refused with its reason. Two plan details changed: refusal lines read "Not from a sentence: it's in File, Exit." so they fit the 12-word limit in 14.6, and the one-time hint is remembered per app for now, not family-wide.
- **2026-11-08, phase 3 (Jev as the assist), the client half.** `jev_request.py` builds TypeSafe's `{model, state, questions}` request (the `fits` and `is_question` noul questions, the `action` choice with "none" over at most 60 candidates in tier 2's order, `size` when a stepped command is a candidate, `correction` when there is something to correct), pinned to `jev-1.14.0`, and refuses to build one that would carry a private word (`QUILL-AI-DECIDE-PRIVATE-DATA`). `jev.py` has the own-key route (the key from Windows Credential Manager, generic credential `QUILL TypeSafe dev key`), the gateway route (`/v1/decide`, which answers disabled until deployed), a three-second budget, `retry-after` honoured only within it, one request in flight, a day's stop after a limit, a spent credit or a switch-off, the section 7.9 codes, and section 7.5's reading of the answer with the 6.4 thresholds. `assist.py` is tier 3 (`JevAssist`, which says one line once on failure, then falls to tier 4) and tier 4 (`CommandPickAssist`, one question to the person's AI, which acts only when it agrees with tier 2 and the command is SAFE). The session asks an assist only what tiers 1 and 2 left open, never about a deliberate refusal. The consent question (7.8) is asked once, says TypeSafe keep requests and say they do not train on them, and offers Use Jev, Use My Own AI Instead and Match on This Computer Only as equal answers. Because the gateway is not deployed and the 16.5 go or no-go has not been met, Jev is offered only where a TypeSafe key is stored; for everyone else nothing changes. One egress row covers the call. The live suite, `tests/live/test_jev_live.py`, runs only with `QUILL_JEV_LIVE=1` and the stored key. It has not been run yet.
