# QUILL Transcribe assets

- `quill-transcribe.ico` — the app/installer icon (referenced by
  `quill-transcribe.spec` and `installer/quill-transcribe.iss`).

**Generated — do not edit by hand.** The icon comes from
`scripts/build_app_icons.py`, which owns the design system for the whole
QuillVille family. To change it, change the `_transcribe` glyph there and re-run:

```powershell
python scripts/build_app_icons.py
```

The glyph is a text caret with words arriving at it: speech becoming text
where the cursor is. The tall caret is the one upright, serifed silhouette in
the family.
