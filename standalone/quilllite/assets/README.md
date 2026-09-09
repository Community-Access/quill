# QuillLite assets

- `quill-lite.ico` — the app and installer icon, referenced by
  `quill-lite.spec`, `installer/quilllite.iss` and
  `installer/quilllite-lite.iss`.

**Generated — do not edit by hand.** The icon comes from
`scripts/build_app_icons.py`, which owns the design system for the whole
QuillVille family. To change it, change the `_quilllite` glyph there and re-run:

```powershell
python scripts/build_app_icons.py
```

`tests/unit/scripts/test_app_icons.py` fails if a committed `.ico` drifts from
what the generator produces, if two apps render the same face, or if a new app
ships an installer with no icon entry — the seam that once let four apps ship
byte-identical copies of Quill Radio's icon.

The glyph is a white page with a folded corner and two amber lines of writing,
on a forest-green tile. Every other glyph in the family is round, pointed, or
built from bars, so this is the only one that blurs to a rectangle with a bite
out of it — which is the test that matters, because the other one is 16×16 in a
taskbar. Two lines of writing, not four: four merged into a grey block at that
size.
