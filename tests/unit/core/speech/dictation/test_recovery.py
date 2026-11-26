from __future__ import annotations

from pathlib import Path

from quill.core.speech.dictation.recovery import DictationRecoveryRepository
from quill.core.speech.dictation.session import DictationSession


def _wav(tmp_path: Path, name: str = "src.wav") -> Path:
    path = tmp_path / name
    path.write_bytes(b"RIFFfake-audio")
    return path


def test_save_audio_moves_and_marks_saved(tmp_path: Path) -> None:
    repo = DictationRecoveryRepository(tmp_path / "rec")
    session = DictationSession()
    src = _wav(tmp_path)
    dest = repo.save_audio(session, src)
    assert dest.exists()
    assert not src.exists()  # moved, not copied
    assert session.audio_state == "saved"
    assert session.audio_path == str(dest)
    # Sidecar written and reflects "audio saved before transcription".
    assert repo.metadata_path(session.session_id).exists()


def test_list_incomplete_returns_unfinished_sessions(tmp_path: Path) -> None:
    repo = DictationRecoveryRepository(tmp_path / "rec")
    pending = DictationSession()
    repo.save_audio(pending, _wav(tmp_path, "a.wav"))

    done = DictationSession()
    repo.save_audio(done, _wav(tmp_path, "b.wav"))
    done.insertion_state = "inserted"
    repo.save_metadata(done)

    incomplete = repo.list_incomplete()
    ids = {item.session.session_id for item in incomplete}
    assert pending.session_id in ids
    assert done.session_id not in ids  # successfully inserted -> not offered


def test_save_transcript_writes_text_and_state(tmp_path: Path) -> None:
    repo = DictationRecoveryRepository(tmp_path / "rec")
    session = DictationSession()
    repo.save_transcript(session, "hello there")
    assert repo.transcript_path(session.session_id).read_text(encoding="utf-8") == "hello there"
    assert session.transcription_state == "done"


def test_delete_removes_all_files(tmp_path: Path) -> None:
    repo = DictationRecoveryRepository(tmp_path / "rec")
    session = DictationSession()
    repo.save_audio(session, _wav(tmp_path))
    repo.save_transcript(session, "x")
    repo.delete(session.session_id)
    assert not repo.audio_path(session.session_id).exists()
    assert not repo.metadata_path(session.session_id).exists()
    assert not repo.transcript_path(session.session_id).exists()


def test_cleanup_expired_only_touches_inserted_sessions(tmp_path: Path) -> None:
    repo = DictationRecoveryRepository(tmp_path / "rec")
    old_done = DictationSession()
    old_done.started_at = 1000.0
    old_done.stopped_at = 1000.0
    repo.save_audio(old_done, _wav(tmp_path, "a.wav"))
    old_done.insertion_state = "inserted"
    repo.save_metadata(old_done)

    old_pending = DictationSession()
    old_pending.started_at = 1000.0
    repo.save_audio(old_pending, _wav(tmp_path, "b.wav"))

    removed = repo.cleanup_expired(retain_seconds=60.0, now=5000.0)
    assert removed == 1
    assert not repo.metadata_path(old_done.session_id).exists()
    assert repo.metadata_path(old_pending.session_id).exists()  # incomplete kept


def test_cleanup_negative_retain_keeps_everything(tmp_path: Path) -> None:
    repo = DictationRecoveryRepository(tmp_path / "rec")
    session = DictationSession()
    session.stopped_at = 1.0
    repo.save_audio(session, _wav(tmp_path))
    session.insertion_state = "inserted"
    repo.save_metadata(session)
    assert repo.cleanup_expired(retain_seconds=-1.0, now=10**9) == 0


def test_session_roundtrips_through_sidecar(tmp_path: Path) -> None:
    repo = DictationRecoveryRepository(tmp_path / "rec")
    session = DictationSession()
    session.context = session.context.__class__(
        document_id="doc-1", caret=42, prefix_char="x", document_revision=7
    )
    repo.save_audio(session, _wav(tmp_path))
    [recovered] = repo.list_incomplete()
    assert recovered.session.context.document_id == "doc-1"
    assert recovered.session.context.caret == 42
    assert recovered.session.context.document_revision == 7


# -- what a waiting recording is called (FUX-05) ------------------------------


def test_states_are_said_in_words_not_codes() -> None:
    from quill.core.speech.dictation.recovery import state_words

    def words(transcription: str, insertion: str = "not_started") -> str:
        session = DictationSession()
        session.transcription_state = transcription
        session.insertion_state = insertion
        return state_words(session)

    assert words("done", "deferred") == "Transcribed, not inserted yet"
    assert words("done", "failed") == "Transcribed, could not be inserted"
    assert words("pending") == words("running") == "Not transcribed yet"
    assert words("failed") == "Transcription failed"
    assert words("empty") == "No speech heard"


def test_the_launch_sentence_names_the_recording_and_the_real_menu(tmp_path: Path) -> None:
    import time

    from quill.core.speech.dictation.recovery import HISTORY_MENU_PATH, startup_sentence

    repo = DictationRecoveryRepository(tmp_path / "rec")
    now = time.mktime((2026, 11, 24, 15, 0, 0, 0, 0, -1))
    older = DictationSession()
    older.started_at = now - 86400 * 3
    newest = DictationSession()
    newest.started_at = time.mktime((2026, 11, 24, 14, 5, 0, 0, 0, -1))
    for session in (older, newest):
        repo.save_metadata(session)
    repo.save_transcript(newest, "Dear Sam, thank you for the notes you sent on Friday")
    pending = repo.list_incomplete()

    one = startup_sentence(pending[:1], now=now)
    assert one == (
        'A dictation recording from today at 14:05, beginning "Dear Sam, thank you for '
        'the notes you" was never inserted. '
        f"{HISTORY_MENU_PATH} has it."
    )
    both = startup_sentence(pending, now=now)
    assert both.startswith("2 dictation recordings were never inserted; the newest is from today")
    assert "(s)" not in both and both.endswith("lists them.")
    assert startup_sentence([], now=now) == ""


def test_the_menu_path_is_the_menus_own() -> None:
    """The sentence used to send people to "Dictation History", which no menu says."""
    from quill.core.speech.dictation.recovery import HISTORY_MENU_PATH

    menu = Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8")
    assert '_("Dictation &History && Review...")' in menu
    assert '_("&Locked Dictation")' in menu and '_("Speec&h")' in menu
    assert HISTORY_MENU_PATH.endswith("Locked Dictation, Dictation History and Review")
