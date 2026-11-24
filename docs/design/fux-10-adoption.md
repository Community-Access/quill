# FUX-10: help that explains the selected situation, app by app

**Date:** 2026-11-23
**Source:** FUX-10 in the family UX plan (`git show b7c6a1a04^:complete2.md`), held to [family-interaction-contracts.md](family-interaction-contracts.md). It is not one of the promoted pilots ([2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md), section 5), so the work here is limited to gaps in help the family already has. It adds no new help centre, panel, key or search.

## What the family already has

- **F1 everywhere.** Every app answers F1 through one engine, `quill/ui/app_context_help.py`. The answer is the window's purpose, from the app's gated catalogue (`surface_help.py`), then the focused control's help text or accessible name, then one sentence on how to drive that kind of control. QUILL's editor answers from `topics.json` (`ContextHelpMixin`), which `build_help_reference` publishes.
- **Reasons for greyed actions.** Radio and Cast put a reason on every dimmed row action (`quill/core/dimmed_reason.py`, `RowAction.reason`, `ResolvedAction.reason`), and a source scan fails any dimmed action without one (`tests/unit/ui/test_dimmed_action_reasons.py`). The context menu carries the reason as the item's help string, and the Quick Action keys say it when asked.
- **Command discovery.** What Can I Say Here (Ctrl+Alt+Shift+F1) and the Command Key in QUILL, QUILL Lite and Radio list what can be done now, and list the rest under "elsewhere" with the registry's reason (`CommandRegistry.unavailable_reason`).
- **The Workbenches** are the full model. F1 follows the selected node, Shift+F1 (What Can I Do Here?) lists every action for the selected row with "greyed:" and why, Alt+F1 explains the provider's word for the row, Shift+F9 (Explain That) explains the last result, Ctrl+Shift+F1 searches places, commands, words and tasks, and a task can be walked through step by step.

## The gap

Outside the Workbenches, F1 on a list or tree said only what the list is for. It said nothing about the row under the cursor. The reasons Radio and Cast had already written reached a person only through a context menu's help string, which most screen readers do not speak in a menu, and some help sentences were wrong for the row you were on (Radio's "Enter plays" on a folder or on the station already playing).

## The change, in the engine

`app_context_help.set_selection_help(control, describe)` lets a list or tree add a paragraph about its selected row to F1. *describe* runs only when F1 is pressed, never while someone arrows the list, so nothing is computed or spoken on selection (GATE-13). It answers "" when the list's own help already covers the row. The paragraph goes between the control's help and the role sentence, in the same help window, so nothing new opens and focus is not moved. The Workbench F1 composes through the same engine, so it gets the paragraph too.

## App by app

| App | F1, Shift+F1, What Is This, Explain That today | The gap | What changed |
| --- | --- | --- | --- |
| QUILL | F1 from `topics.json`; What Is This Document? describes the document and anything that will stop you; Command Key and What Can I Say Here list commands with the registry's reasons | A command the registry cannot explain is listed as "isn't available here right now" with no next step (`command_key_hosts._dimmed`) | Left: the reason must come from each command's own probe, which is the Command Key work's to add, command by command |
| QUILL Lite | As QUILL, through the shared engine and Lite's catalogue | As QUILL | Left, for the same reason |
| Radio | F1 is What Is This?; What Can I Say Here; Shift+F1 is the release notes | F1 on the Favorites tree said "Enter plays" on every row, including folders and the station already playing, and never mentioned a note or a station marked for move | F1 says what Enter does on this row, whether it is marked for move, and your note |
| Cast | F1 through the shell; no Shift+F1 | Every greyed episode and podcast action has a reason, but only the context menu's help string carried it. Pause Download was dimmed with no reason at all | F1 on the episode list says which menu items are unavailable for the selected episode or podcast, and why; Pause Download's menu item says why it is dimmed |
| Media Player | F1 through the shell | F1 on the Chapters tree already says what Enter does for both kinds of row (a seek, or the section's own file), and the status bar says which chapter is playing | None needed |
| Converter | F1 is Help for This Window; Shift+F1 is the release notes | The queue forgot each file's result after a run, so a row read the same whether it converted, failed or was skipped | F1 on a queue row says its last result; a folder row counts its files |
| Studio | F1 through the shell | The Library Window (Ctrl+Alt+Y) did not open at all: it imported a module that does not exist, then filled itself before the app knew its tree. Its tree said "Enter opens the selected book" on group rows too. The Chapter Workbench list's help was replaced by a second `SetHelpText`, so F1 never said that Enter plays the chapter | The window opens with your books; F1 on a group row says Enter opens nothing, and on a moved book says so; the Chapter Workbench list has one help text |
| Transcribe | F1 through the shell | Choose Model shows the selected model's readiness in a details box beside the list; Resume and Discard Held Words say in their help that they work while dictation is paused | None needed |
| Inkwell | F1 through the shell and its catalogue | The Abbreviations list marks an entry that is turned off, but F1 did not say that it will not expand or where to turn it back on | F1 on a disabled entry says both |
| Beacon | F1 through the shell; the results list has a details pane that follows the selection | Covered by the details pane. Beacon is not released yet, and `app.py` is over its size budget | None needed now |
| Social | F1 is Social's Keyboard Guide, from its own package; the shared engine only for the Scribe windows | Social keeps its own help model | Left: a change belongs with Social's own help work |
| Weather | F1 through the shell; every list has a detail field beside it that follows the selection | Covered by the detail fields | None needed |
| GitHub and WordPress Workbenches | The full model above | Search Help matches a command only by its label, so a word from its description does not find it | Left: the Workbench frame work is active in those files, and tasks and glossary entries already match on their own words |

## Acceptance

- **A disabled action has a readable reason and next step:** Radio and Cast rows, the Workbenches already. QUILL and Lite commands without a probe are left, as above.
- **Existing users keep menu paths and command identities:** no menu, key or command id changes.
- **Search matches intent and synonyms:** unchanged; see the Workbench row.
- **Context help knows the state:** F1 now reads the selected row's state where a list has one.
- **Help does not interrupt reading:** F1 is still a window the person opens; nothing is said on selection.
- **A short explanation expands to a worked example:** each F1 window keeps its Open User Guide button where the topic names a section.
