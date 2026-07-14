"""Orchestration for Tools > Speech > Batch Export to Speech Audio.

Free functions (not a mixin) so the heavy orchestration lives outside the
already-budgeted ``main_frame`` modules (GATE-11). Each takes the ``MainFrame``
as ``frame`` and uses its established helpers: ``_show_modal_dialog``,
``_run_background_task``, ``_show_message_box``, ``_preview_voice``,
``_set_status``, ``settings``, ``frame`` (the wx window), and ``_wx``.

The actual conversion is the tested wx-free core: ``document_speech`` drives
``chapter_assemble`` over every discovered document, with the chosen engine,
sounder, gaps, sentence/tail pauses and spoken headings.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from quill.ui.audio_studio.request import BatchSpeechRequest


class _BookReviewCancelled(Exception):
    """Internal: the user cancelled the chapter-review dialog, so skip the book build."""


class _BookStepDone(Exception):
    """Internal: the book step already finished on another path (library mode)."""


_ENGINE_OPTIONS = [
    ("Windows (SAPI 5)", "sapi5"),
    ("DECtalk", "dectalk"),
    ("Piper (neural, offline)", "piper"),
    ("Kokoro (neural, offline)", "kokoro"),
    ("eSpeak-NG (many languages)", "espeak"),
]


def _voices_for(engine: str) -> list[tuple[str, str]]:
    """[(voice_label, voice_id)] for *engine*, mirroring the Speech Hub lists."""
    from quill.core import read_aloud as ra

    try:
        if engine == "kokoro":
            voices = ra.list_kokoro_voices()
        elif engine == "piper":
            voices = ra.list_piper_catalog_voices()
        elif engine == "espeak":
            voices = ra.list_espeak_voices()
        elif engine == "dectalk":
            voices = ra.list_dectalk_voices()
        else:  # sapi5
            voices = ra.list_voices()
    except Exception:  # noqa: BLE001 - a missing engine yields an empty list
        return []
    return [(v.name or v.id, v.id) for v in voices]


def _defaults(frame: Any) -> BatchSpeechRequest:
    s = frame.settings
    engine = (s.read_aloud_engine or "sapi5").strip().lower()
    voice = {
        "kokoro": s.read_aloud_kokoro_voice,
        "dectalk": s.read_aloud_dectalk_voice,
        "espeak": s.read_aloud_espeak_voice,
    }.get(engine, s.read_aloud_voice)
    if engine == "piper" and s.read_aloud_piper_model:
        voice = Path(s.read_aloud_piper_model).stem
    source = Path.home()
    doc_path = getattr(frame, "_active_document_path", lambda: None)()
    if isinstance(doc_path, (str, Path)) and str(doc_path):
        parent = Path(doc_path).parent
        if parent.is_dir():
            source = parent
    base = BatchSpeechRequest(
        source_folder=source,
        recursive=False,
        extensions=(".docx", ".md", ".html", ".htm", ".txt"),
        engine=engine,
        voice=voice or "",
        rate=int(s.read_aloud_rate),
        speed=float(s.read_aloud_kokoro_speed),
        output_format="mp3",
        sound_enabled=bool(s.batch_speech_chapter_sound_enabled),
        sound_volume=int(s.batch_speech_chapter_sound_volume),
        article_gap_ms=int(s.batch_speech_article_gap_ms),
        sentence_gap_ms=int(s.batch_speech_sentence_gap_ms),
        tail_padding_ms=int(s.batch_speech_tail_padding_ms),
        speak_headings=True,
        skip_existing=False,
        temp_folder=(getattr(s, "batch_speech_temp_folder", "") or ""),
        save_spoken_text=bool(getattr(s, "batch_speech_save_spoken_text", False)),
    )
    # Apply-on-open: a remembered project profile overlays the global defaults.
    return _apply_project_profile(frame, base)


def _engine_available(frame: Any) -> dict[str, bool]:
    from quill.core.read_aloud import (
        discover_dectalk_executable,
        discover_espeak_executable,
        discover_piper_executable,
        kokoro_onnx_ready,
    )

    s = frame.settings
    return {
        "sapi5": True,
        "dectalk": discover_dectalk_executable(s.read_aloud_dectalk_executable) is not None,
        "piper": discover_piper_executable() is not None,
        "kokoro": kokoro_onnx_ready(),
        "espeak": discover_espeak_executable(s.read_aloud_espeak_executable) is not None,
    }


def _active_pronunciation_dictionaries(
    frame: Any, engine: str, source_folder: Path, *, language: str | None = None
) -> list[Any]:
    """Resolve the enabled, in-scope pronunciation dictionaries for this batch.

    Honors ``settings.pronunciation_enabled`` and the per-user enabled-id
    selection; the source folder is the project scope (a batch is a project run).
    Returns an empty list when pronunciation is off or none are defined, so the
    default behavior is unchanged until the user sets dictionaries up.
    """
    s = frame.settings
    if not getattr(s, "pronunciation_enabled", True):
        return []
    from quill.core.speech.pronunciation import active_dictionaries

    ids = list(getattr(s, "pronunciation_enabled_dictionary_ids", []) or [])
    enabled_ids = set(ids) if ids else None
    try:
        return active_dictionaries(
            engine, project_dir=source_folder, enabled_ids=enabled_ids, language=language
        )
    except Exception:  # noqa: BLE001 - a broken dictionary store must not block export
        return []


def _resolve_chapter_sound_path(frame: Any, dest_dir: Path) -> Path | None:
    """Resolve the configured chapter-transition ``sound_id`` to a real WAV.

    Looks the id up in the active sound pack (``settings.sound_pack_path``, or the
    bundled Ink pack) and writes the pre-buffered bytes into *dest_dir*. Returns
    ``None`` when no id is set or it is not in the pack, so chapter assembly falls
    back to its generated placeholder chime (the format-mismatch fallback in
    ``chapter_assemble`` also covers a sound that does not match the section audio).
    """
    settings = frame.settings
    sound_id = (getattr(settings, "batch_speech_chapter_sound_id", "") or "").strip()
    if not sound_id:
        return None
    import quill
    from quill.core.sound_pack import load_sound_pack

    pack_path = (getattr(settings, "sound_pack_path", "") or "").strip()
    pack = (
        Path(pack_path)
        if pack_path
        else Path(quill.__file__).parent / "assets" / "sound_packs" / "ink"
    )
    try:
        data = load_sound_pack(pack).events.get(sound_id)
    except Exception:  # noqa: BLE001 - a broken pack must not block export
        return None
    if not data:
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"chapter_sound_{sound_id}.wav"
    out.write_bytes(data)
    return out


def _cloud_credentials(frame: Any, provider: str) -> tuple[str, str]:
    """Return ``(api_key, model)`` for a cloud TTS *provider*, both possibly empty.

    Reuses the frame's per-provider key getters (the same credentials the AI Voice
    feature reads) and each provider's configured/default model. An empty key means
    the cloud target is skipped with a status note rather than failing the batch.
    """
    from quill.core.ai import cloud_tts

    s = frame.settings
    if provider == "gemini":
        api_key = frame._get_gemini_api_key()
    elif provider == "elevenlabs":
        api_key = frame._get_elevenlabs_api_key()
    else:  # openai
        api_key = frame._get_openai_api_key()
    model = (getattr(s, "ai_tts_model", "") or "").strip()
    # Only honor the saved model when it belongs to this provider; otherwise default.
    if model not in cloud_tts.models_for(provider):
        model = cloud_tts.default_model(provider)
    return api_key, model


def _ai_provider_metered() -> bool:
    """True when the configured AI assistant is a paid cloud provider (needs a key).

    Used to decide whether translation-via-AI adds a metered cost to the estimate; a
    local model (Ollama/llama.cpp) is free. Defaults to True (show a cost) on error.
    """
    try:
        from quill.core.ai.providers import provider_requires_api_key
        from quill.core.assistant_ai import load_assistant_connection_settings

        return provider_requires_api_key(load_assistant_connection_settings().provider)
    except Exception:  # noqa: BLE001 - estimate is best-effort
        return True


def _cloud_tts_targets(frame: Any, targets: Any) -> list[tuple[str, str]]:
    """The ``(provider, model)`` pairs for the cloud voices among *targets*."""
    from quill.core.speech.document_speech import CLOUD_ENGINES

    out: list[tuple[str, str]] = []
    for _code, engine, _voice in targets:
        if engine in CLOUD_ENGINES:
            _key, model = _cloud_credentials(frame, engine)
            out.append((engine, model))
    return out


def confirm_cloud_cost(
    frame: Any, *, translation_provider: str, targets: Any, char_count: int
) -> bool:
    """Show a combined translation + TTS estimate and ask to proceed; True = go.

    Returns True immediately when nothing metered is involved (no cloud voices and a
    free translation backend), so local-only runs are never interrupted. When a
    cloud cost is estimated, a Yes/No confirmation surfaces it before the run.
    """
    cloud = _cloud_tts_targets(frame, targets)
    from quill.core.speech.cost_estimate import estimate_combined

    estimate = estimate_combined(
        translation_provider=translation_provider,
        cloud_tts_targets=cloud,
        char_count=char_count,
        languages=len(tuple(targets)),
        ai_metered=_ai_provider_metered(),
    )
    if not estimate.is_metered:
        return True
    wx = frame._wx
    answer = frame._show_message_box(
        f"{estimate.summary()}.\n\nThis run uses metered cloud services. Proceed?",
        "Translated Speech Audio",
        wx.ICON_QUESTION | wx.YES_NO,
    )
    return answer == wx.YES


def _build_translator(req: Any) -> Any:
    """Return ``for_language(name) -> translate(text)->text`` or None when not needed.

    Loads the AI connection/key (or LibreTranslate URL) once; the per-language closure
    wraps :func:`quill.core.ai.translation.translate_text`.
    """
    if not req.translation_targets:
        return None
    from quill.core.ai.translation import translate_text
    from quill.core.assistant_ai import (
        load_assistant_api_key,
        load_assistant_connection_settings,
    )

    conn = load_assistant_connection_settings()
    api_key = load_assistant_api_key()
    provider = req.translation_provider or "ai_assistant"
    lt_url = req.libretranslate_url or "http://localhost:5000"

    def for_language(language_name: str) -> Any:
        def _translate(text: str) -> str:
            translated, _src = translate_text(text, language_name, conn, api_key, provider, lt_url)
            return translated

        return _translate

    return for_language


def _export_translations(
    frame: Any,
    req: Any,
    src: Path,
    base_final: Path,
    suffix: str,
    chapter_sound: Path | None,
    opts_fn: Any,
    for_language: Any,
    voice_blacklist: Any = None,
    temp_root: Path | None = None,
) -> int:
    """Export *src* in each configured target language; return chapters produced."""
    import shutil
    import tempfile

    from quill.core.ai.translation import LANGUAGE_NAMES
    from quill.core.speech.document_speech import (
        CLOUD_ENGINES,
        DocumentSpeechError,
        SynthesisSpec,
        synthesize_document_to_chaptered_file,
    )

    chapters = 0
    for lang_code, t_engine, t_voice in req.translation_targets:
        lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
        out = base_final.with_name(f"{base_final.stem} ({lang_name}){suffix}")
        t_dicts = _active_pronunciation_dictionaries(
            frame, t_engine, req.source_folder, language=lang_code
        )
        if t_engine in CLOUD_ENGINES:
            api_key, model = _cloud_credentials(frame, t_engine)
            if not api_key:
                frame._wx.CallAfter(
                    frame._set_status, f"Skipped {out.name} ({t_engine} API key not configured)"
                )
                continue
            t_spec = SynthesisSpec(
                engine=t_engine,
                voice=t_voice,
                rate=req.rate,
                speed=req.speed,
                api_key=api_key,
                model=model,
            )
        else:
            t_spec = SynthesisSpec(engine=t_engine, voice=t_voice, rate=req.rate, speed=req.speed)
        work = Path(
            tempfile.mkdtemp(prefix="quill_batch_tr_", dir=str(temp_root) if temp_root else None)
        )
        try:
            result = synthesize_document_to_chaptered_file(
                src,
                work / f"out{suffix}",
                t_spec,
                opts_fn(chapter_sound),
                work_dir=work / "w",
                pronunciation_dictionaries=t_dicts,
                combine_headings=req.combine_headings,
                translate=for_language(lang_name),
                voice_blacklist=voice_blacklist,
            )
            shutil.copyfile(result.with_tones_path or result.output_path, out)
            chapters += len(result.chapters)
            frame._wx.CallAfter(frame._set_status, f"{out.name}: {len(result.chapters)} chapter(s)")
        except DocumentSpeechError as exc:
            frame._wx.CallAfter(frame._set_status, f"Skipped {out.name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - isolate per-language failures
            frame._wx.CallAfter(frame._set_status, f"Error on {out.name}: {exc}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return chapters


def _current_project_dir(frame: Any) -> Path | None:
    """The active document's folder — the project a batch run is scoped to (§4.10)."""
    doc_path = getattr(frame, "_active_document_path", lambda: None)()
    if isinstance(doc_path, (str, Path)) and str(doc_path):
        parent = Path(doc_path).parent
        if parent.is_dir():
            return parent
    return None


def _apply_project_profile(frame: Any, defaults: BatchSpeechRequest) -> BatchSpeechRequest:
    """Overlay the project's remembered speech profile onto *defaults* (apply-on-open).

    Precedence is this-run > **project** > global > defaults: the dialog still wins
    (this-run), but a folder that was "remembered" pre-fills the dialog from its
    `.quill/speech-project.json` instead of the global settings.
    """
    import dataclasses

    project_dir = _current_project_dir(frame)
    if project_dir is None:
        return defaults
    from quill.core.speech.project_profile import load_profile

    profile = load_profile(project_dir)
    if profile is None:
        return defaults
    syn, ch = profile.synthesizer, profile.chapters
    fmt = profile.output.format
    if fmt not in {"mp3", "m4b", "wav"}:
        fmt = defaults.output_format
    tr = profile.translation
    return dataclasses.replace(
        defaults,
        engine=syn.engine or defaults.engine,
        voice=syn.voice or defaults.voice,
        rate=syn.rate or defaults.rate,
        speed=syn.speed or defaults.speed,
        output_format=fmt,
        sound_enabled=ch.sound_enabled,
        sound_volume=ch.sound_volume,
        article_gap_ms=ch.article_gap_ms,
        sentence_gap_ms=ch.sentence_gap_ms,
        tail_padding_ms=ch.tail_padding_ms,
        chapter_mode="separate" if ch.mode == "separate" else "single",
        combine_headings=ch.combine_headings,
        normalize_loudness=ch.normalize_loudness,
        round_robin_voices=tuple(ch.round_robin_voices),
        # Translated-export targets are remembered per project (roadmap §7).
        translation_targets=tuple((t.language, t.engine, t.voice) for t in tr.targets),
        translation_provider=tr.provider,
        libretranslate_url=tr.libretranslate_url,
        # Phase 4-6 wizard fields are part of the project profile so the
        # per-folder auto-remember covers them and "Skip to summary" stays
        # a 3-keystroke fast-path on the second run.
        book_credits=bool(profile.book_credits),
        library_mode=bool(profile.library_mode),
    )


def _save_project_profile(frame: Any, req: BatchSpeechRequest) -> None:
    """Remember this run's choices in the source folder's profile (auto-remember on Start)."""
    if not req.source_folder.is_dir():
        return
    from quill.core.speech.project_profile import (
        ChapterProfile,
        OutputProfile,
        SpeechProjectProfile,
        SynthesizerProfile,
        TranslationProfile,
        TranslationTarget,
        save_profile,
    )

    profile = SpeechProjectProfile(
        synthesizer=SynthesizerProfile(
            engine=req.engine, voice=req.voice, rate=int(req.rate), speed=float(req.speed)
        ),
        output=OutputProfile(format=req.output_format),
        chapters=ChapterProfile(
            mode=req.chapter_mode,
            sound_enabled=req.sound_enabled,
            sound_volume=req.sound_volume,
            article_gap_ms=req.article_gap_ms,
            sentence_gap_ms=req.sentence_gap_ms,
            tail_padding_ms=req.tail_padding_ms,
            combine_headings=req.combine_headings,
            normalize_loudness=req.normalize_loudness,
            round_robin_voices=tuple(req.round_robin_voices),
        ),
        translation=TranslationProfile(
            provider=req.translation_provider,
            libretranslate_url=req.libretranslate_url,
            targets=[
                TranslationTarget(language=c, engine=e, voice=v)
                for c, e, v in req.translation_targets
            ],
        ),
        # Persist the Phase 4-6 wizard flags so the next run on the same
        # folder pre-selects them in the dialog.
        book_credits=bool(req.book_credits),
        library_mode=bool(req.library_mode),
    )
    try:
        save_profile(profile, req.source_folder)
    except Exception:  # noqa: BLE001 - remembering is best-effort
        pass


def _persist_choices(frame: Any, req: BatchSpeechRequest) -> None:
    from quill.core.settings import save_settings

    s = frame.settings
    s.read_aloud_engine = req.engine
    if req.voice:
        if req.engine == "kokoro":
            s.read_aloud_kokoro_voice = req.voice
        elif req.engine == "dectalk":
            s.read_aloud_dectalk_voice = req.voice
        elif req.engine == "espeak":
            s.read_aloud_espeak_voice = req.voice
        elif req.engine == "sapi5":
            s.read_aloud_voice = req.voice
    s.read_aloud_rate = req.rate
    s.read_aloud_kokoro_speed = req.speed
    s.batch_speech_chapter_sound_enabled = req.sound_enabled
    s.batch_speech_chapter_sound_volume = req.sound_volume
    s.batch_speech_article_gap_ms = req.article_gap_ms
    s.batch_speech_sentence_gap_ms = req.sentence_gap_ms
    s.batch_speech_tail_padding_ms = req.tail_padding_ms
    s.batch_speech_temp_folder = req.temp_folder
    s.batch_speech_save_spoken_text = req.save_spoken_text
    try:
        save_settings(s)
    except Exception:  # noqa: BLE001 - persistence is best-effort
        pass


def _book_output_path(req: BatchSpeechRequest) -> Path:
    """Where the assembled audiobook is written (explicit path, or named from folder)."""
    if req.book_output_path.strip():
        return Path(req.book_output_path).with_suffix(f".{req.book_format}")
    folder = req.source_folder
    return folder / f"{folder.name}.{req.book_format}"


def _make_temp_root(req: BatchSpeechRequest) -> Path:
    """Create and return this run's scratch root under the chosen (or system) temp dir."""
    import tempfile
    from datetime import datetime

    parent = Path(req.temp_folder) if req.temp_folder.strip() else Path(tempfile.gettempdir())
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = parent / f"quill-batch-{stamp}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _prompt_chapter_plan_sync(
    frame: Any, audio_files: list[Path]
) -> list[tuple[str, list[str]]] | None | object:
    """Show the chapter editor on the UI thread and block until the user closes it.

    Returns the edited ``(title, [paths])`` plan, or ``None`` when the user cancels.
    Runs from the background task, so it marshals the modal to the UI thread via
    ``CallAfter`` and waits on an event for the result. A sentinel is unnecessary:
    the dialog always yields a plan or None, both meaningful to the caller.
    """
    import threading

    from quill.core.speech.audiobook import title_from_filename
    from quill.ui.audiobook_chapter_editor_dialog import ChapterEditorDialog

    rows = [
        (str(p), title_from_filename(p) or f"Chapter {i}")
        for i, p in enumerate(audio_files, start=1)
    ]
    holder: dict[str, Any] = {}
    done = threading.Event()

    def _show() -> None:
        try:
            dlg = ChapterEditorDialog(
                frame.frame, rows=rows, announce=getattr(frame, "_announce", None)
            )
            holder["plan"] = dlg.show(frame._show_modal_dialog)
        except Exception as exc:  # noqa: BLE001 - never wedge the worker on a UI error
            holder["plan"] = None
            holder["error"] = exc
        finally:
            done.set()

    frame._wx.CallAfter(_show)
    done.wait()
    return holder.get("plan")


def _assemble_book(
    frame: Any,
    req: BatchSpeechRequest,
    audio_files: list[Path],
    log: Any,
    *,
    plan: list[tuple[str, list[str]]] | None = None,
) -> str:
    """Combine *audio_files* into one chaptered audiobook; return a summary line.

    When *plan* is given (the user reviewed/edited chapters) it drives the chapter
    titles and any merges; otherwise one filename-derived chapter per file is used.
    """
    from quill.core.speech.audiobook import (
        build_audiobook,
        build_chapter_list,
        chapters_from_plan,
        estimate_output,
        find_cover,
        format_size,
        preflight_check,
        probe_stream_stats,
        verify_audiobook,
        write_book_sidecars,
    )
    from quill.core.speech.ffmpeg import AudioMetadata

    out = _book_output_path(req)
    # Never fold a previously built book (or this run's own target) back in as a chapter.
    sources = [p for p in audio_files if p.is_file() and p.resolve() != out.resolve()]
    if not sources:
        log.log("Audiobook: no audio files to assemble.")
        return "audiobook skipped (no audio found)"
    if plan is not None:
        chapters = chapters_from_plan([(title, [Path(p) for p in paths]) for title, paths in plan])
    else:
        chapters = build_chapter_list(sources)
    cover_text = req.book_cover_path.strip()
    cover = Path(cover_text) if cover_text else find_cover(req.source_folder)
    metadata = AudioMetadata(
        album=req.book_title or req.source_folder.name,
        artist=req.book_author,
        album_artist=req.book_narrator or req.book_author,
        genre=req.book_genre,
        year=req.book_year,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    # Pre-flight: mixed stream shapes are fine (the build re-encodes) but the
    # user should hear about them in the log before a long run.
    preflight = preflight_check([probe_stream_stats(p) for c in chapters for p in c.all_paths])
    for note in preflight.notes:
        log.log(f"Audiobook pre-flight: {note}")
    total_ms, est_bytes = estimate_output(chapters)
    log.log(
        f"Audiobook: assembling {len(chapters)} chapter(s) -> {out.name} "
        f"({req.book_format}, about {total_ms // 60000} min, ~{format_size(est_bytes)})"
    )
    result = build_audiobook(
        chapters,
        out,
        output_format=req.book_format,
        metadata=metadata,
        cover=cover if (cover and cover.is_file()) else None,
        acx_normalize=req.book_acx_normalize,
        trim_silence_files=req.trim_silence_files,
        fade_in_ms=req.book_fade_in_ms,
        fade_out_ms=req.book_fade_out_ms,
        tempo=req.book_tempo,
        on_progress=lambda m: log.log(f"Audiobook: {m}"),
    )
    for note in result.notes:
        log.log(f"Audiobook: {note}")
    try:
        for sidecar in write_book_sidecars(out, chapters, title=req.book_title):
            log.log(f"Audiobook sidecar: {sidecar.name}")
    except OSError as exc:  # sidecars are best-effort artifacts
        log.log(f"Audiobook sidecars not written: {exc}")
    # Post-build read-back: report what a player will actually see.
    verdict = verify_audiobook(out, expected_chapters=result.chapter_count)
    if verdict.ok:
        verified = f"verified {verdict.chapter_count} chapters"
    else:
        verified = "; ".join(verdict.issues) or "verification failed"
    log.log(f"Audiobook built: {result.output_path} ({verified})")
    return f"audiobook {out.name} ({verified})"


def _run(frame: Any, req: BatchSpeechRequest) -> None:
    from quill.core.speech.batch_export import discover_files
    from quill.core.speech.chapter_assemble import ChapterAssembleOptions
    from quill.core.speech.conversion_log import NullConversionLog, open_conversion_log
    from quill.core.speech.document_speech import (
        DocumentSpeechError,
        SynthesisSpec,
        synthesize_document_to_chaptered_file,
        synthesize_document_to_separate_files,
    )
    from quill.ui.ai_transcribe_dialog import AIProgressDialog

    files = discover_files(
        req.source_folder,
        list(req.extensions),
        req.recursive,
        include_glob=req.include_glob,
        exclude_glob=req.exclude_glob,
        max_file_bytes=req.max_file_bytes,
    )
    if req.audition and files:
        # Audition: one document proves the voice/pace/mastering before a long run.
        files = files[:1]
    # With audiobook assembly on, an empty document set is allowed — the run
    # assembles whatever audio is already in the folder (the pre-recorded case).
    if not files and not req.make_book:
        frame._show_message_box(
            "No matching documents were found in that folder.",
            "Batch Export to Speech Audio",
            frame._wx.ICON_INFORMATION | frame._wx.OK,
        )
        return

    # In book mode each document becomes one chapter file, so force the single-file
    # path and a plain WAV per document; the book is then assembled into its format.
    book_mode = req.make_book
    effective_format = "wav" if book_mode else req.output_format
    suffix = {"mp3": ".mp3", "m4b": ".m4b"}.get(effective_format, ".wav")

    spec = SynthesisSpec(engine=req.engine, voice=req.voice, rate=req.rate, speed=req.speed)
    dictionaries = _active_pronunciation_dictionaries(frame, req.engine, req.source_folder)
    for_language = _build_translator(req)
    # Cost surfacing (roadmap §7): when cloud translated targets are configured,
    # estimate the combined translation + TTS cost from the corpus size (a byte
    # proxy for characters) and confirm before any metered work starts.
    if for_language is not None:
        corpus_chars = sum(f.stat().st_size for f in files if f.is_file())
        if not confirm_cloud_cost(
            frame,
            translation_provider=req.translation_provider,
            targets=req.translation_targets,
            char_count=corpus_chars,
        ):
            frame._set_status("Batch speech export cancelled")
            return
    # Voice-failure blacklist (roadmap §5): known-bad voices are skipped in the
    # round-robin rotation, and any new failure this run is persisted so later runs
    # skip it too. Loaded once and saved after the batch.
    from quill.core.speech.voice_blacklist import load_blacklist, save_blacklist

    voice_blacklist = load_blacklist()

    # Incremental rebuilds (the authoring loop): fingerprint each document's
    # bytes + every audio-shaping setting; a matching, still-present output is
    # reused instead of re-synthesized. Applies only to the chaptered documents
    # path with the "overwrite" policy — skip/rename keep their own meanings —
    # and never to dry runs or auditions.
    from quill.core.speech.synth_cache import can_reuse, load_cache, save_cache
    from quill.core.speech.synth_cache import fingerprint as synth_fingerprint

    cache_settings: dict[str, object] = {
        "engine": req.engine,
        "voice": req.voice,
        "rate": req.rate,
        "speed": req.speed,
        "format": effective_format,
        "sound": [
            req.sound_enabled,
            req.sound_volume,
            str(getattr(getattr(frame, "settings", None), "batch_speech_chapter_sound_id", "")),
        ],
        "gaps": [req.article_gap_ms, req.sentence_gap_ms, req.tail_padding_ms],
        "speak_headings": req.speak_headings,
        "combine_headings": req.combine_headings,
        "normalize_loudness": req.normalize_loudness,
        "round_robin": list(req.round_robin_voices),
        "casting": [list(rule) for rule in req.casting_rules],
        "translations": [list(t) for t in req.translation_targets],
        "translation_provider": req.translation_provider,
        "dictionaries": repr(dictionaries),
    }
    reuse_enabled = (
        req.reuse_unchanged
        and req.on_existing == "overwrite"
        and req.chapter_mode == "single"
        and not req.dry_run
        and not req.audition
    )
    cache_entries: dict[str, str] = load_cache(req.source_folder) if reuse_enabled else {}

    # Open the diagnostic log in the output folder (where the audio/book lands) and
    # create this run's scratch root — both before any conversion work starts.
    out_folder = _book_output_path(req).parent if book_mode else req.source_folder
    try:
        log: Any = open_conversion_log(out_folder, title="Batch export to speech")
    except OSError:
        log = NullConversionLog()
    temp_root = _make_temp_root(req)
    log.log(f"Temporary files: {temp_root}")
    log.log(
        f"Discovered {len(files)} document(s); engine={req.engine}, voice={req.voice}, "
        f"per-document format={effective_format}, book={book_mode}, dry_run={req.dry_run}"
    )

    # A focused, non-modal progress dialog (screen reader announces it on open) that
    # can be minimized to the status bar; percentage = words processed / total words.
    progress_dialog = AIProgressDialog(
        frame.frame,
        "Batch Export to Speech Audio",
        "Preparing...",
        status_fn=frame._set_status,
    )
    # Defer the show so it runs *after* the modal config dialog has finished tearing
    # down — otherwise the closing modal reclaims focus right after our SetFocus and
    # the progress dialog opens without the screen-reader focus landing on it.
    frame._wx.CallAfter(progress_dialog.show)

    # Chunk size by engine. Kokoro's model has a small context window (~510 phoneme
    # tokens); handing it one ~8000-char call (what a heading-less document produced)
    # stalls it, which is exactly the "stuck on Preparing..." report. Keep Kokoro well
    # under that window; Piper streams sentence-by-sentence so it only needs a modest
    # cap; classic engines stay on the large cap to avoid needless per-call overhead.
    chunk_chars = {"kokoro": 1000, "piper": 4000}.get(req.engine, 8000)

    def opts(sound_path: Path | None = None) -> ChapterAssembleOptions:
        return ChapterAssembleOptions(
            article_gap_ms=req.article_gap_ms,
            sound_enabled=req.sound_enabled,
            sound_volume=req.sound_volume,
            sound_path=sound_path,
            output_format=effective_format,
            speak_headings=req.speak_headings,
            sentence_gap_ms=req.sentence_gap_ms,
            tail_padding_ms=req.tail_padding_ms,
            normalize_loudness=req.normalize_loudness,
            # Auto-chunk very long sections so a single synthesis call never runs
            # past the engine timeout; short sections are unaffected (one call).
            max_chunk_chars=chunk_chars,
        )

    total = len(files)

    def _save_spoken_sidecar(src: Path, transform_preview: Any, extract_text: Any) -> None:
        """Write the exact text sent to the engine as a ``<doc>.spoken.txt`` sidecar."""
        try:
            preview = transform_preview(
                extract_text(src),
                engine=req.engine,
                pronunciation_dictionaries=dictionaries,
            )
            out = src.with_suffix(".spoken.txt")
            out.write_text(preview.text + "\n", encoding="utf-8")
            log.log(f"Saved spoken text: {out.name}")
        except Exception as exc:  # noqa: BLE001 - sidecar capture must not break a run
            log.log(f"Could not save spoken text for {src.name}: {exc}")

    def work(_bg_progress: Any) -> object:
        from quill.core.speech.batch_export import (
            _unique_path,
            count_document_words,
            extract_text,
            transform_preview,
        )

        # Resolve the configured chapter-transition sound once for the whole run;
        # None falls back to the generated placeholder chime in chapter assembly.
        sound_dir = Path(tempfile.mkdtemp(prefix="snd_", dir=str(temp_root)))
        chapter_sound = _resolve_chapter_sound_path(frame, sound_dir) if req.sound_enabled else None
        done = skipped = errors = total_chapters = total_subs = 0
        book_summary = ""

        # Pre-count words so progress is reported as a percentage of the corpus.
        log.log("Counting words...")
        word_counts = [count_document_words(f) for f in files]
        total_words = sum(word_counts)
        log.log(f"Total words to convert: {total_words}")
        processed_words = 0

        def advance(words: int, message: str) -> None:
            """Add *words* to the processed count and push percent + message everywhere."""
            nonlocal processed_words
            processed_words += words
            pct = int(processed_words / total_words * 100) if total_words else -1
            progress_dialog.set_progress(pct, message)
            log.log(message)
            frame._wx.CallAfter(frame._set_status, message)

        try:
            for i, src in enumerate(files, start=1):
                words = word_counts[i - 1]
                log.log(f"[{i}/{total}] start {src.name} ({words} words)")
                # Leave the "Preparing..." label immediately so a single long file
                # (e.g. a heading-less document) does not look frozen while it runs.
                start_pct = int(processed_words / total_words * 100) if total_words else -1
                progress_dialog.set_progress(
                    start_pct, f"[{i}/{total}] {src.name}: synthesizing..."
                )
                if not req.dry_run and req.save_spoken_text:
                    _save_spoken_sidecar(src, transform_preview, extract_text)
                if req.dry_run:
                    try:
                        preview = transform_preview(
                            extract_text(src),
                            engine=req.engine,
                            pronunciation_dictionaries=dictionaries,
                        )
                        out = src.with_suffix(".preview.txt")
                        out.write_text(
                            f"# Dry run preview for {src.name} "
                            f"({preview.substitutions} pronunciation substitution(s))\n\n"
                            f"{preview.text}\n",
                            encoding="utf-8",
                        )
                        done += 1
                        total_subs += preview.substitutions
                        advance(
                            words,
                            f"[{i}/{total}] {src.name}: preview written "
                            f"({preview.substitutions} substitutions)",
                        )
                    except Exception as exc:  # noqa: BLE001 - isolate per-file failures
                        errors += 1
                        advance(words, f"[{i}/{total}] Error on {src.name}: {exc}")
                    continue
                if not book_mode and req.chapter_mode == "separate":
                    out_dir = src.parent / src.stem
                    if req.on_existing == "skip" and out_dir.is_dir() and any(out_dir.iterdir()):
                        skipped += 1
                        advance(words, f"[{i}/{total}] Skipped {src.name} (exists)")
                        continue
                    sep_work = Path(tempfile.mkdtemp(prefix="sep_", dir=str(temp_root)))
                    try:
                        written = synthesize_document_to_separate_files(
                            src,
                            out_dir,
                            spec,
                            opts(chapter_sound),
                            work_dir=sep_work / "w",
                            pronunciation_dictionaries=dictionaries,
                            combine_headings=req.combine_headings,
                            voice_rotation=list(req.round_robin_voices),
                            voice_blacklist=voice_blacklist,
                        )
                        done += 1
                        total_chapters += len(written)
                        advance(words, f"[{i}/{total}] {src.stem}: {len(written)} article file(s)")
                    except DocumentSpeechError as exc:
                        errors += 1
                        advance(words, f"[{i}/{total}] Skipped {src.name}: {exc}")
                    except Exception as exc:  # noqa: BLE001 - isolate per-file failures
                        errors += 1
                        advance(words, f"[{i}/{total}] Error on {src.name}: {exc}")
                    finally:
                        shutil.rmtree(sep_work, ignore_errors=True)
                    continue
                final = src.with_suffix(suffix)
                try:
                    cache_key = src.relative_to(req.source_folder).as_posix()
                except ValueError:
                    cache_key = src.name
                if reuse_enabled and can_reuse(
                    cache_entries, cache_key, src, final, cache_settings
                ):
                    skipped += 1
                    advance(words, f"[{i}/{total}] Reused {final.name} (unchanged since last run)")
                    continue
                if final.exists():
                    if req.on_existing == "skip":
                        skipped += 1
                        advance(words, f"[{i}/{total}] Skipped {src.name} (exists)")
                        continue
                    if req.on_existing == "rename":
                        final = _unique_path(final)
                    # "overwrite": leave ``final`` as-is
                work_dir = Path(tempfile.mkdtemp(prefix="doc_", dir=str(temp_root)))
                staged = work_dir / f"out{suffix}"

                def _file_progress(
                    parts_done: int,
                    parts_total: int,
                    _i: int = i,
                    _src: Path = src,
                    _words: int = words,
                ) -> None:
                    """Move the bar within a single document as each audio chunk lands."""
                    frac = parts_done / parts_total if parts_total else 1.0
                    pct = (
                        int((processed_words + frac * _words) / total_words * 100)
                        if total_words
                        else -1
                    )
                    progress_dialog.set_progress(
                        pct, f"[{_i}/{total}] {_src.name}: chunk {parts_done}/{parts_total}"
                    )

                try:
                    result = synthesize_document_to_chaptered_file(
                        src,
                        staged,
                        spec,
                        opts(chapter_sound),
                        work_dir=work_dir / "w",
                        pronunciation_dictionaries=dictionaries,
                        combine_headings=req.combine_headings,
                        voice_rotation=list(req.round_robin_voices),
                        casting_rules=list(req.casting_rules),
                        voice_blacklist=voice_blacklist,
                        on_progress=_file_progress,
                    )
                    deliverable = result.with_tones_path or result.output_path
                    shutil.copyfile(deliverable, final)
                    if reuse_enabled:
                        try:
                            cache_entries[cache_key] = synth_fingerprint(src, cache_settings)
                        except OSError:
                            pass  # an unreadable source just misses the cache
                    done += 1
                    chapter_count = len(result.chapters)
                    total_chapters += chapter_count
                    advance(words, f"[{i}/{total}] {final.name}: {chapter_count} chapter(s)")
                    if for_language is not None:
                        total_chapters += _export_translations(
                            frame,
                            req,
                            src,
                            final,
                            suffix,
                            chapter_sound,
                            opts,
                            for_language,
                            voice_blacklist,
                            temp_root,
                        )
                except DocumentSpeechError as exc:
                    errors += 1
                    advance(words, f"[{i}/{total}] Skipped {src.name}: {exc}")
                except Exception as exc:  # noqa: BLE001 - isolate per-file failures
                    errors += 1
                    advance(words, f"[{i}/{total}] Error on {src.name}: {exc}")
                finally:
                    shutil.rmtree(work_dir, ignore_errors=True)

            # Audiobook assembly: combine the produced (and any pre-recorded) audio
            # in the folder into one chaptered book.
            if book_mode and not req.dry_run:
                from quill.core.speech.audiobook import scan_audio_folder

                try:
                    if req.library_mode:
                        # Library mode: every immediate subfolder with audio becomes
                        # its own book, titled after the subfolder, unattended.
                        import dataclasses as _dc

                        built = 0
                        for sub in sorted(p for p in req.source_folder.iterdir() if p.is_dir()):
                            sub_audio = scan_audio_folder(sub, recursive=req.recursive)
                            if not sub_audio:
                                continue
                            progress_dialog.set_progress(-1, f"Building {sub.name}...")
                            sub_req = _dc.replace(
                                req, source_folder=sub, book_title=sub.name, book_output_path=""
                            )
                            try:
                                log.log(
                                    f"Library: {_assemble_book(frame, sub_req, sub_audio, log)}"
                                )
                                built += 1
                            except Exception as exc:  # noqa: BLE001 - keep building the rest
                                errors += 1
                                log.log(f"Library: {sub.name} failed: {exc}")
                        book_summary = f"library: {built} audiobook(s) built"
                        frame._wx.CallAfter(frame._set_status, book_summary)
                        raise _BookStepDone
                    audio = scan_audio_folder(req.source_folder, recursive=req.recursive)
                    if req.book_credits and files and req.book_title:
                        # Best-effort spoken frame: opening/closing credits in the
                        # run's own voice become the first and last chapters.
                        from quill.core.speech.credits import synthesize_credit_files

                        try:
                            log.log("Audiobook: synthesizing opening/closing credits...")
                            opening, closing = synthesize_credit_files(
                                req.book_title,
                                req.book_author,
                                req.book_narrator,
                                spec,
                                ChapterAssembleOptions(output_format="wav"),
                                temp_root / "credits",
                            )
                            audio = [opening, *audio, closing]
                        except Exception as exc:  # noqa: BLE001 - credits never sink a book
                            log.log(f"Audiobook: credits skipped ({exc})")
                    # Open the chapter editor when the user asked to review, or when
                    # there were no documents to synthesize (a pure pre-recorded folder,
                    # the old standalone builder's case). Cancelling skips the book.
                    plan: list[tuple[str, list[str]]] | None = None
                    if audio and (req.book_review_chapters or not files):
                        progress_dialog.set_progress(-1, "Review chapters before building...")
                        log.log("Opening the chapter editor for review...")
                        plan = _prompt_chapter_plan_sync(frame, audio)  # type: ignore[assignment]
                        if plan is None:
                            book_summary = "audiobook cancelled at chapter review"
                            log.log(book_summary)
                            frame._wx.CallAfter(frame._set_status, book_summary)
                            raise _BookReviewCancelled
                    progress_dialog.set_progress(-1, "Assembling audiobook...")
                    log.log("Assembling audiobook...")
                    book_summary = _assemble_book(frame, req, audio, log, plan=plan)
                    frame._wx.CallAfter(frame._set_status, book_summary)
                except _BookStepDone:
                    pass  # library mode built its books; the summary is already set
                except _BookReviewCancelled:
                    pass  # user cancelled the review; keep the synthesized audio, skip the book
                except Exception as exc:  # noqa: BLE001 - report, don't crash the run
                    errors += 1
                    book_summary = f"audiobook failed: {exc}"
                    log.log(book_summary)
                    frame._wx.CallAfter(frame._set_status, book_summary)

            # Persist any voices that failed this run so later runs skip them.
            save_blacklist(voice_blacklist)
            if reuse_enabled and cache_entries:
                save_cache(req.source_folder, cache_entries)
            log.log(
                f"Done: {done} done, {skipped} skipped, {errors} error(s), "
                f"{total_chapters} chapter(s). {book_summary}".strip()
            )
            return (done, skipped, errors, total_chapters, total_subs, book_summary)
        finally:
            progress_dialog.close()
            log.close()
            shutil.rmtree(temp_root, ignore_errors=True)

    def on_success(result: object) -> None:
        done, skipped, errors, total_chapters, total_subs, book_summary = result  # type: ignore[misc]
        if req.dry_run:
            frame._set_status(
                f"Dry run complete: {done} preview(s) written, {total_subs} "
                f"substitution(s), {errors} error(s)"
            )
            return
        tail = f"; {book_summary}" if book_summary else ""
        frame._set_status(
            f"Batch speech export complete: {done} done ({total_chapters} chapters), "
            f"{skipped} skipped, {errors} error(s){tail}"
        )

    frame._run_background_task(
        f"Batch speech export ({total} file(s))",
        work,
        on_success,
        notify_on_success=True,
        notify_on_error=True,
        notification_category="speech",
    )


def run_batch_export_to_speech(frame: Any) -> None:
    """Entry point bound to Tools > Speech > Audio Studio."""
    from quill.ui.audio_studio import show_audio_studio

    request = show_audio_studio(frame)
    if request is None:
        frame._set_status_quiet("Audio Studio cancelled")
        return
    _remember_sources(request)  # source MRU writes
    _persist_choices(frame, request)
    _save_project_profile(frame, request)  # auto-remember this run for the project
    _run(frame, request)


def _remember_sources(request: BatchSpeechRequest) -> None:
    """Push the request's source folder onto the Audio Studio's source MRU.

    Both the documents and audio journeys write the same MRU — the wizard
    does not distinguish between "a folder of documents" and "a folder of
    audio files" at the filesystem level, so remembering one list for both
    is the right call. The MRU write is best-effort: a corrupt store does
    not stop the run, it just means the next launch will not pre-populate
    the dropdown.
    """
    folder = getattr(request, "source_folder", None)
    if folder is None or not str(folder).strip():
        return
    try:
        from pathlib import Path

        from quill.core.recent import add_recent_audio_source_folder

        add_recent_audio_source_folder(Path(folder), limit=10)
    except Exception:  # noqa: BLE001 - MRU write is best-effort
        pass
