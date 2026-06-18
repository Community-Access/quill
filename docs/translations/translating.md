# Translating QUILL

QUILL uses GNU gettext catalogs and a GitHub pull-request workflow for
translations. You do not need a Crowdin account, special access, or programming
knowledge — if you can edit a text file and open a pull request, you can
contribute a translation.

---

## Quick start

1. Fork the repository on GitHub.
2. Copy `quill/locale/quill.pot` as your starting point.
3. Create the file `quill/locale/{lang}/LC_MESSAGES/quill.po`
   (for example `quill/locale/fr/LC_MESSAGES/quill.po` for French).
4. Fill in the `msgstr` values with your translations.
5. Run the validator locally (see below).
6. Open a pull request using the **Translation PR template**.

That is the complete workflow. No accounts, no queues, no approvals before you
can start.

---

## Step-by-step guide

### 1. Fork and clone

```
git clone https://github.com/<your-username>/quill.git
cd quill
pip install -e ".[ui,dev]"
```

### 2. Create your .po file from the template

```
mkdir -p quill/locale/fr/LC_MESSAGES
cp quill/locale/quill.pot quill/locale/fr/LC_MESSAGES/quill.po
```

Replace `fr` with your language code (POSIX locale tag: `de`, `es`, `pt_BR`,
`zh_CN`, etc.).

Edit the header block at the top of your `.po` file:

```po
msgid ""
msgstr ""
"Project-Id-Version: QUILL 0.6.0\n"
"Language: fr\n"
"Language-Team: French\n"
"Last-Translator: Your Name <email@example.com>\n"
"Plural-Forms: nplurals=2; plural=(n > 1);\n"
"Content-Type: text/plain; charset=UTF-8\n"
```

Set `Plural-Forms` to match your language's plural rules. See the reference at
https://www.gnu.org/software/gettext/manual/html_node/Plural-forms.html.

### 3. Translate

For each entry in the file, fill in the `msgstr` value:

```po
#: quill/ui/main_frame_menu.py:42
msgid "&File"
msgstr "&Fichier"
```

Leave `msgstr ""` for strings you have not translated yet. Those strings will
fall back to English at runtime. A partial translation that covers the menus
and common dialogs is more useful than no translation at all.

### 4. Validate locally

```
python -m quill.tools.check_translation
```

Fix any errors before opening your pull request. The CI gate runs the same
check and will block merge if errors are present.

### 5. Compile and test in the running app

```
pybabel compile -d quill/locale -D quill
python -m quill
```

Open QUILL Settings and set **Language** to your language code. Navigate the
menus and dialogs to verify your translations appear and sound natural.

Pay particular attention to:
- Menu mnemonics (the underlined shortcut letters — check the **Mnemonic `&`**
  rules below).
- Announcement strings — what your screen reader says during actions.
- Plural forms — "1 word" vs "3 words".

### 6. Regenerate the HTML and EPUB artifacts

If you modify `translating.md` itself as part of your contribution, regenerate
the HTML and EPUB:

```
pandoc docs/translations/translating.md -o docs/translations/translating.html
pandoc docs/translations/translating.md -o docs/translations/translating.epub
```

### 7. Open a pull request

Use the **Translation** PR template (select it in the GitHub PR creation
interface). Add the label `translation` to your PR.

---

## Coverage thresholds

- **90%** for an established language (one that has shipped in a previous release).
- **70%** for a new language in its first release.

Languages below threshold are shown in the language selector with a warning
rather than being hidden, so users who prefer even a partial translation can
still choose it.

If your language misses a release, it can catch up and ship in the next one.

---

## Keeping your translation current

When new strings are added to QUILL, the `.pot` file is regenerated. To merge
new strings into your `.po` file without losing your existing work:

```
pybabel update -d quill/locale -D quill -i quill/locale/quill.pot
```

New strings appear with empty `msgstr ""`. Strings that were changed in English
are marked `#, fuzzy` — review these and clear the `fuzzy` flag when done.

---

## Regenerating the .pot template (maintainers)

When source strings change, regenerate the template and commit it:

```
pybabel extract \
  -F babel.cfg \
  -k _ \
  -k "ngettext:1,2" \
  -k lazy_gettext \
  --project "QUILL" \
  --version "0.6.0" \
  --copyright-holder "Blind Information Technology Solutions (BITS) and Community Access" \
  --msgid-bugs-address "https://github.com/Community-Access/quill/issues" \
  -o quill/locale/quill.pot \
  .
```

Commit `quill/locale/quill.pot` whenever source strings are added or changed.
Translators update their `.po` files from the new `.pot` before the next
release.

---

## The QUILL product glossary

The following terms are QUILL product names. Your language team decides whether
to translate them or leave them in English. Record the decision in your `.po`
file as a translator comment so future contributors apply it consistently.

| Term | Notes |
|---|---|
| Copy Tray | QUILL's multi-slot clipboard feature |
| Ask Quill | The AI assistant dialog |
| Quillin | A QUILL extension |
| Quick Nav | The rapid in-document navigation mode |
| Skill Library | The library of AI-powered writing skill packs |
| Prompt Library | The library of saved AI prompts |
| GLOW | QUILL's guided-learning workflow system |

---

## Translator credit

Translator names appear in the QUILL release notes for each release in which
their work ships. If you would prefer to be listed by a username, set that in
your PR description.

---

## Questions and help

Open a GitHub issue with the label `translation`. Aim to respond within three
business days.

---

# Style guide

## Tone and register

QUILL speaks to the user in the second person, directly. Use "your document",
"press this key", not "the user's document" or "one presses this key."

Match the register of the target language's screen reader ecosystem:
- French: use "vous" (formal) unless the French-language community explicitly
  votes for "tu". Record the decision as a translator comment.
- German: use "Sie" (formal) by default.
- For other languages, follow the convention used by NVDA's official
  translation into your language.

## Mnemonic markers (`&`)

A mnemonic marker is the `&` character before one letter in a menu item or
button label. It creates a keyboard shortcut: Alt plus that letter activates
the item. Screen reader users rely on mnemonics to navigate menus without
arrow keys.

Rules:
1. Every menu item and button label has exactly one `&`.
2. Your translation must also contain exactly one `&`.
3. Place the `&` before a letter that is unique within the same menu or dialog.
4. The `&` letter must appear in your translated word.

The CI gate catches missing or extra `&` markers automatically.

## Keyboard shortcuts

Modifier key names are not translated:

- Ctrl, Alt, Shift, Enter, Escape, Tab, F1–F12

A string like `&Open...\tCtrl+O` should become (in French)
`&Ouvrir...\tCtrl+O`. The `\t` accelerator keeps `Ctrl+O`; only the label's
`&` mnemonic is yours to relocate.

## Announcement strings (speech strings)

Announcement strings are marked with a `# SPEECH:` comment in the `.pot`
file:

```po
#. SPEECH: announced after copy-to-tray action
msgid "Copied to slot {n}"
```

Rules for announcement strings:
1. Translate for natural speech, not literal label equivalence.
2. Do not abbreviate. Spell out acronyms unless they are universally known in
   your language's technology community.
3. Add spoken context if the meaning would be lost without visual UI.
4. Test every announcement string with a screen reader set to your language.

## Plural forms

Follow your language's actual plural rules. Reference:
https://www.gnu.org/software/gettext/manual/html_node/Plural-forms.html

The `Plural-Forms` header in your `.po` file must match your language's rules.
The CI gate checks that every `msgstr[n]` entry exists.

## Placeholders

Placeholders are variable values QUILL inserts at runtime:
- `{name}` — Python format string: `{count}`, `{filename}`
- `%(name)s` — Old-style: `%(count)s`, `%(provider)s`

Rules:
1. Never translate a placeholder. `{n}` remains `{n}` in every language.
2. Never remove a placeholder.
3. You may reorder placeholders to match your language's grammar.

The CI gate checks placeholder preservation.

## Technical identifiers — do not translate

- File extensions: `.qpf`, `.sqp`, `.po`, `.pot`, `.mo`
- Setting key names: `language`, `setup_wizard_completed`
- URL paths and domain names
- ARIA role names: `button`, `dialog`, `listbox`, `menu`, `menuitem`

---

# Appendix: i18n status for 0.6.0

**What is complete:**
- `quill/locale/quill.pot` — extraction template, regenerated from source.
- `quill/core/i18n.py` — runtime `_()` loader; falls back to the English
  string when no `.mo` is present, so the app runs without translations.
- All user-facing strings in `quill/ui/` and key `quill/core/` modules are
  wrapped with `_()`, `ngettext()`, or `lazy_gettext()`.
- `python -m quill.tools.check_translation` validates `.po` files on every PR.
- Translation PR template in `.github/PULL_REQUEST_TEMPLATE/translation.md`.

**What is not done yet:**
- No language-specific `.po` / `.mo` files ship with 0.6.0. The product ships
  English-only with the full translation infrastructure in place.
- A few low-priority internal modules (diagnostic output, developer console
  strings) still have unwrapped strings. These are not user-facing in normal
  operation.

**For the first translator:**
Start from `quill/locale/quill.pot`. Create
`quill/locale/{lang}/LC_MESSAGES/quill.po` following the Quick start above.
Open a pull request with the translation PR template.

**Future: translation portal**
When translation volume grows, QUILL may add Weblate or Crowdin as a
browser-based alternative while keeping gettext catalogs as the source format.
The PR workflow remains available at all times.
