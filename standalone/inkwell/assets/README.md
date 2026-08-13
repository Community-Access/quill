# Quill Inkwell assets

- `quill-inkwell.ico` — the app/installer icon (referenced by
  `quill-inkwell.spec` and `installer/quill-inkwell.iss`).

**Generated — do not edit by hand.** The icon comes from
`scripts/build_app_icons.py`, which owns the design system for the whole
QuillVille family. To change it, change the `_inkwell` glyph there and re-run:

```powershell
python scripts/build_app_icons.py
```

Until 2026-08-13 this file was a byte-identical copy of Quill Weather's icon,
which was itself a copy of Quill Radio's — three apps wearing a fourth app's
face in the taskbar. The generator exists so that cannot happen again.

The glyph is a nib dipped into an inkwell: the app is named for the well, and
the pot is a silhouette nothing else in the family has. Two alternatives were
drawn and rejected because they failed at 16×16, which is the size that
actually matters — expanding text lines blurred to a grey block, and a bare
fountain nib read as a flame.
