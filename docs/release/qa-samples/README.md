# QUILL QA sample-document corpus

Small, purpose-built input documents for **manual** release QA. Each file has
**known, fixed content** so "correct" is unambiguous: a tester opens the file in
QUILL, runs the referenced journey, and compares what QUILL says and writes
against the expected structure below.

These files are for **manual QA only** — they are inputs a human opens by hand
while following `qa-core-journeys.md` and the master sign-off pack. They are not
fixtures for the automated suite and nothing here is asserted by CI.

Keep every file byte-stable: the journeys quote exact counts, cell contents,
alt text, and screen-reader wording, so editing a sample silently invalidates the
"Expected" fields that depend on it.

| File | Features / journeys it exercises | Expected structure / outcome |
| --- | --- | --- |
| `formatting.md` | Heading navigation (QUILL Next/Previous Heading and the screen reader's `H` / `Shift+H`); bold/italic/underline/strikethrough; ordered and unordered lists; blockquote; inline + fenced code; link; image alt; Save-As fidelity; Find/Replace + Regex Helper; Read Aloud | Six headings, one of each level **H1–H6** in order (`H`/Next Heading reaches all six); the words **bold**, *italic*, underlined `underline` (via `<u>`), and struck `strike`; one unordered list (Apples/Oranges/Pears) and one ordered list (First/Second/Third); one blockquote ("The quick brown fox…"); inline code `print("hello")` and one fenced `python` code block; one link labelled **QUILL project**; one image with alt **"Red circle"** |
| `table.md` | Table cell navigation (`Ctrl+Alt+Arrows`); pipe-escaping in a cell; Save-As table fidelity | One caption sentence above a **3-column** table with a header row (Region/Device/Notes) and **3 body rows**; the South row's Device cell contains the literal pipe **`Phone \| Watch`** (must stay one cell, not split); last cell is East/Laptop/Backordered so the "end of table" edge is reachable |
| `math.md` | Insert Equation (inline vs block); math reading (Read this part aloud / MathCAT); MathML round-trip | Two inline equations in `\(...\)` — `E = mc^2` and `a^2 + b^2 = c^2`; one block equation in `$$...$$` — `\int_0^1 x^2 \, dx = \frac{1}{3}` (equals one third); one `<math>` MathML block stating x = 1/2 |
| `reading-order.txt` | Improve Reading Order AI journey; provider-confirm prompt; wording preserved | A four-step tea recipe printed **out of order** with one step broken across a mid-sentence line break; the file also states the intended correct order (steps First→Second→Third→Fourth). After the AI runs, a **new unsaved** document should read the four steps in order with the **same wording** |
| `plain.txt` | Baseline open / read / Save-As round-trip | Three plain paragraphs, no markup; text that comes back out of a Save-As must match character for character |
| `sample.html` | HTML import; Paste HTML as Markdown | An HTML doc with one `h1` ("Trip Checklist"), a paragraph, a 3-item unordered list, a 2-column table (Day/City) with two body rows, one link labelled **QUILL project**, and one `<img>` with alt **"Red circle"** |
| `compare-original.txt` and `compare-revised.txt` | Compare tools (`tools.compare_*`) in the Acceptance Test Book | A known before/after pair with **exactly three differences**: line 2 changes **March → April**; line 3 gains **"and performance"**; the revised file adds a fourth line **"A follow-up review is scheduled for February."** Compare must report these three and nothing else |
| `data.csv` | CSV / Table Studio (`tools.csv_studio`) and Calculator document stats | A 3-column CSV (Region/Units/Revenue) with **4 data rows** (North/South/East/West). Known totals: **Units = 465**, **Revenue = 9300**; row count 4, column count 3 |
| `encoding-cp1252.txt` | Choose Encoding (`file.choose_encoding`) | Text saved in **Windows-1252**, not UTF-8: `Café résumé — naïve façade. Prices in £ and €.` Opened as UTF-8 it shows mojibake; re-reading as **Windows-1252** restores the accents and currency symbols correctly |
| `line-endings-crlf.txt` | Toggle Line Endings (`file.toggle_line_endings`) | Three lines (`Line one` / `Line two` / `Line three`) terminated with **Windows CRLF** (`\r\n`). QUILL should report CRLF; toggling to LF and saving rewrites the endings |

## Notes for the tester

- Paths quoted in the journeys are relative to this folder
  (`docs/release/qa-samples/`). Copy the whole folder onto the machine under test.
- `red-circle.png` is referenced by `formatting.md` and `sample.html` only as an
  image **reference** — the alt text is what QA checks, so the binary image file
  is not required for any journey to pass (a broken-image placeholder with the
  correct alt is the expected non-blocking outcome).
- The last four rows above (`compare-*`, `data.csv`, `encoding-cp1252.txt`,
  `line-endings-crlf.txt`) back specific scenarios in the **Acceptance Test Book**
  (`../acceptance/`). `encoding-cp1252.txt` and `line-endings-crlf.txt` are
  **byte-specific** — copy them as-is; do not open and re-save them in an editor
  that would rewrite the encoding or the line endings, or the scenario they support
  becomes untestable.
- If you must edit a sample, update the matching "Expected" cell here **and** the
  affected step in `qa-core-journeys.md` (and `../acceptance/`) in the same change.
