"""The display rename must preserve installation and saved-data identities."""

from pathlib import Path

from quill.core.audio_studio.surface_help import is_known_title
from quill.core.runtime_apps import RUNTIME_APPS


def test_studio_display_name_keeps_launcher_identity():
    app = next(app for app in RUNTIME_APPS if app.ref_id == "studio")
    assert app.display == "QUILL Studio"
    assert app.module == "quill.apps.studio"
    assert app.launcher_exe == "QuillAudioStudio.exe"


def test_new_and_legacy_titles_keep_context_help():
    for name in ("QUILL Studio", "QUILL Audio Studio"):
        for suffix in ("", " (Safe Mode)", " Preferences"):
            assert is_known_title(name + suffix)


def test_installer_rename_preserves_upgrade_identity():
    root = Path(__file__).resolve().parents[3]
    text = (root / "standalone/studio/installer/quill-audio-studio.iss").read_text()
    assert '#define AppName "QUILL Studio"' in text
    assert "AppId={{64D6B5F9-01E3-47D5-B49F-794DFC0106BF}}" in text
    assert '#define AppRefId "studio"' in text
    assert 'Filename: "{app}\\QuillAudioStudio.exe"' in text
    assert "QUILL-Audio-Studio-Setup-Shared-{#AppVersion}" in text
    assert 'Name: "{group}\\QUILL Audio Studio.lnk"' in text
