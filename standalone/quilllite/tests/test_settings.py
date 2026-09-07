import json

from quilllite import settings as settings_mod


def test_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    s = settings_mod.Settings(theme="system", font_size=14)
    s.remember_recent("C:/a.txt")
    s.remember_recent("C:/b.txt")
    s.remember_recent("C:/a.txt")
    settings_mod.save(s, path)
    loaded = settings_mod.load(path)
    assert loaded.theme == "system" and loaded.font_size == 14
    assert loaded.recent_files == ["C:/a.txt", "C:/b.txt"]


def test_bad_values_fall_back(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"theme": "purple", "font_size": "big", "default_mode": "pdf"}))
    loaded = settings_mod.load(path)
    assert loaded.theme == "dark" and loaded.font_size == 12 and loaded.default_mode == "plain"


def test_recent_is_capped():
    s = settings_mod.Settings()
    for i in range(20):
        s.remember_recent(f"C:/{i}.txt")
    assert len(s.recent_files) == settings_mod.MAX_RECENT
    assert s.recent_files[0] == "C:/19.txt"
