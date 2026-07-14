"""Automatic source-language detection on paste/typing (#181 follow-up).

A thin mixin on :class:`~quill.ui.main_frame.MainFrame` that debounces content
changes and, for an *unpinned* untitled/``.txt`` document, runs the wx-free
:mod:`quill.core.language_detect` scorer. What it does with a confident guess is
governed by ``settings.language_detection_mode``:

- ``"off"``     — never runs (default).
- ``"hint"``    — quietly shows "Looks like X" in the status bar; nothing else.
- ``"prompt"``  — announces a dismissible suggestion to set the language.
- ``"auto"``    — sets the Document Language automatically (with a spoken note).

It never overrides a real file extension or a language the user pinned, mirrors
VS Code's debounce + confidence discipline, and — unlike VS Code's silent/visual
switch — keeps a screen-reader user informed instead of surprised.
"""

from __future__ import annotations

_DETECT_DEBOUNCE_MS = 800
_MIN_CHARS_TO_DETECT = 24
_GENERIC_TEXT_SUFFIXES = {"", ".txt", ".text", ".log"}


class LanguageDetectMixin:
    """Debounced, mode-driven Document Language auto-detection."""

    # Relies on MainFrame: _wx, settings, editor, document, _current_tab,
    # set_document_language, _announce, _set_status.

    def _language_detection_eligible(self) -> bool:
        """Only untitled / generic-text documents that the user has not pinned."""
        tab = getattr(self, "_current_tab", None)
        if tab is None or getattr(tab, "_language_profile_pinned", False):
            return False
        path = self.document.path
        if path is None:
            return True
        return path.suffix.lower() in _GENERIC_TEXT_SUFFIXES

    def _schedule_language_detection(self) -> None:
        """Debounce a detection pass; safe to call on every keystroke/paste."""
        mode = str(getattr(self.settings, "language_detection_mode", "off") or "off")
        if mode == "off" or not self._language_detection_eligible():
            return
        wx = self._wx
        timer = getattr(self, "_language_detect_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - a dead timer must not break typing
                pass
        self._language_detect_timer = wx.CallLater(
            _DETECT_DEBOUNCE_MS, self._run_language_detection
        )

    def _note_language_session_use(self, name: str) -> None:
        """Remember a chosen language this session to bias future detection."""
        if not name or name == "Plain text":
            return
        bias = getattr(self, "_language_session_bias", None)
        if bias is None:
            bias = {}
            self._language_session_bias = bias
        bias[name] = min(bias.get(name, 0.0) + 1.0, 4.0)

    def _run_language_detection(self) -> None:
        from quill.core.language_detect import detect_language, should_switch

        mode = str(getattr(self.settings, "language_detection_mode", "off") or "off")
        if mode == "off" or not self._language_detection_eligible():
            return
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        text = editor.GetValue()
        if len(text) < _MIN_CHARS_TO_DETECT:
            return
        # Braille content is not a programming language; if it looks like ASCII
        # braille, suggest Braille Mode instead of a code profile.
        from quill.core.brf_ascii import looks_like_braille

        if looks_like_braille(text):
            self._maybe_suggest_braille_mode(mode)
            return
        result = detect_language(text, bias=getattr(self, "_language_session_bias", None))
        if result.language is None:
            return
        tab = getattr(self, "_current_tab", None)
        current = getattr(getattr(tab, "_language_profile", None), "name", None)
        if not should_switch(current, result):
            return
        if result.language == getattr(self, "_last_language_suggestion", None):
            return  # already suggested/applied; don't nag while they keep typing
        self._last_language_suggestion = result.language
        self._act_on_language_detection(mode, result.language, result.confidence)

    def _maybe_suggest_braille_mode(self, mode: str) -> None:
        """Offer Braille Mode for pasted ASCII-braille (never auto-enters a mode).

        Entering Braille Mode changes the whole editing surface, so even in
        "auto" this only suggests — it does not switch for you.
        """
        if getattr(self, "_last_language_suggestion", None) == "__braille__":
            return  # already suggested; don't nag
        self._last_language_suggestion = "__braille__"
        if mode == "hint":
            self._set_status(
                "Looks like Braille — use Help > Enable Braille Mode to open it as braille."
            )
        else:  # prompt or auto
            message = (
                "This looks like Braille. Use Help, Enable Braille Mode to open it "
                "as a braille document."
            )
            self._set_status(message)

    def _act_on_language_detection(self, mode: str, language: str, confidence: float) -> None:
        percent = int(round(confidence * 100))
        if mode == "auto":
            # set_document_language announces, updates the status bar, and gives
            # the Save As hint; prefix a short note so the switch is never silent.
            self._announce(f"Detected {language} ({percent} percent).")
            self.set_document_language(language)
        elif mode == "prompt":
            message = (
                f"This looks like {language}. Press Ctrl+Shift+L, then Enter, "
                f"to set the document language."
            )
            self._set_status(message)
        else:  # "hint" — visible only, no speech
            self._set_status(
                f"Looks like {language} ({percent}%) — press Ctrl+Shift+L to set the language."
            )
