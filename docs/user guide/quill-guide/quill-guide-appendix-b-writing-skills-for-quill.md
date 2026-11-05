# Appendix B: Writing skills for QUILL

This appendix shows you how to write, check and share your own skills. A skill
lives in a `.sqp` file (Skill Quill Pack). It is a multi-step AI workflow,
written in plain Markdown. If you can write a prompt, you can write a skill.

## What a skill is

A QUILL prompt is one instruction. A skill is a short conversation: a series of
instructions, where each step can see what the step before it produced.

A skill is the right tool when:

- You want to analyse your text first, then act on what the analysis found.
- You want to gather information in one step and write with it in the next.
- You want to check something (is this a question or a statement?) and go a
  different way depending on the answer.
- You want a better result on the same task, by giving the model context it
  built for itself in an earlier step.

## Your first skill

Create a file called `my-first-skill.sqp` and open it in QUILL. Type this in:

````markdown
---
schema: quill.skill/1
name: Explain Then Simplify
description: Explains the selected text in plain terms, then simplifies it further.
author: Your Name
version: 1.0.0
---

# Step 1: Explain

Explain the following text as if the reader has no prior knowledge. Use simple
vocabulary and short sentences. Aim for 50-80 words.

Text to explain:
{selection}

# Step 2: Simplify further

The explanation below is good, but we need it even simpler. Rewrite it so a
twelve-year-old would understand it immediately. Keep the core meaning.

Explanation to simplify:
{step1.output}

```output
format: text
label: Plain-language explanation
accept_into: clipboard
```
````

The part between the two `---` lines is the front matter: the skill's name and
details. Each line that starts with `# Step` begins a new step. `{selection}`
is your selected text, and `{step1.output}` is whatever step 1 produced.

Save the file, then check it with the validator:

```powershell
python -m quill.tools.sqp_validator my-first-skill.sqp
```

If all is well, you will see:

```
my-first-skill.sqp: OK
```

## Adding parameters

Parameters let the person running the skill choose options first. Before step 1
begins, QUILL shows a small dialog that asks for those choices.

Here is the same skill with a choice of reading level added:

````markdown
---
schema: quill.skill/1
name: Explain Then Simplify
description: Explains and simplifies selected text at a chosen reading level.
author: Your Name
version: 1.0.0
parameters:
  - name: level
    label: Target reading level
    type: choice
    choices: [Grade 4, Grade 6, Grade 8]
    default: Grade 6
---

# Step 1: Explain

Explain the following text so it is accessible at {parameters.level} reading level.
Use simple vocabulary and short sentences. Aim for 50-80 words.

Text to explain:
{selection}

# Step 2: Simplify further

Rewrite the explanation below to be even clearer. Target: {parameters.level}.
Keep the core meaning intact.

{step1.output}

```output
format: text
label: Plain-language explanation
accept_into: clipboard
```
````

Now `{parameters.level}` can be used in both steps. Its value is whatever the
user picked in the dialog.

There are five kinds of parameter:

| Type | UI control | Example |
| --- | --- | --- |
| `text` | Single-line text field | A keyword or name |
| `multiline` | Multi-line text area | A block of context |
| `choice` | Drop-down list | Reading level, tone, language |
| `bool` | Checkbox | Include citations: yes/no |
| `number` | Numeric field | Word count target |

## Using the input block

A long piece of text can bury the instruction it belongs to. The `input` block
adds the data after the instruction, so the step stays easy to read:

````markdown
# Step 1: Extract key claims

Read the following document and list the five most important claims it makes.
Number each claim. One sentence per claim.

```input
{document}
```
````

Without the `input` block you would write:

```markdown
# Step 1: Extract key claims

Read the following document and list the five most important claims it makes.
Number each claim. One sentence per claim.

Document:
{document}
```

Both do the same thing. The `input` block is just tidier when the data is long.

## Branching on an answer

A `condition` block sends the skill down one path or another, depending on what
a step produced.

````markdown
# Step 1: Detect intent

Read the following text. Is it asking a question, or making a statement?
Answer with exactly one word: "question" or "statement".

```input
{selection}
```

```condition
if: "{step1.output}" contains "question"
then: step2
else: step3
```

# Step 2: Answer the question

Answer this question clearly and concisely:
{selection}

```output
format: text
label: Answer
accept_into: clipboard
```

# Step 3: Expand the statement

Expand the following statement into a full paragraph with supporting detail:
{selection}

```output
format: text
label: Expanded statement
accept_into: clipboard
```
````

Here is what happens. After step 1 runs, QUILL checks the condition. If the
output contains "question", it jumps to step 2. Otherwise it jumps to step 3.
Whichever step runs last is the one that produces the result.

You can use these operators in a condition:

| Operator | Matches when |
| --- | --- |
| `contains` | Subject contains value (case-insensitive) |
| `equals` | Subject exactly matches value (case-insensitive) |
| `starts_with` | Subject starts with value |
| `ends_with` | Subject ends with value |
| `length_gt` | Subject length > number |
| `length_lt` | Subject length < number |
| `is_empty` | Subject is blank |

## Controlling the output

The `output` block on the last step decides what happens to the result.

````markdown
```output
format: text
label: Rewritten paragraph
accept_into: selection
```
````

It has three settings:

- `format`: `text` (the default), `list` (the AI should return a bulleted or
  numbered list), or `json` (the AI should return valid JSON).
- `accept_into`: what happens when the user presses Accept in the result
  dialog. `selection` replaces the current selection in the editor.
  `clipboard` copies the result to the clipboard. `none` just shows it,
  read-only (this is the default).
- `label`: the heading of the result dialog, so the user knows what they are
  reviewing.

## A complete example, Accessible Rewrite

Here is the "Accessible Rewrite" skill that comes with QUILL, in full.

````markdown
---
schema: quill.skill/1
name: Accessible Rewrite
description: Rewrites selected text for plain-language accessibility.
author: QUILL Project
version: 1.0.0
parameters:
  - name: reading_level
    label: Target reading level
    type: choice
    choices: [Grade 6, Grade 8, Grade 10, No target]
    default: Grade 8
---

# Step 1: Analyse accessibility issues

Review the following text for plain-language accessibility issues. List the
problems as a numbered list. Focus on: sentence length (over 25 words), passive
voice, unexplained jargon or acronyms, abstract nouns where concrete ones would
serve better, and complex nested clauses. Be concise — one clear problem per
line. If the text has no issues, say "No issues found."

```input
{selection}
```

# Step 2: Rewrite for accessibility

Rewrite the text below to fix the issues identified in Step 1. Requirements:
- Target reading level: {parameters.reading_level}
- Preserve all factual content
- Do not add new information

Original text:
{selection}

Issues to fix:
{step1.output}

```output
format: text
label: Rewritten text
accept_into: selection
```
````

Step 1 reads the text and makes a numbered list of problems. Step 2 gets that
list through `{step1.output}`, along with the original text, so the model knows
exactly what to fix. When the user presses Accept, the rewrite replaces the
selection.

## Checking your skill

Always run the validator before you share a skill:

```powershell
python -m quill.tools.sqp_validator my-skill.sqp
```

For a stricter check:

```powershell
python -m quill.tools.sqp_validator my-skill.sqp --strict
```

With `--strict`, it also warns you if `description` or `author` is missing.

These are the errors people meet most, and how to fix them:

| Error | Cause | Fix |
| --- | --- | --- |
| `schema must be 'quill.skill/1'` | Missing or wrong schema | Add `schema: quill.skill/1` to front matter |
| `front matter must include 'name'` | No `name:` field | Add `name: My Skill` |
| `must have at least one step` | No `# Heading` lines | Add at least one `# Step N:` heading |
| `{step3.output} references a step that hasn't run yet` | Forward reference | Steps can only reference outputs from earlier steps |
| `unknown parameter 'tone'` | Used `{parameters.tone}` but didn't declare it | Add `tone` to the `parameters` list in front matter |
| `output format 'xml' is invalid` | Bad `format:` value | Use `text`, `list`, or `json` |

## Sharing skills

A `.sqp` file is plain text, so you can share it the same way you share any
document. There are three ways it reaches other people:

- Through the Skill Library. Whoever receives your `.sqp` file imports it with
  **AI > AI Library...** (on the AI menu once **Show advanced AI features**
  is checked there): choose the Skills tab, then **Import .sqp**.
- Through a Quillin. If you look after a Quillin, put your `.sqp` files in the
  Quillin's folder. QUILL finds them on its own when the Skill Library loads.
- As a file on its own. A `.sqp` file holds everything it needs. Anyone can also
  open it in QUILL's editor to read it, understand it and change any step.

## Tips for writing good skills

- Be specific in each step. "List the five most important claims" works better
  than "What are the claims?" The model follows precise wording.
- Say exactly what you want back. Instead of "Summarise the following", write
  "Write a one-sentence summary of the following text. Return only the summary
  sentence, no preamble." Then `{step1.output}` holds just what you expect.
- Try it on short text first. Type two or three sentences into the editor,
  select them, and run the skill. Short text runs faster, and mistakes are
  easier to track down.
- Put long data in an `input` block. If the selection might be a whole
  document, put `{document}` in an `input` block instead of in the middle of
  the prompt. The step reads more cleanly.
- Give a branch its own detection step. If you are branching on whether the
  text is a question, a statement, a list or something else, let step 1 do only
  that sorting, and ask for a one-word answer. The tighter the answer, the more
  reliably the condition works.
- Choose `accept_into` on purpose. If the skill rewrites the selection, use
  `accept_into: selection`. If it makes something extra (a meeting summary, an
  outline), use `accept_into: clipboard`, so the user can paste it where they
  like. Use `none` for skills that only inform you (a grammar analysis, a
  readability score), where you read the result but do not insert it.

## Reference card

### Front matter fields

| Field | Required | Default |
| --- | --- | --- |
| `schema: quill.skill/1` | yes | none |
| `name: ...` | yes | none |
| `description: ...` | recommended | `""` |
| `author: ...` | recommended | `""` |
| `version: ...` | no | `1.0.0` |
| `parameters: [...]` | no | `[]` |

### Variables

| Variable | Value |
| --- | --- |
| `{selection}` | Selected editor text (full document if nothing selected) |
| `{document}` | Full document text |
| `{title}` | Document title |
| `{clipboard}` | Clipboard text at skill-start time |
| `{stepN.output}` | Output from step N (must be a lower-numbered step) |
| `{parameters.name}` | Value of a declared parameter |

### Fenced block types

| Block | Where | Purpose |
| --- | --- | --- |
| `` `input` `` | Any step | Appends data to the prompt |
| `` `condition` `` | Any step | Branch to `then`/`else` step after this step runs |
| `` `output` `` | Last step | Controls format, label, accept_into |
| `` `use-prompt` `` | Any step | Delegates to a named Prompt Library prompt |

### Values at a glance

- Condition operators: `contains`, `equals`, `starts_with`, `ends_with`,
  `length_gt`, `length_lt`, `is_empty`.
- Output formats: `text`, `list`, `json`.
- Output accept_into values: `selection`, `clipboard`, `none`.

## Where to go next

Open the Skill Library from the **AI** menu and run one of the skills that come
with QUILL, then open its `.sqp` file and see how it was put together. Chapter
10, AI, when you want it, covers the rest of the assistant.

---

- Previous: [Appendix A: The QUILL Developer Console](quill-guide-appendix-a-quill-developer-console.html)
- Next: [Appendix C: Every emoji QUILL can insert](quill-guide-appendix-c-every-emoji-quill-can-insert.html)
- [Contents](../userguide.html)
