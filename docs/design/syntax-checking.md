# Check This File: syntax checking in both editors

Status: shipped 2026-11-06. This note is the record
of what was built, how each checker is run, and the security model the user
approved. The user guide (QUILL chapter 6, "Checking a file for problems";
QUILL Lite chapter 4, "Navigate > Code") is the reader's version.

## What the user gets

- **Check This File...** (`Ctrl+Alt+/`, Navigate > Code) checks the whole
  document and reports every problem a checker can find, each with a line, a
  column, a severity (error, warning or info) and a message. With problems it
  opens the **Problems** list, one row per problem, place first; Enter goes to
  the one chosen. With none it says "No problems found."
- **Next Problem** (`Ctrl+Alt+.`) and **Previous Problem** (`Ctrl+Alt+,`) move
  the caret to the next or previous problem and say "Problem 2 of 5, line 12,
  column 5, error: ...". They wrap, and they check again whenever the text has
  changed since the last check.
- QUILL checks every language below. QUILL Lite checks Markdown and HTML, the
  two languages it knows, with the built-in checkers only, and never starts an
  outside tool. That keeps Lite level with QUILL, not ahead (family rule 10).

### Why these keys

A code editor's own are F8 and Shift+F8. Both are taken in both editors by
Word's extend-selection pair (Start Selection and Complete Selection), which
family rule 1 keeps. The problem keys take the shape of Compare's
`Ctrl+Alt+Shift+.` and `Ctrl+Alt+Shift+,` with one modifier fewer, and Check
This File sits on the question-mark key beside them. All three were free in
both editors. They are in `menu_lint._CTRL_ALT_DOCUMENTED` with the AltGr cost
stated: on a few layouts AltGr with comma or period types a character.

## Code

| Module | Job |
| --- | --- |
| `quill/core/problems/model.py` | `Problem`, `CheckReport`, the sentences, offsets, Next/Previous |
| `quill/core/problems/builtin.py` | Tier 1, built-in checkers |
| `quill/core/problems/outside.py` | Tiers 2 and 3: the allowlist, runner and parsers |
| `quill/core/problems/registry.py` | `language_key`, `check_document`, the one call both editors make |
| `quill/ui/problems_commands.py` | The shared commands, over editor hooks |
| `quill/ui/main_frame_code_nav.py` | QUILL's Navigate > Code |
| `quill/apps/lite_window_code_nav.py` | QUILL Lite's Navigate > Code |

Checkers are keyed by language: the language profile's name in lower case,
refined by file name (`.jsonc` and VS Code's settings files are JSONC; an
`.xhtml` file is checked as XML and as HTML).

## Tier 1: built in

No outside tool and no new dependency.

| Language | Checker | Finds |
| --- | --- | --- |
| JSON | `json` | The first parse error |
| JSONC | comments and trailing commas blanked, positions kept, then `json` | The first parse error; an unclosed comment |
| XML | `quill.core.safe_xml` (defusedxml) | The first well-formedness error; entity declarations are refused |
| HTML | `html.parser` subclass | Every unclosed and mismatched tag (optional end tags and void elements allowed), closing tags with nothing open, duplicate ids, `img` without `alt` |
| TOML | `tomllib` | The first parse error |
| YAML | PyYAML `safe_load_all`, when importable (it arrives with the speech packages) | The first parse error |
| Python | `compile(..., "exec")`, warnings recorded | Syntax errors, compile-time errors, `SyntaxWarning`s. The code object is discarded; nothing runs |
| INI, CFG | `configparser` (strict, no interpolation) | Missing section header, duplicate sections and options, every unparsable line |
| CSV, TSV | `csv` (strict), delimiter sniffed | Ragged rows (up to 200) and quote errors |
| Markdown | GLOW's heading-jump and image-alt rules, plus link checks | Heading skips, images without alt, empty links, relative links to missing files |

pyflakes is not a dependency, so undefined names in Python come from Ruff when
it is installed (tier 3). The repository has no `.reg`, PowerShell or SQL
parser to reuse, so those languages have no checker.

## Tiers 2 and 3: tools the user already has

Tier 2 is JavaScript through Node.js; tier 3 is everything else. They share one
mechanism and one allowlist, `CHECKER_TOOLS` in `quill/core/problems/outside.py`.

| Tool | Languages | Arguments | Parser |
| --- | --- | --- | --- |
| `node` | JavaScript | `--check FILE` | `file:line` header, caret column, `SyntaxError: message` |
| `tsc` | TypeScript | `--noEmit --pretty false FILE` | `file(line,col): error TS1234: message` |
| `eslint` | JavaScript, TypeScript | `--format json FILE` | ESLint JSON results |
| `ruff` | Python | `check --output-format json --no-cache FILE` | Ruff JSON; syntax and undefined-name codes are errors, the rest warnings |
| `php` | PHP | `-l FILE` | `Parse error: message in FILE on line N` |
| `ruby` | Ruby | `-c FILE` | `file:line: message`, or Prism's framed source with a caret |
| `perl` | Perl | `-c FILE` | `message at FILE line N, near "..."` |
| `shellcheck` | Shell | `-f gcc FILE` | gcc style |
| `gcc` | C, C++ | `-fsyntax-only FILE` | gcc style |
| `clang` | C, C++ | `-fsyntax-only FILE` | gcc style (runs only when gcc is not found) |
| `gofmt` | Go | `-e -l FILE` | gcc style without severity |
| `rustc` | Rust | `--error-format=json --emit=metadata --out-dir TEMP FILE` | rustc JSON diagnostics, primary span |
| `csc` | C# | `-nologo -target:library -out:TEMP/check.dll FILE` | `file(line,col): error CS1234: message` |
| `xmllint` | XML | `--noout FILE` | `file:line: parser error : message`, caret column |

Notes per tool:

- **go vet** needs a module, so the single-file check is `gofmt -e`.
- **rustc** has no stable no-codegen switch; `--emit=metadata` into a throwaway
  folder is the cheapest stable equivalent.
- **dotnet build** checks C# only as part of a project. `csc` checks one file;
  without it the user hears "No checker installed for C#" with that reason.
- **eslint** loads the project's own configuration, which is JavaScript, and
  **perl -c** runs the file's `BEGIN` blocks and `use` statements. The guide
  says so in plain words.
- A tool that exits with an error and no output the parser understands (an
  ESLint with no configuration, say) is reported as "eslint could not check
  this file: <its first line>" rather than silently passing.

## Security model

Approved by the user on 2026-11-06. CLAUDE.md records it as the
"Syntax-checker allowlist" invariant.

- **A fixed, frozen allowlist.** `CHECKER_TOOLS` is a `MappingProxyType`; each
  entry is an executable name, fixed arguments and a parser. Nothing from the
  document or from settings reaches the argument list except the file path.
  `tests/unit/core/test_problems_outside.py` freezes the table, so a new
  executable or a changed argument is a deliberate change in two places.
- **Not the external-engine allowlist.** `_ENGINE_EXECUTABLE_BASENAMES` in
  `quill/core/ai/external_engine.py` answers a different question (which AI
  engine processes may be configured) and was not widened; a test checks that.
- **Found, never fetched.** Tools are found with `shutil.which` only. Nothing is
  downloaded or installed. A missing tool is a sentence, not a prompt.
- **Run safely.** Every run goes through
  `quill.stability.safe_subprocess.run_subprocess_safely`: an argv list, no
  shell, a 15-second timeout, output decoded as UTF-8, the environment
  unchanged, and the working directory set to the file's own folder (or the
  temporary folder for an untitled document).
- **What is checked is what is on screen.** A saved, unchanged file is checked
  in place. An unsaved or modified one is written to a temporary copy with the
  same name in a fresh temporary folder, which is deleted afterwards; the copy's
  path is replaced by the file name in every message.
- **Off the UI thread.** When a language has an outside tool, QUILL runs the
  check on its task manager and says "Checking this file"; the built-in tier is
  fast enough to run inline. QUILL Lite runs no outside tools at all.
- **Local only, so no egress entry.** The checkers start local processes and
  open no network connection. The network egress audit
  (`quill/tools/network_egress_audit.py`) inventories outbound network calls,
  and this feature adds none, so it has no row there. (A tool the user has
  installed could itself go online, as it would from a terminal; QUILL passes
  no option that asks it to.)

## Tests

- `tests/unit/core/test_problems_builtin.py`: every built-in checker against
  small good and bad samples, including that `compile` runs nothing.
- `tests/unit/core/test_problems_outside.py`: the frozen allowlist; every parser
  against output captured from the real tool (node, ruff, php, perl, gofmt and
  rustc were captured on this machine; the others from their documented
  formats); the runner's temporary copy, working directory, timeout and missing
  tools, with a fake `which` and `run`. No test needs a tool installed.
- `tests/unit/core/test_problems_model.py`: offsets, wrap-around, the sentences.
- `tests/unit/ui/test_main_frame_code_nav.py` and
  `tests/unit/apps/test_lite_code_nav.py`: the commands in each editor.

## The Problems pane

Since 2026-11-08, View > Problems Pane docks the same problems under the
editor in both editors, and `problems_pane_visible` remembers it. Check This
File fills the pane instead of opening the modal list while it is shown.
Since P2, the pane also checks again after a save and, when its Check after a
pause box (`problems_check_after_pause`) is checked, after 1.5 seconds without
typing; those checks say only a changed count. The
widget is `quill/ui/problems_pane.py`, its filters and sentences are
`quill/core/problems/pane.py`, and the plan for what feeds it next (open
files, a check after a pause, language servers) is `docs/design/intellisense.md`.

## Possible later work

- A language server client would give problems as you type. It is a much larger
  surface (a long-running process per language, a protocol) and was not part
  of this change.
- A setting to turn the outside tools off, if anybody wants the built-in tier
  only in QUILL.
