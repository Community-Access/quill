"""Tests for the pluggable watch-action registry (WATCH-2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech.provider import TranscriptionResult, TranscriptionSegment
from quill.core.watch_actions import (
    OUTCOME_DONE,
    OUTCOME_FAILED,
    OUTCOME_SKIPPED,
    AiAction,
    ConvertAction,
    CopyAction,
    MoveAction,
    OcrAction,
    OpenAction,
    RunMacroAction,
    RunPythonTransformAction,
    UnavailableAction,
    WatchAction,
    WatchActionOutcome,
    WatchActionRegistry,
    WatchItem,
    _humanize_action_error,
    default_registry,
)
from quill.core.watch_transcribe import WhispererTranscribeAction


def _item(path: Path) -> WatchItem:
    return WatchItem(source_path=path, profile_id="p1")


def test_outcome_helpers_and_ok_flag() -> None:
    assert WatchActionOutcome.done("hi").ok is True
    assert WatchActionOutcome.failed("nope").ok is False
    assert WatchActionOutcome.skipped("later").status == OUTCOME_SKIPPED


def test_register_and_get_round_trip() -> None:
    registry = WatchActionRegistry()
    action = OpenAction(on_open=lambda _p: None)
    registry.register(action)
    assert registry.get("open") is action
    assert registry.get("missing") is None


def test_register_rejects_empty_id() -> None:
    registry = WatchActionRegistry()
    with pytest.raises(ValueError):
        registry.register(OpenAction(action_id=""))


def test_register_rejects_duplicate_without_replace() -> None:
    registry = WatchActionRegistry()
    registry.register(MoveAction())
    with pytest.raises(ValueError):
        registry.register(MoveAction())


def test_register_replace_supersedes_placeholder() -> None:
    registry = WatchActionRegistry()
    registry.register(UnavailableAction(action_id="glow_audit", label="GLOW", reason="not yet"))
    real = MoveAction(action_id="glow_audit", label="GLOW real")
    registry.register(real, replace=True)
    assert registry.get("glow_audit") is real


def test_actions_are_sorted_by_id() -> None:
    registry = WatchActionRegistry()
    registry.register(OpenAction(on_open=lambda _p: None))
    registry.register(MoveAction())
    ids = [action.action_id for action in registry.actions()]
    assert ids == sorted(ids)


def test_feature_gating_filters_available_actions() -> None:
    enabled = {"future.glow": False}
    registry = WatchActionRegistry(feature_enabled=lambda fid: enabled.get(fid, True))
    registry.register(OpenAction(on_open=lambda _p: None))  # no feature -> always on
    registry.register(
        UnavailableAction(
            action_id="glow_audit",
            label="GLOW",
            required_feature_id="future.glow",
            reason="not yet",
        )
    )
    available_ids = {action.action_id for action in registry.available_actions()}
    assert "open" in available_ids
    assert "glow_audit" not in available_ids
    assert registry.is_available("open") is True
    assert registry.is_available("glow_audit") is False


def test_run_unknown_action_fails_clearly() -> None:
    registry = WatchActionRegistry()
    outcome = registry.run("nope", _item(Path("x.txt")))
    assert outcome.status == OUTCOME_FAILED
    assert "Unknown watch action" in outcome.message


def test_run_disabled_feature_is_skipped_not_failed() -> None:
    registry = WatchActionRegistry(feature_enabled=lambda _fid: False)
    registry.register(
        UnavailableAction(
            action_id="glow_audit",
            label="GLOW",
            required_feature_id="future.glow",
            reason="not yet",
        )
    )
    outcome = registry.run("glow_audit", _item(Path("x.txt")))
    assert outcome.status == OUTCOME_SKIPPED


def test_run_invalid_options_fails_before_running() -> None:
    registry = WatchActionRegistry()
    registry.register(MoveAction())
    outcome = registry.run("move", _item(Path("x.txt")), {"destination": ""})
    assert outcome.status == OUTCOME_FAILED
    assert "destination" in outcome.message.lower()


def test_open_action_invokes_callback(tmp_path: Path) -> None:
    seen: list[Path] = []
    registry = WatchActionRegistry()
    registry.register(OpenAction(on_open=seen.append))
    source = tmp_path / "doc.txt"
    source.write_text("hi", encoding="utf-8")
    outcome = registry.run("open", _item(source))
    assert outcome.status == OUTCOME_DONE
    assert seen == [source]


def test_open_action_without_handler_fails() -> None:
    registry = WatchActionRegistry()
    registry.register(OpenAction())  # no handler
    outcome = registry.run("open", _item(Path("x.txt")))
    assert outcome.status == OUTCOME_FAILED


def test_move_action_moves_file(tmp_path: Path) -> None:
    source = tmp_path / "in" / "doc.txt"
    source.parent.mkdir()
    source.write_text("hi", encoding="utf-8")
    dest = tmp_path / "out"
    dest.mkdir()
    registry = WatchActionRegistry()
    registry.register(MoveAction())
    outcome = registry.run("move", _item(source), {"destination": str(dest)})
    assert outcome.status == OUTCOME_DONE
    assert not source.exists()
    assert (dest / "doc.txt").exists()
    assert outcome.result_path == dest / "doc.txt"


def test_run_guards_against_action_crash() -> None:
    class Boom(MoveAction):
        def validate(self, options) -> list[str]:  # type: ignore[override]
            return []

        def run(self, item: WatchItem, options) -> WatchActionOutcome:  # type: ignore[override]
            raise RuntimeError("kaboom")

    registry = WatchActionRegistry()
    registry.register(Boom(action_id="boom", label="Boom"))
    outcome = registry.run("boom", _item(Path("x.txt")))
    assert outcome.status == OUTCOME_FAILED
    assert "kaboom" in outcome.message


def test_default_registry_has_builtins_and_placeholders() -> None:
    registry = default_registry(on_open=lambda _p: None)
    ids = {action.action_id for action in registry.actions()}
    assert {
        "open",
        "move",
        "copy",
        "convert",
        "run_macro",
        "run_python",
        "ai",
        "glow_audit",
        "bw_transcribe",
    } <= ids


def test_actions_satisfy_protocol() -> None:
    for action in (OpenAction(), MoveAction(), UnavailableAction(action_id="x", label="X")):
        assert isinstance(action, WatchAction)


def test_copy_action_copies_and_keeps_original(tmp_path: Path) -> None:
    source = tmp_path / "in" / "doc.txt"
    source.parent.mkdir()
    source.write_text("hi", encoding="utf-8")
    dest = tmp_path / "out"
    dest.mkdir()
    registry = WatchActionRegistry()
    registry.register(CopyAction())
    outcome = registry.run("copy", _item(source), {"destination": str(dest)})
    assert outcome.status == OUTCOME_DONE
    assert source.exists()  # original left in place
    assert (dest / "doc.txt").read_text(encoding="utf-8") == "hi"
    assert outcome.result_path == dest / "doc.txt"


def test_copy_action_missing_destination_fails() -> None:
    registry = WatchActionRegistry()
    registry.register(CopyAction())
    outcome = registry.run("copy", _item(Path("x.txt")), {"destination": ""})
    assert outcome.status == OUTCOME_FAILED
    assert "destination" in outcome.message.lower()


def test_convert_action_invokes_handler(tmp_path: Path) -> None:
    source = tmp_path / "doc.md"
    source.write_text("# hi", encoding="utf-8")
    produced = tmp_path / "doc.html"
    produced.write_text("<h1>hi</h1>", encoding="utf-8")
    seen: list[tuple[Path, str]] = []

    def fake_convert(path: Path, fmt: str) -> Path:
        seen.append((path, fmt))
        return produced

    registry = WatchActionRegistry()
    registry.register(ConvertAction(on_convert=fake_convert))
    outcome = registry.run("convert", _item(source), {"target_format": "html"})
    assert outcome.status == OUTCOME_DONE
    assert seen == [(source, "html")]
    assert outcome.result_path == produced


def test_convert_action_without_handler_fails() -> None:
    registry = WatchActionRegistry()
    registry.register(ConvertAction())
    outcome = registry.run("convert", _item(Path("x.md")), {"target_format": "html"})
    assert outcome.status == OUTCOME_FAILED
    assert "handler" in outcome.message.lower()


def test_convert_action_missing_format_fails() -> None:
    registry = WatchActionRegistry()
    registry.register(ConvertAction(on_convert=lambda p, f: p))
    outcome = registry.run("convert", _item(Path("x.md")), {})
    assert outcome.status == OUTCOME_FAILED
    assert "format" in outcome.message.lower()


def test_run_macro_action_invokes_handler(tmp_path: Path) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("hi", encoding="utf-8")
    seen: list[tuple[Path, str]] = []
    registry = WatchActionRegistry()
    registry.register(RunMacroAction(on_run_macro=lambda p, n: seen.append((p, n))))
    outcome = registry.run("run_macro", _item(source), {"macro_name": "Tidy"})
    assert outcome.status == OUTCOME_DONE
    assert seen == [(source, "Tidy")]


def test_run_macro_action_requires_name() -> None:
    registry = WatchActionRegistry()
    registry.register(RunMacroAction(on_run_macro=lambda p, n: None))
    outcome = registry.run("run_macro", _item(Path("x.txt")), {})
    assert outcome.status == OUTCOME_FAILED
    assert "macro" in outcome.message.lower()


class _FakeSandboxResult:
    def __init__(self, *, succeeded: bool, result: str = "", error: str = "") -> None:
        self.succeeded = succeeded
        self.result = result
        self.stdout = result
        self.stderr = error
        self.error = error


def test_python_transform_writes_result_in_place(tmp_path: Path) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("hello", encoding="utf-8")

    def fake_runner(code: str, *, document_text: str, timeout_seconds: float):
        assert document_text == "hello"
        return _FakeSandboxResult(succeeded=True, result=document_text.upper())

    registry = WatchActionRegistry()
    registry.register(RunPythonTransformAction(runner=fake_runner))
    outcome = registry.run("run_python", _item(source), {"code": "result = document_text.upper()"})
    assert outcome.status == OUTCOME_DONE
    assert source.read_text(encoding="utf-8") == "HELLO"
    assert outcome.result_path == source


def test_python_transform_writes_to_suffixed_file(tmp_path: Path) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("hello", encoding="utf-8")

    def fake_runner(code: str, *, document_text: str, timeout_seconds: float):
        return _FakeSandboxResult(succeeded=True, result="new")

    registry = WatchActionRegistry()
    registry.register(RunPythonTransformAction(runner=fake_runner))
    outcome = registry.run(
        "run_python", _item(source), {"code": "result = 'new'", "output_suffix": ".out"}
    )
    assert outcome.status == OUTCOME_DONE
    assert source.read_text(encoding="utf-8") == "hello"  # original untouched
    assert (tmp_path / "doc.out.txt").read_text(encoding="utf-8") == "new"


def test_python_transform_failure_surfaces_error(tmp_path: Path) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("hello", encoding="utf-8")

    def fake_runner(code: str, *, document_text: str, timeout_seconds: float):
        return _FakeSandboxResult(succeeded=False, error="boom")

    registry = WatchActionRegistry()
    registry.register(RunPythonTransformAction(runner=fake_runner))
    outcome = registry.run("run_python", _item(source), {"code": "result = 1"})
    assert outcome.status == OUTCOME_FAILED
    assert "boom" in outcome.message


def test_python_transform_requires_code() -> None:
    registry = WatchActionRegistry()
    registry.register(RunPythonTransformAction(runner=lambda *a, **k: None))
    outcome = registry.run("run_python", _item(Path("x.txt")), {})
    assert outcome.status == OUTCOME_FAILED
    assert "transform" in outcome.message.lower()


def test_ai_action_skipped_without_consent(tmp_path: Path) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("hi", encoding="utf-8")
    called: list[Path] = []

    def fake_ai(path: Path, options) -> WatchActionOutcome:
        called.append(path)
        return WatchActionOutcome.done("summarized")

    registry = WatchActionRegistry()
    registry.register(AiAction(on_ai=fake_ai))
    outcome = registry.run("ai", _item(source), {"mode": "summarize"})
    assert outcome.status == OUTCOME_SKIPPED
    assert "consent" in outcome.message.lower()
    assert called == []  # handler never invoked without consent


def test_ai_action_runs_with_consent(tmp_path: Path) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("hi", encoding="utf-8")

    def fake_ai(path: Path, options) -> WatchActionOutcome:
        return WatchActionOutcome.done(f"{options['mode']} done")

    registry = WatchActionRegistry()
    registry.register(AiAction(on_ai=fake_ai))
    outcome = registry.run("ai", _item(source), {"mode": "summarize", "consent": True})
    assert outcome.status == OUTCOME_DONE
    assert outcome.message == "summarize done"


def test_ai_action_invalid_mode_fails() -> None:
    registry = WatchActionRegistry()
    registry.register(AiAction(on_ai=lambda p, o: WatchActionOutcome.done()))
    outcome = registry.run("ai", _item(Path("x.txt")), {"mode": "nope", "consent": True})
    assert outcome.status == OUTCOME_FAILED
    assert "mode" in outcome.message.lower()


def test_dry_run_describes_runnable_action(tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir()
    registry = WatchActionRegistry()
    registry.register(MoveAction())
    preview = registry.dry_run("move", _item(tmp_path / "doc.txt"), {"destination": str(dest)})
    assert "doc.txt" in preview
    assert str(dest) in preview


def test_dry_run_reports_invalid_options() -> None:
    registry = WatchActionRegistry()
    registry.register(MoveAction())
    preview = registry.dry_run("move", _item(Path("doc.txt")), {"destination": ""})
    assert preview.lower().startswith("would not run")


def test_dry_run_flags_missing_consent(tmp_path: Path) -> None:
    registry = WatchActionRegistry()
    registry.register(AiAction(on_ai=lambda p, o: WatchActionOutcome.done()))
    preview = registry.dry_run("ai", _item(tmp_path / "doc.txt"), {"mode": "summarize"})
    assert "consent" in preview.lower()


def test_dry_run_unknown_action() -> None:
    registry = WatchActionRegistry()
    assert "Unknown" in registry.dry_run("nope", _item(Path("x.txt")))


def test_ocr_action_registered_in_default_registry() -> None:
    registry = default_registry()
    action = registry.get("ocr")
    assert action is not None
    assert action.required_feature_id == "core.ocr"
    assert getattr(action, "requires_consent", False) is False  # OCR is offline


def test_ocr_action_skipped_when_feature_off(tmp_path: Path) -> None:
    source = tmp_path / "scan.png"
    source.write_bytes(b"fake")
    called: list[Path] = []
    registry = WatchActionRegistry(feature_enabled=lambda fid: fid != "core.ocr")
    registry.register(OcrAction(on_ocr=lambda p: called.append(p) or "text"))
    outcome = registry.run("ocr", _item(source))
    assert outcome.status == OUTCOME_SKIPPED
    assert called == []  # handler never invoked when the feature is off


def test_ocr_action_happy_path_writes_text_file(tmp_path: Path) -> None:
    source = tmp_path / "scan.png"
    source.write_bytes(b"fake")
    registry = WatchActionRegistry()
    registry.register(OcrAction(on_ocr=lambda _p: "Recognized words"))
    outcome = registry.run("ocr", _item(source))
    assert outcome.status == OUTCOME_DONE
    target = source.with_suffix(".txt")
    assert target.read_text(encoding="utf-8") == "Recognized words\n"
    assert outcome.result_path == target


def test_ocr_action_without_handler_fails() -> None:
    registry = WatchActionRegistry()
    registry.register(OcrAction())
    outcome = registry.run("ocr", _item(Path("scan.png")))
    assert outcome.status == OUTCOME_FAILED
    assert "ocr engine" in outcome.message.lower()


# --- M-1: action-error humanization -----------------------------------------


def test_humanize_permission_error_is_actionable() -> None:
    message = _humanize_action_error("move", PermissionError(13, "Permission denied"))
    assert "permission" in message.lower()
    assert "Quill" in message
    assert "Errno" not in message


def test_humanize_file_not_found_mentions_reappear() -> None:
    message = _humanize_action_error("copy", FileNotFoundError(2, "No such file"))
    assert "disappeared" in message.lower()


def test_humanize_generic_oserror_keeps_strerror() -> None:
    message = _humanize_action_error("move", OSError(28, "No space left on device"))
    assert "No space left on device" in message


def test_humanize_unrecognized_error_falls_back_to_str() -> None:
    message = _humanize_action_error("open", ValueError("bad token"))
    assert message == "bad token"


def test_move_action_permission_error_humanized(tmp_path: Path) -> None:
    source = tmp_path / "x.txt"
    source.write_text("x")
    destination = tmp_path / "sub"  # does not exist
    registry = WatchActionRegistry()
    action = MoveAction()
    registry.register(action)
    outcome = registry.run(
        "move",
        _item(source),
        {"destination": str(destination)},
    )
    assert outcome.status == OUTCOME_FAILED
    assert "permission" in outcome.message.lower() or "folder" in outcome.message.lower()
    assert "Errno" not in outcome.message


# ---------------------------------------------------------------------------
# WhispererTranscribeAction (WATCH-9): offline audio transcription
# ---------------------------------------------------------------------------


def _result(text: str = "hello world", *, with_segments: bool = False) -> TranscriptionResult:
    segments = ()
    if with_segments:
        segments = (
            TranscriptionSegment(start_seconds=0.0, end_seconds=1.5, text="hello"),
            TranscriptionSegment(start_seconds=1.5, end_seconds=3.0, text="world"),
        )
    return TranscriptionResult(full_text=text, segments=segments)


def _transcriber(result: TranscriptionResult):
    return lambda _path, _options: result


def test_whisperer_transcribe_writes_sibling_transcript(tmp_path: Path) -> None:
    audio = tmp_path / "interview.mp3"
    audio.write_bytes(b"fake-audio")
    captured: dict[str, object] = {}

    def fake_transcribe(path: Path, options) -> TranscriptionResult:
        captured["path"] = path
        captured["model_id"] = options.get("model_id")
        return _result("hello world")

    action = WhispererTranscribeAction(on_transcribe=fake_transcribe)
    outcome = action.run(_item(audio), {"model_id": "base"})

    assert outcome.status == OUTCOME_DONE
    transcript = audio.with_suffix(".txt")
    assert outcome.result_path == transcript
    assert transcript.read_text(encoding="utf-8") == "hello world\n"
    assert captured["path"] == audio
    assert captured["model_id"] == "base"


class _FakeActionBackend:
    def __init__(self, *_a: object, **_k: object) -> None: ...

    def is_available(self) -> tuple[bool, None]:
        return (True, None)

    def respond(self, _prompt: str) -> str:
        return "## Minutes\n- decided to ship"


def test_whisperer_transcribe_then_runs_ai_action(tmp_path: Path, monkeypatch) -> None:
    import quill.core.ai.model_manager as mm
    import quill.core.ai.provider_backend as pb

    monkeypatch.setattr(mm, "load_ai_enabled", lambda: True)
    monkeypatch.setattr(pb, "ProviderChatBackend", _FakeActionBackend)

    audio = tmp_path / "standup.mp3"
    audio.write_bytes(b"x")
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result("we decided to ship")))
    outcome = action.run(_item(audio), {"transcript_action": "meeting-minutes"})

    assert outcome.status == OUTCOME_DONE
    # The transcript and the action document are both written next to the audio.
    assert audio.with_suffix(".txt").read_text(encoding="utf-8") == "we decided to ship\n"
    doc = audio.with_name("standup-meeting-minutes.md")
    assert doc.read_text(encoding="utf-8").startswith("## Minutes")
    assert "standup-meeting-minutes.md" in outcome.message


def test_transcribe_action_skipped_when_ai_off_keeps_transcript(
    tmp_path: Path, monkeypatch
) -> None:
    import quill.core.ai.model_manager as mm

    monkeypatch.setattr(mm, "load_ai_enabled", lambda: False)
    audio = tmp_path / "note.mp3"
    audio.write_bytes(b"x")
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result("hello")))
    outcome = action.run(_item(audio), {"transcript_action": "meeting-minutes"})

    assert outcome.status == OUTCOME_DONE  # the transcript still succeeds
    assert audio.with_suffix(".txt").exists()
    assert not audio.with_name("note-meeting-minutes.md").exists()
    assert "AI is off" in outcome.message


def test_whisperer_transcribe_srt_writes_timestamped_captions(tmp_path: Path) -> None:
    audio = tmp_path / "talk.mp3"
    audio.write_bytes(b"x")
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result(with_segments=True)))
    outcome = action.run(_item(audio), {"output_format": "srt"})
    assert outcome.status == OUTCOME_DONE
    srt = audio.with_suffix(".srt")
    assert outcome.result_path == srt
    body = srt.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,500" in body
    assert "hello" in body and "world" in body


def test_whisperer_transcribe_vtt_writes_webvtt(tmp_path: Path) -> None:
    audio = tmp_path / "talk.mp3"
    audio.write_bytes(b"x")
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result(with_segments=True)))
    outcome = action.run(_item(audio), {"output_format": "vtt"})
    assert outcome.result_path == audio.with_suffix(".vtt")
    assert audio.with_suffix(".vtt").read_text(encoding="utf-8").startswith("WEBVTT")


def test_whisperer_transcribe_markdown_format(tmp_path: Path) -> None:
    audio = tmp_path / "talk.mp3"
    audio.write_bytes(b"x")
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result("a sentence")))
    outcome = action.run(_item(audio), {"output_format": "md"})
    assert outcome.result_path == audio.with_suffix(".md")
    assert "# Transcript" in audio.with_suffix(".md").read_text(encoding="utf-8")


def test_whisperer_transcribe_srt_without_segments_falls_back_to_text(tmp_path: Path) -> None:
    audio = tmp_path / "talk.mp3"
    audio.write_bytes(b"x")
    # Engine returned no timestamped segments -> never write an empty .srt.
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result("plain text only")))
    outcome = action.run(_item(audio), {"output_format": "srt"})
    assert outcome.result_path == audio.with_suffix(".txt")
    assert audio.with_suffix(".txt").read_text(encoding="utf-8") == "plain text only\n"


def test_whisperer_transcribe_unknown_format_is_flagged() -> None:
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result()))
    problems = action.validate({"output_format": "docx"})
    assert problems
    assert "Unknown transcript format" in problems[0]


def test_whisperer_transcribe_requires_no_consent_and_no_feature() -> None:
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result()))
    # Offline path: no per-profile consent and no feature flag required, so it is
    # always available in the registry.
    assert action.requires_consent is False
    assert action.required_feature_id == ""


def test_whisperer_transcribe_skips_non_audio(tmp_path: Path) -> None:
    doc = tmp_path / "notes.txt"
    doc.write_text("not audio")
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result("should not run")))
    outcome = action.run(_item(doc), {})
    assert outcome.status == OUTCOME_SKIPPED
    assert "supported audio" in outcome.message


def test_whisperer_transcribe_engine_error_is_failed_outcome(tmp_path: Path) -> None:
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"x")

    def boom(_path: Path, _options) -> TranscriptionResult:
        raise RuntimeError("engine exploded")

    action = WhispererTranscribeAction(on_transcribe=boom)
    outcome = action.run(_item(audio), {})
    assert outcome.status == OUTCOME_FAILED
    assert "engine exploded" in outcome.message


def test_whisperer_transcribe_injected_handler_validates_ok() -> None:
    # With an injected handler and a valid format, validate() never probes the engine.
    action = WhispererTranscribeAction(on_transcribe=_transcriber(_result()))
    assert action.validate({}) == []
    assert action.validate({"output_format": "vtt"}) == []


def test_whisperer_transcribe_default_validate_reports_missing_model(monkeypatch) -> None:
    # No injected handler: validate() reports the no-model guidance instead of
    # silently succeeding, so the profile dry-run explains why it would not run.
    import quill.core.speech.transcribe as transcribe_mod

    monkeypatch.setattr(transcribe_mod, "has_installed_offline_model", lambda: False)
    action = WhispererTranscribeAction()
    problems = action.validate({})
    assert problems
    assert "Manage Speech Models" in problems[0]


def test_default_registry_registers_real_transcribe_action() -> None:
    registry = default_registry()
    action = registry.get("bw_transcribe")
    assert isinstance(action, WhispererTranscribeAction)
    # No longer a placeholder: it is feature-ungated and consent-free (offline).
    assert registry.is_available("bw_transcribe")
