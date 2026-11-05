"""Suggest Alt Text and Describe Image, wired to the editor's own AI (wordpress.md 6.8, 10).

A mixin of :class:`~quill.ui.wordpress_media_commands.WordPressMediaCommands`.
Nothing new is invented: the picture goes through the editor's Ask About an
Image route (``host.ai_describe_image``), with the same switch, connection and
first-picture agreement. Each action says what it sends before it sends it.
A suggestion only ever lands in a field to be read and changed; nothing here
saves alt text by itself.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress import media_alt as ma
from quill.core.wordpress import media_tools as mt
from quill.core.wordpress import site_media as wpm
from quill.ui import wordpress_dialogs as dlg

#: Where a library picture is kept while the AI looks at it.
_PICTURES = "QUILL WordPress pictures"


class WordPressMediaAi:
    # Provided by WordPressCommands.
    host: Any

    def _picture_file(
        self, source: object, api: Any, name: str, then: Callable[[Path], None]
    ) -> None:
        """A file on this computer for *source*: a path, bytes, a library item or an address."""
        if isinstance(source, Path):
            then(source)
            return
        if isinstance(source, bytes):
            then(temp_picture(name, source))
            return
        address = source.source_url if isinstance(source, wpm.MediaItem) else str(source)
        if address.lower().startswith(("https://", "http://")):
            if api is None:
                self.host.announce(f"{name} is on the web, and QUILL has no site to fetch it from.")
                return
            self.background(  # type: ignore[attr-defined]
                f"fetching {name}",
                lambda: temp_picture(
                    name, mt.download_file(api._opener, address, any_type=True).content
                ),
                then,
            )
            return
        from quill.core.ai.doc_images import resolve_image_source

        found = resolve_image_source(address, self.host.current_path())
        if found is None:
            self.host.announce(f"{name} is not on this computer, so the AI cannot look at it.")
            return
        then(found if isinstance(found, Path) else temp_picture(name, found))

    def _ask_ai(self, path: Path, question: str, on_answer: Callable[[str], None]) -> None:
        ask = getattr(self.host, "ai_describe_image", None)
        if not callable(ask):
            self.host.announce("AI help is not available in this window.")
            return

        def failed(said: str) -> None:
            reason = (said or "no reason was given").rstrip(".")
            self.host.announce(f"The AI did not answer: {reason}.")

        ask(path, question, on_answer, failed)

    def _suggest_alt(
        self,
        source: object,
        api: Any,
        name: str,
        context: ma.ImageContext,
        fill: Callable[[str], None],
        on_fuller: Callable[[str], None] | None = None,
    ) -> None:
        """Suggest Alt Text: the picture and the words around it go to the chosen AI."""
        sent = "the picture" + (" and the text around it" if any(vars_of(context)) else "")
        self.host.announce(f"Suggest Alternative Text sends {sent} to your chosen AI.")

        def answered(text: str) -> None:
            suggestion = ma.clean_suggestion(text)
            if suggestion.decorative:
                self.host.announce(
                    f"Your AI thinks {name} is decorative. Check Decorative if you agree."
                )
                return
            if not suggestion.alt:
                self.host.announce(
                    "Your AI gave no suggestion. Write the alternative text yourself."
                )
                return
            fill(suggestion.alt)
            if suggestion.fuller and on_fuller is not None:
                on_fuller(suggestion.fuller)

        self._picture_file(
            source,
            api,
            name,
            lambda path: self._ask_ai(path, ma.alt_text_question(context), answered),
        )

    def _describe(self, source: object, api: Any, name: str) -> None:
        """Describe Image: the picture alone goes to the chosen AI; the answer is for you."""
        self.host.announce("Describe Image sends the picture to your chosen AI.")

        def answered(text: str) -> None:
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title=f"Describe Image: {name}",
                text=text.strip() or "Your AI gave no description.",
                help_text=(
                    "What your AI sees in the picture, for you rather than for visitors: "
                    "subject, arrangement, colours, any words, and any problems."
                ),
            )

        self._picture_file(
            source, api, name, lambda path: self._ask_ai(path, ma.DESCRIBE_QUESTION, answered)
        )


def vars_of(context: ma.ImageContext) -> list[str]:
    return [context.heading, context.before, context.after, context.caption, context.link]


def temp_picture(name: str, content: bytes) -> Path:
    folder = Path(tempfile.gettempdir()) / _PICTURES
    folder.mkdir(parents=True, exist_ok=True)
    filename = mt.safe_filename(name or "picture", "picture")
    sniffed = mt.picture_extension(content)
    if sniffed and not filename.lower().endswith(("." + sniffed, ".jpeg")):
        filename = filename.rsplit(".", 1)[0] + "." + sniffed
    target = folder / filename
    target.write_bytes(content)
    return target
