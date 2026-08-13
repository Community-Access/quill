# Quill Weather assets

- `quill-weather.ico` — the app/installer icon (referenced by
  `quill-weather.spec` and `installer/quill-weather.iss`).

**Generated — do not edit by hand.** The icon comes from
`scripts/build_app_icons.py`, which owns the design system for the whole
QuillVille family. To change it, change the `_weather` glyph there and re-run:

```powershell
python scripts/build_app_icons.py
```

Until 2026-08-13 this file was a byte-identical copy of Quill Radio's icon.
The generator exists so a new app cannot inherit somebody else's face again.

The glyph is a sun behind a cloud — the one glyph in the family that is a
picture of a thing rather than a diagram, because weather is the one app whose
subject is a thing.
