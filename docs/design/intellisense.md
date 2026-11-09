# IntelliSense on a key press, for QUILL and QUILL Lite

Written 2026-11-08 for Jeff to review. Accepted the same day; being built in the phase order below.

## The short version

- Suggestions appear only when you press the key, never on their own. Typing "as you type" stays an opt-in setting, off by default.
- QUILL already has the start of this: **Edit > Word Prediction...** on **Ctrl+.** suggests words and Markdown or HTML tags. QUILL Lite has nothing yet.
- The plan grows that one command into real code completion in four layers, from no new dependencies to optional language servers. Each layer only adds better suggestions to the same list on the same key.
- **The first useful layer needs no new dependency at all.** QUILL already ships Pygments, which can split over 500 languages into names, keywords and strings.

## What exists today

- `quill/core/intellisense.py` (135 lines): words from the spelling dictionary and the document, plus Markdown and HTML tag choices.
- `quill/ui/main_frame_intellisense.py`: the suggestion list. `_show_intellisense_popup(manual=True)` is the key-press path.
- `edit.word_prediction` on Ctrl+. (`keymap.py` line 753). It lives in QUILL's Edit menu.
- The setting `intellisense_as_you_type`, off by default, with a View menu toggle.
- The feature `core.intellisense` is off in two profiles and on but quiet in the rest. In an off profile, Ctrl+. says "Word prediction is unavailable in this profile".
- Pygments (`pygments>=2.21.0`) is already a dependency, used by spell checking to lex code (`quill/core/spellcheck_lexers.py`).
- Navigate > Code and Check This File exist (`quill/core/problems/`), with an allowlist of outside tools (`CHECKER_TOOLS`) that run only if they're installed.

## Do we need a language parser?

Not to start. It depends how smart the suggestions should be.

| Layer | What it knows | New dependency | Size |
|---|---|---|---|
| 1. Names in this file | every name, keyword and string in the file, for its language | none (Pygments is shipped) | small |
| 2. Names across the project | the same across open files and the project folder | none | small |
| 3. Structure | which names are in scope here, functions and their parameters, members after a dot | tree-sitter and its grammars, or Jedi for Python | medium |
| 4. Full language smarts | types, imports, documentation, signatures, the same as VS Code | a language server per language | large |

### Layer 1: names in this file

- Pygments identifies the language and splits the file into tokens. The list offers the names and keywords that start with what you've typed, nearest first.
- Works for every language Pygments knows, offline and instantly.
- Not smart about scope: it can offer a name that isn't usable at that spot.

### Layer 2: names across the project

- The same, over open documents and the project folder, with a size cap and a background index on the task manager.
- Prefers names from the current file, then from files it imports, then the rest.

### Layer 3: structure

Two candidates, and the plan recommends trying the first:

- **tree-sitter** (`tree-sitter` plus `tree-sitter-language-pack`, both MIT and published as Windows wheels). A real parser for about 160 languages. It gives scopes, function signatures, members after a dot, and the outline. Roughly 30 to 60 MB of grammars, which go in the shared runtime under the bundle-everything rule. It would also improve Navigate > Code.
- **Jedi** (MIT, pure Python, about 5 MB), for Python only. It gives real Python completions, signatures and docstrings. Small and well proven, but one language.

### Layer 4: language servers

- A generic Language Server Protocol client, the protocol VS Code uses, talking to servers such as Pyright (Python), typescript-language-server (JavaScript and TypeScript), clangd (C and C++), rust-analyzer, gopls (Go) and OmniSharp (C#).
- This is the same kind of decision as Check This File's outside tools: a fixed allowlist, run only if installed, through `safe_subprocess`, local only, no network. Widening that allowlist needs your approval, as it did on 2026-11-06.
- Correction: the shared runtime does not carry a general Node. The Copilot tools it ships are a self-contained bundle. Embedding the Microsoft servers below means bundling Node itself, about 30 MB.

### Embedding the Microsoft language tools, as VS Code does (Jeff, 2026-11-08)

VS Code's language smarts come from separate language servers. Some are open source and can be embedded; some are licensed only for Microsoft's own products and cannot. To check before bundling: each licence below is from memory and must be read from the package itself.

| Language | What VS Code uses | Can QUILL embed it? | Instead |
|---|---|---|---|
| JavaScript, TypeScript | the TypeScript language service (`tsserver`, in the `typescript` package) | yes, open source (Apache 2.0) | wrapped by `typescript-language-server` (MIT) |
| HTML, CSS, JSON, Markdown | VS Code's own servers, from the VS Code repository | yes, open source (MIT), published together as `vscode-langservers-extracted` | |
| Python | Pylance | **no**: its licence allows only Microsoft's VS Code products | **Pyright**, the open-source engine inside Pylance (MIT) |
| C and C++ | the C/C++ extension's engine | **no**: licensed for VS Code only | **clangd** (LLVM, Apache 2.0) |
| C# | the C# extension and C# Dev Kit | Dev Kit **no**; the Roslyn language server needs its licence checked | OmniSharp (MIT) |
| PowerShell | PowerShell Editor Services | yes, open source (MIT); needs PowerShell, which Windows has | |
| XML | Red Hat's LemMinX | yes (Eclipse Public License); needs Java or its native build | |

**What embedding would take:**
- **A Language Server Protocol client** in `quill/core`, talking over the server's standard input and output, with no network: completions, signature help, hover documentation, go to definition and problems.
- **Node bundled in the shared runtime,** pinned and hash-checked like Pandoc, for TypeScript, the VS Code HTML, CSS, JSON and Markdown servers, and Pyright. That's about 30 MB for Node, plus roughly 15 to 40 MB of servers, all to be measured.
- **clangd as its own download** (about 30 MB) if C and C++ matter. Otherwise it's run only if it's installed.
- **An allowlist entry for each server,** like Check This File's `CHECKER_TOOLS`: fixed arguments, run through `safe_subprocess`, local only. You approve the list.
- **Licence notices** in `THIRD-PARTY-NOTICES.txt`, and the bundled-component inventory.
- **The same screen-reader experience as layers 1 to 3,** fed by the server: the count, the kind, the signature, documentation in the details field, and parameter hints. Problems from the server feed Navigate > Code and Check This File.
- **Start each server on first use,** not at launch, and stop it when the last file of that language closes, so it costs nothing until you press Ctrl+..

**Recommendation:** embed in this order: (1) the VS Code HTML, CSS, JSON and Markdown servers, which are small, the ones writers most use, and the same as VS Code's; (2) TypeScript and JavaScript; (3) Pyright for Python. Use clangd and PowerShell only if they're installed. Never Pylance or the C/C++ extension's engine.

## How it works for someone using a screen reader

- **Press Ctrl+.** In a code file you hear the count and the first suggestion with its kind, for example "8 suggestions. count, function, 2 parameters." In prose, it stays word prediction.
- **Up and Down** move through the list. Each item says its name and kind, and its signature or a one-line description where the layer has one. Tab or Enter inserts it. Escape closes the list and leaves the text untouched.
- **A details field**, reached with a key, holds the full documentation for the selected item, where layer 3 or 4 has it.
- **Parameter hints on their own key** (proposed Ctrl+Shift+. ): inside a call's brackets, it says which parameter you're on, "parameter 2 of 3, seconds". This needs layer 3.
- **Nothing is announced that the screen reader already says** (GATE-13), and everything spoken is also brailled (GATE-BRAILLE).
- **No sound or speech while typing** unless "as you type" is turned on.

## Keys

- **Ctrl+.** stays the one key for suggestions, in both editors (rule 2: the command both products have keeps the chord). It's free in QUILL Lite.
- **Ctrl+Shift+.** for parameter hints, if it's free in both keymaps. To be checked.
- Ctrl+Space stays with the sentence commands, as `keymap.py` records.

## QUILL Lite

- The suggestion list moves out of `main_frame_intellisense.py` into a shared module, so both editors run one implementation (the way the GitHub account flow was shared).
- Lite gets **Edit > Word Prediction...** on Ctrl+., with the same layers, at the same time as QUILL. QUILL Lite may never be ahead of QUILL.

## A Problems pane, in QUILL and QUILL Lite (Jeff, 2026-11-08)

### What exists today
- Both editors already share `quill/ui/problems_commands.py`. **Check This File** (Ctrl+Alt+/) checks the document and opens a **Problems list**, one row per problem with the line and column first. **Next Problem** (Ctrl+Alt+.) and **Previous Problem** (Ctrl+Alt+,) walk them without the list.
- The list is a modal window. It closes when you pick a problem, so it can't stay open while you fix things.
- QUILL already docks a pane below the editor, Reveal Codes (`quill/ui/reveal_codes_pane.py`), and F6 moves between regions. That's the pattern to follow.

### What the pane would be
- A **Problems pane docked below the editor,** like VS Code's, that stays open while you work. It's a list, one row per problem: severity, line and column, the message, and where it came from (built-in checker, outside tool, language server, spelling, accessibility check).
- **F6** reaches it, as it reaches the other regions, and **Escape** returns to the editor without closing it. Enter on a row goes to that place in the text and puts focus there.
- **It updates after each check,** never while you're typing. The checks run when you save, when you ask, or after a pause you choose (off by default). When the count changes while you're in the editor, it says one short sentence, such as "3 problems", and nothing more (GATE-13). Always brailled too (GATE-BRAILLE).
- **Filters:** errors only, this file or all open files, and by source. A filter row heads the pane, so Tab reaches it.
- **Every source feeds it:** Check This File's built-in checkers and outside tools today, the language servers in layer 4, and in time the accessibility check (GLOW), the Forms check and spelling. Each source writes the one problem model, `quill/core/problems/model.py`, so the pane never needs to know which tool spoke.
- **A context menu on each row:** Go To, Copy Message, Explain (the server's documentation, or the AI if one is chosen) and, where a server offers one, Quick Fix.
- **Show or hide it** from View > Problems Pane in both editors. Ctrl+Shift+M, VS Code's key, is taken by Set Mark in both editors, so the plan proposes no chord at first (rule 9, with a written reason), or one checked free in both keymaps.
- The modal Problems list stays for people who prefer it. Check This File opens the pane instead when the pane is shown.

### Phases
| Phase | What ships | Size |
|---|---|---|
| P1 | the pane in both editors over today's checkers: docked, F6, filters, Go To, live count | medium |
| P2 | all open files, and checking after a pause (off by default) | small |
| P3 | language server problems and Quick Fix, with layer 4 | medium |
| P4 | accessibility, Forms and spelling problems in the same pane | medium |

P1 needs no new dependency and can ship before any of the IntelliSense layers.

### Decisions
7. **Build the pane?** Recommendation: yes, P1 first.
8. **Its key:** none at first, or a chord checked free in both editors? Recommendation: check the free chords, and use View > Problems Pane until one is agreed.
9. **Check after a pause while typing?** Recommendation: off by default, a setting to turn on, and never an announcement until the count changes.

## Phases

| Phase | What ships | New dependency | Size |
|---|---|---|---|
| 0 | your decisions below | none | small |
| 1 | the shared list in both editors, Lite gets Ctrl+., key-press only in every profile | none | small |
| 2 | layer 1, code names in this file, with kinds announced | none | small |
| 3 | layer 2, project-wide names, background index | none | medium |
| 4 | layer 3, tree-sitter, or Jedi for Python, plus parameter hints | tree-sitter wheels, or Jedi | medium |
| 5 | layer 4, the language server client with a fixed allowlist | none bundled; servers only if installed | large |

Each phase is its own PR, with behavioural tests (Lite command coverage), the menu and access key gates, F1 help, both user guides and the changelogs.

## Tests

- A corpus of small files per language with the cursor at known spots and the expected suggestions.
- Speed budgets: the list appears within 100 ms for layers 1 to 3 on a 1 MB file, measured the way GATE-PERF measures (never under `tracemalloc`).
- Announcement tests: the count, the first item and kind, and nothing repeated.
- Property tests: Escape never changes the text; inserting a suggestion replaces only the fragment typed.

## Decisions for you

**Accepted, 2026-11-08.** Jeff accepted every recommendation, decisions 1 to 9, in his words: "i agree with all assumptions, go and start this as well". That acceptance also approves the layer 4 server allowlist for the named servers only (the VS Code HTML, CSS, JSON and Markdown servers, typescript-language-server with typescript, and Pyright; clangd and PowerShell Editor Services only if already installed). Each network download of Node or a server, and each new Python dependency, is still asked about first.

Measured 2026-11-08: no chord near Ctrl+Shift+M is free in both editors, so the Problems pane ships with no chord (rule 9, reason recorded in the bound-command gate). Ctrl+Shift+. is taken in both editors too, so parameter hints need a different key when phase 4 or the servers arrive.

1. **Key-press only in every profile,** including the two where word prediction is off today? Recommendation: yes. A list you have to ask for can't get in anyone's way.
2. **How far to go:** stop at layer 2 (no new dependency), or continue to layer 3? Recommendation: build phases 1 to 3 now, then decide on layer 3 once you've used it.
3. **tree-sitter or Jedi for layer 3?** Recommendation: tree-sitter, because it covers every language and also improves Navigate > Code, at the cost of 30 to 60 MB in the shared runtime.
4. **Embed Microsoft's open-source language servers (layer 4)?** Recommendation: yes, in the order in the embedding section: the VS Code HTML, CSS, JSON and Markdown servers, then TypeScript, then Pyright. This means bundling Node (about 30 MB). Never Pylance or the C/C++ engine, whose licences forbid it.
5. **Parameter hints on Ctrl+Shift+.** if it's free in both editors? Recommendation: yes.
6. **Language servers before or after tree-sitter?** Recommendation: servers first for the languages they cover, since they're better than a parser there, and tree-sitter later for the long tail of other languages.

**Further decisions, 2026-11-08 (Jeff):** download and bundle Node 24.22.1, the servers and ripgrep ("get all language servers completed"); TypeScript 6.0.3 with typescript-language-server now, TypeScript 7's native server later ("ok, make it so"); built-in quick-fix rules, widened to the common linters' fixable rules, each family switchable ("do what you feel is best"); a formatter: Prettier 3.9.10 bundled beside the servers, and ruff format, black, clang-format, gofmt and rustfmt allowed when installed ("yes"); a way to get each unbundled tool from Settings ("provide ways for users to get these tools inside of settings"), and rich formatting settings ("make rich settings so users can chose"). The switches live in one window, Code Checks and Fixes.

## Progress

- 2026-11-08: Problems pane P1 in both editors (PR #1798): docked, F6, Show and Source filters, Go To with a re-check after edits, the count sentence; no chord (rule 9).
- 2026-11-08: Phase 1. The suggestion list moved into `quill/ui/suggestion_list.py`; QUILL's `main_frame_intellisense.py` is its adapter and QUILL Lite's is `quill/apps/lite_window_word_prediction.py` (Edit > Word Prediction..., Ctrl+.). The key works in every QUILL profile; "as you type" stays off by default and still follows the profile.
- 2026-11-08: Phase 2, layer 1. `quill/core/code_names.py`: in a code file (any extension Pygments knows, prose excluded) the list offers the file's own names nearest first, with kinds. `str.find` over a lower-cased copy finds the names, a definition-word check at each occurrence gives function or class, and Pygments reads only 2,500 characters either side of the caret for the other kinds. Lexing the whole file was measured at about 1.5 s per 600 KB, so it is never done. Under 100 ms on 1 MB of QUILL's own code, best of five, in the perf test; one-letter fragments look 100,000 characters either side.
- 2026-11-08: Problems pane P2, first half. While shown, the pane re-checks quietly after a save and, with its Check after a pause box (`problems_check_after_pause`, off by default, both editors), after 1.5 s of stillness; only a changed count is said. All open files is the second half, still to do.
- 2026-11-08: Phase 3, layer 2. `quill/core/project_names.py` indexes the project (nearest folder with `.git`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `.sln` or `composer.json`, else the document's folder) on the task manager in both editors, with one index per root shared by every window. Caps: 5,000 files, 1 MB a file, 40 MB in all; dependency, build and hidden folders skipped. Ranking after this file's names: same case, then names from imported files, then defined names. On this machine the walk of `quill/core` (1,773 files) took about 25 s, almost all of it in `open()` (antivirus); that is the case for ripgrep in the layer 4 phase.
- 2026-11-08: Problems pane P2, second half. The Files chooser (this file, All open files) lists every open document's problems through `combine_reports`, the others checked with the built-in checkers only; Enter on another document brings it forward. P2 is complete.

## Remaining tasks

- [ ] Problems pane P3 and P4 (P1 is PR #1798, P2 PRs #1804 and this one).
- [ ] Read the licence of each server package before bundling it (TypeScript, vscode-langservers-extracted, Pyright, the Roslyn language server).
- [ ] Measure Node plus the servers in the shared runtime.
- [ ] Layer 4 phase: bundle ripgrep (`rg.exe`, about 5 MB) beside Node in the shared runtime, pinned and SHA-256 checked like Pandoc. Read its licence (MIT or Unlicense) from the release first, record it in THIRD-PARTY-NOTICES and the component inventory, and add a network-audit note that it is local only. Layer 2's project index uses it when present and falls back to the pure-Python walk. Ask Jeff before the first download (parent session, 2026-11-08, with Jeff's go-ahead).
- [ ] Choose a key for parameter hints: Ctrl+Shift+. is taken in both editors (measured 2026-11-08).
- [ ] Measure the tree-sitter grammar size for the languages we care about, before phase 4.
- [ ] Screen-reader checks with JAWS and NVDA for each phase, added to `docs/qa/screen-reader-checks-2026-10.md`.
