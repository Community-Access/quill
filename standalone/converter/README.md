# Quill Converter

An accessible, screen-reader-first **audio format converter** as its own
standalone Windows app. Convert audio (and pull the audio track out of video)
between MP3, M4A/M4B, Opus, Ogg, FLAC, WAV, AAC, and more — with presets and a
full Advanced DSP catalog — entirely on your machine through the bundled FFmpeg.

The application itself lives in the [`quill`](https://github.com/Community-Access/quill)
package (`quill.apps.converter`) and runs the exact same wx-free conversion
engine QUILL and Audio Studio use. This folder is only the **product wrapper**:
the launcher entry point, the tile icon, and the build/installer plumbing.

## Run from source

```
run-quill-converter.bat
```

or, with a checkout that has `quill` installed:

```
python -m quill.apps.converter
```

Pass one or more file paths to queue them immediately (this is what the Windows
Explorer "Convert with Quill" right-click entry does):

```
python -m quill.apps.converter song.wav album\
```

## Build

The portable bundle and the native launcher (with the `quill-converter.ico`
tile icon) are produced by the shared QuillVille builder:

```
python standalone/studio/scripts/build_portable.py --product converter \
    --out standalone/converter/dist/QuillConverter \
    --source-root . --ffmpeg-dir <vetted ffmpeg dir> --version 1.0.0
```

`quill-converter.spec` is the PyInstaller onedir spec (legacy path, preserved
like the sibling apps); the released launcher is the native QuillVille C
launcher, which spawns `pythonw.exe -m quill.apps.converter`.

The tile icon is generated (and regenerable) from
`assets/make_quill_converter_icon.py`.

## License

MIT. The bundled FFmpeg keeps its own license; the app never bundles yt-dlp
(URL import installs it on demand, with a one-time consent + rights notice).
