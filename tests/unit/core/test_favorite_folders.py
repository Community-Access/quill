from pathlib import Path

from quill.core.favorite_folders import (
    FavoriteFolders,
    filter_favorite_files,
    list_files_in_favorites,
)


def test_add_appends_in_insertion_order(tmp_path: Path) -> None:
    target = tmp_path / "favorite_folders.json"
    vault = FavoriteFolders(path=target)
    assert vault.add(r"C:\Projects\Reports") is True
    assert vault.add(r"C:\Projects\Drafts") is True
    assert vault.folders == [r"C:\Projects\Reports", r"C:\Projects\Drafts"]


def test_add_duplicate_returns_false_and_does_not_duplicate(tmp_path: Path) -> None:
    target = tmp_path / "favorite_folders.json"
    vault = FavoriteFolders(path=target)
    vault.add(r"C:\Projects\Reports")
    assert vault.add(r"C:\Projects\Reports") is False
    assert vault.folders == [r"C:\Projects\Reports"]


def test_add_blank_is_ignored(tmp_path: Path) -> None:
    target = tmp_path / "favorite_folders.json"
    vault = FavoriteFolders(path=target)
    assert vault.add("   ") is False
    assert vault.folders == []


def test_remove_existing_returns_true(tmp_path: Path) -> None:
    target = tmp_path / "favorite_folders.json"
    vault = FavoriteFolders(path=target)
    vault.add(r"C:\Projects\Reports")
    assert vault.remove(r"C:\Projects\Reports") is True
    assert vault.folders == []


def test_remove_missing_returns_false(tmp_path: Path) -> None:
    target = tmp_path / "favorite_folders.json"
    vault = FavoriteFolders(path=target)
    assert vault.remove(r"C:\Projects\Reports") is False


def test_round_trip_persists_across_load(tmp_path: Path) -> None:
    target = tmp_path / "favorite_folders.json"
    vault = FavoriteFolders(path=target)
    vault.add(r"C:\Projects\Reports")
    vault.add(r"C:\Projects\Drafts")

    loaded = FavoriteFolders.load(target)
    assert loaded.folders == [r"C:\Projects\Reports", r"C:\Projects\Drafts"]


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "does-not-exist.json"
    vault = FavoriteFolders.load(target)
    assert vault.folders == []


def test_load_malformed_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "favorite_folders.json"
    with open(target, "wb") as f:
        f.write(b"{not valid json")
    vault = FavoriteFolders.load(target)
    assert vault.folders == []


def test_names_uses_folder_basename() -> None:
    # Forward slashes, not backslashes: names() does Path(folder).name, and
    # pathlib on POSIX doesn't split on "\\" -- forward slashes parse
    # correctly as a Windows-style path on every platform pytest runs on.
    vault = FavoriteFolders(folders=["C:/Projects/Reports", "C:/Projects/Drafts"])
    assert vault.names() == ["Reports", "Drafts"]


def test_names_falls_back_to_full_path_on_collision() -> None:
    vault = FavoriteFolders(folders=[r"C:\Work\Reports", r"D:\Archive\Reports"])
    assert vault.names() == [r"C:\Work\Reports", r"D:\Archive\Reports"]


# --- Quick Open over favorites -------------------------------------------- #


def test_list_files_in_favorites_is_non_recursive(tmp_path: Path) -> None:
    folder = tmp_path / "Reports"
    folder.mkdir()
    (folder / "top.txt").write_text("x")
    nested = folder / "nested"
    nested.mkdir()
    (nested / "deep.txt").write_text("x")

    vault = FavoriteFolders(folders=[str(folder)])
    files = list_files_in_favorites(vault)

    assert [f.path.name for f in files] == ["top.txt"]
    assert files[0].folder_label == "Reports"


def test_list_files_in_favorites_skips_missing_folder(tmp_path: Path) -> None:
    vault = FavoriteFolders(folders=[str(tmp_path / "does-not-exist")])
    assert list_files_in_favorites(vault) == []


def test_list_files_in_favorites_recursive_finds_nested_files(tmp_path: Path) -> None:
    folder = tmp_path / "Reports"
    folder.mkdir()
    (folder / "top.txt").write_text("x")
    nested = folder / "nested"
    nested.mkdir()
    (nested / "deep.txt").write_text("x")
    deeper = nested / "deeper"
    deeper.mkdir()
    (deeper / "deepest.txt").write_text("x")

    vault = FavoriteFolders(folders=[str(folder)])
    files = list_files_in_favorites(vault, recursive=True)

    assert sorted(f.path.name for f in files) == ["deep.txt", "deepest.txt", "top.txt"]
    assert all(f.folder_label == "Reports" for f in files)


def test_list_files_in_favorites_recursive_is_capped(tmp_path: Path, monkeypatch) -> None:
    import quill.core.favorite_folders as ff_module

    monkeypatch.setattr(ff_module, "_RECURSIVE_SCAN_CAP", 3)
    folder = tmp_path / "Reports"
    folder.mkdir()
    for i in range(10):
        (folder / f"file{i}.txt").write_text("x")

    vault = FavoriteFolders(folders=[str(folder)])
    files = list_files_in_favorites(vault, recursive=True)

    assert len(files) == 3


def test_list_files_in_favorites_combines_multiple_folders(tmp_path: Path) -> None:
    reports = tmp_path / "Reports"
    reports.mkdir()
    (reports / "q1.txt").write_text("x")
    drafts = tmp_path / "Drafts"
    drafts.mkdir()
    (drafts / "notes.txt").write_text("x")

    vault = FavoriteFolders(folders=[str(reports), str(drafts)])
    files = list_files_in_favorites(vault)

    assert sorted(f.path.name for f in files) == ["notes.txt", "q1.txt"]


def test_filter_favorite_files_empty_query_returns_all(tmp_path: Path) -> None:
    folder = tmp_path / "Reports"
    folder.mkdir()
    (folder / "a.txt").write_text("x")
    (folder / "b.txt").write_text("x")
    vault = FavoriteFolders(folders=[str(folder)])
    files = list_files_in_favorites(vault)

    assert filter_favorite_files(files, "") == files


def test_filter_favorite_files_matches_substring_case_insensitively(tmp_path: Path) -> None:
    folder = tmp_path / "Reports"
    folder.mkdir()
    (folder / "Quarterly.txt").write_text("x")
    (folder / "notes.txt").write_text("x")
    vault = FavoriteFolders(folders=[str(folder)])
    files = list_files_in_favorites(vault)

    filtered = filter_favorite_files(files, "quart")
    assert [f.path.name for f in filtered] == ["Quarterly.txt"]


def test_filter_favorite_files_no_match_returns_empty(tmp_path: Path) -> None:
    folder = tmp_path / "Reports"
    folder.mkdir()
    (folder / "a.txt").write_text("x")
    vault = FavoriteFolders(folders=[str(folder)])
    files = list_files_in_favorites(vault)

    assert filter_favorite_files(files, "zzz") == []
