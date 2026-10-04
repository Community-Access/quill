# Finding Settings in Preferences

Status: implemented in source; not yet released. Manual NVDA, JAWS, and
Narrator acceptance remains outstanding.

## Keyboard Workflow

Open the app's existing Preferences or Settings window. The added **Find a
setting** field searches visible labels, accessible names, and authored help
text. Search words are matched without regard to case, and all words must occur
in a result's description. Field values are never searched.

1. Type a setting name or a term from its help.
2. Press Down to move into Matching settings.
3. Use the arrows to choose a result, then Enter to focus that setting.
4. Change the setting using its normal control. Search does not change it.
5. Use the existing OK/Apply or Cancel action when finished.

Control+F returns to search from elsewhere in the window. Enter in search or
the matches navigates, rather than accepting the entire dialog. Escape in search
clears a nonempty query first; with an empty query it retains the window's
ordinary close/cancel behavior. A disabled result stays disabled and is not
activated. No-results feedback is available in the count beside the results.
Callers with an announcement channel receive a debounced count announcement.

Choosing a setting on another notebook/book page reveals that page. Beacon's
custom section panels follow the same rule. Search never presses action buttons;
it puts keyboard focus on them. Standard control names and native focus changes
are left to the screen reader rather than announced twice.

## Where else search reaches

* **Windows built one part at a time.** QUILL Cast's Preferences shows one
  section at a time, so a search over what is on screen could only find the
  section showing. It searches every section; choosing a match shows its
  section and focuses the setting.
* **Apps whose settings are menu options.** Quill Converter, Quill Media
  Player and Quill Inkwell have no settings window. **Help > Find a Setting or
  Command** (Ctrl+Alt+Shift+S) searches every menu row; Enter does the row as
  its menu would, and an option says whether it is now on or off.
* **Settings shown as a web form.** A form made of switches and choices, such
  as GLOW Accessibility, gets a Find a setting box at the top; Enter moves to
  the first match. With a screen reader running the same form is native and
  gets the ordinary search.

## Current Coverage

- QUILL: the Preferences category hub and native Settings/Preferences dialogs
  shown through the shared dialog contract. Hub search finds categories and
  their descriptions; it does not index controls in unopened nested dialogs.
- QUILL Lite: its actual Preferences fields, including recovery, appearance,
  announcements, and feedback settings.
- Quill Radio, QUILL Cast, and Audio Studio: their shared companion Preferences
  dialog, including choices, checkboxes, text settings, and action buttons.
- Weather: its native Weather Settings dialog.
- Beacon: its Preferences hub and Settings windows using its existing local
  dialog setup, including navigation to hidden section panels.
- Sanctioned modeless Settings/Preferences windows: installed through the
  shared modeless show path; cleanup occurs on destruction.

Converter, Player, and Inkwell do not currently expose a unified Preferences
window. A complete family-wide Preferences entry point for those apps is still
required; this feature does not invent or duplicate their existing settings.
Accessible web forms are also outside the native wx control index.

## Privacy and Lifetime

Matching reads labels, accessible names, and help text only. It never indexes
passwords, API keys, document text, or any other field value. Search makes no
network calls and has no separate persistence store.

Search is installed once per surface. Its count timer stops when a modal closes
or its surface is destroyed. Child destruction alone does not invalidate the
whole window. Reopening a retained surface reactivates its search owner.

## Verification

Automated tests exercise actual wx notebook pages, native fields, companion
Preferences controls, Lite's constructed Preferences, Beacon's hidden Sync
panel, value preservation, disabled results, cancellation, and count suppression
after close. The broader Preferences/dialog suite passed 67 tests before the
modeless follow-up; the final search/dialog-contract check passed 29 tests.

Before release, manually verify typing, Tab order, result counts, Enter,
Escape, and focus return with NVDA, JAWS, and Narrator. Also complete the three
missing app entry points and web-form coverage before claiming all-app search.