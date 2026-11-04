"""Captions, transcripts, listening versions, named embeds and documents as pages.

Plan: wordpress.md 9.6.

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``. This
module holds Captions for Video and Transcript for Audio; the other three rows
and the family apps' flows are in :mod:`quill.ui.wordpress_listen_pages`.

Captions and transcripts are made **on this computer**, by the offline
transcription QUILL already has: the library file is downloaded, transcribed on
a background task, and nothing is sent anywhere until the writer has reviewed
the words. Captions are reviewed as one line per cue -- its time, then its
words -- so Up and Down walk them.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import listening as ls
from quill.core.wordpress import local as lc
from quill.core.wordpress import site_media as wpm
from quill.core.wordpress.episode import TRANSCRIPT_SUMMARY
from quill.core.wordpress.listen_engines import download
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_listen_pages import WordPressListenPages

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

_WHAT = {
    "video": ("Captions for Video", "&Video:", "captions", "a video"),
    "audio": ("Transcript for Audio", "&Audio file:", "a transcript", "an audio file"),
}

CAPTIONS_HELP = (
    "One caption on each line: its start and end time, then the words. Correct the words, "
    "change a speaker's label to their name, or add a sound in square brackets, like "
    "[applause]. Keep each time as it is unless you mean to move the caption."
)
TRANSCRIPT_HELP = (
    "The transcript, one paragraph per speaker or every few sentences. Correct anything "
    "misheard and change speaker labels to names before it goes into the page."
)
PLACEMENTS = (
    "Folded under the player, as Read the transcript (recommended)",
    "In full under the player",
)


class WordPressListenCommands(WordPressListenPages):
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    def cmd_captions(self) -> None:
        self._transcribe_from_library("video")

    def cmd_transcript(self) -> None:
        self._transcribe_from_library("audio")

    # ------------------------------------------------------------------ #

    def _transcribe_from_library(self, kind: str) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        api = self.api(profile)  # type: ignore[attr-defined]
        self.background(  # type: ignore[attr-defined]
            f"reading the {kind} files on {profile.name}",
            lambda: list(wpm.list_media(api, media_type=kind)),
            lambda items: self._choose_and_transcribe(kind, copy, profile, api, items),
        )

    def _choose_and_transcribe(
        self,
        kind: str,
        copy: lc.WorkingCopy,
        profile: st.SiteProfile,
        api: Any,
        items: list[wpm.MediaItem],
    ) -> None:
        title, prompt, making, noun = _WHAT[kind]
        if not items:
            self.host.announce(
                f"There is no {kind} in {profile.name}'s Media Library yet. Upload {noun} "
                "first, then try again."
            )
            return
        text = self.host.current_text()
        initial = next((i for i, m in enumerate(items) if m.source_url and m.source_url in text), 0)
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title=title,
            prompt=prompt,
            rows=[m.spoken() for m in items],
            initial=initial,
            help_text=(
                f"Choose the {kind} to make {making} for. One already in this document is "
                "selected. It is transcribed on this computer; nothing is sent until you have "
                "reviewed the words."
            ),
        )
        if index is None:
            return
        media = items[index]
        name = media.title or media.filename
        self.host.announce(
            f"Making {making} for {name} on this computer. This can take a few minutes; "
            "the review opens when it is done."
        )
        engines = self.listen_engines()

        def work() -> Any:
            with tempfile.TemporaryDirectory(prefix="quill-wp-media-") as folder:
                local_file = Path(folder) / (media.filename or f"media-{media.id}")
                download(api, media.source_url, local_file)
                return engines.transcribe(local_file)

        def done(result: Any) -> None:
            if kind == "video":
                self._review_captions(copy, profile, api, media, result)
            else:
                self._review_transcript(copy, profile, media, result)

        self.background(f"transcribing {name}", work, done)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # captions (9.6)

    def _review_captions(
        self,
        copy: lc.WorkingCopy,
        profile: st.SiteProfile,
        api: Any,
        media: wpm.MediaItem,
        result: Any,
    ) -> None:
        name = media.title or media.filename
        cues = ls.cues_from_segments(
            getattr(result, "segments", ()),
            str(getattr(result, "full_text", "") or ""),
            float(getattr(result, "duration_seconds", 0.0) or 0.0),
        )
        if not cues:
            self.host.announce(f"No speech was found in {name}, so there are no captions to make.")
            return
        text = ls.review_text(cues)
        while True:
            edited = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Review Captions",
                prompt="&Captions, one on each line with its time:",
                value=text,
                multiline=True,
                help_text=CAPTIONS_HELP,
            )
            if edited is None:
                return
            try:
                cues = ls.cues_from_review(edited)
                break
            except ls.CaptionsError as exc:
                self.host.announce(str(exc.args[0]))
                text = edited
        language = str(getattr(result, "language", "") or "en")
        srclang = language.split("-", 1)[0].lower() or "en"
        label = ls.language_label(srclang)
        vtt = ls.to_webvtt(cues).encode("utf-8")
        file_name = f"{Path(media.filename or name).stem}.{srclang}.vtt"

        def work() -> wpm.MediaItem:
            return wpm.upload_media(
                api, file_name, vtt, "text/vtt", title=f"Captions for {name}", post=media.post
            )

        def done(track: wpm.MediaItem) -> None:
            where = self._wire_track(copy, media, track.source_url, label, srclang)
            self.host.announce(
                f"Captions uploaded to {profile.name} and added to {where}. Visitors get them "
                "when you next Save Draft to Site or Publish."
            )

        self.background(f"uploading the captions for {name}", work, done)  # type: ignore[attr-defined]

    def _wire_track(
        self, copy: lc.WorkingCopy, media: wpm.MediaItem, src: str, label: str, srclang: str
    ) -> str:
        """Attach the captions to the video's block, or insert the video with them."""
        text = self.host.current_text()
        track = (src, label, srclang)
        if copy.text_format == "html":
            span = ls.find_media_block(text, "core/video", media.id, media.source_url)
            if span is not None:
                block = ls.add_track(text[span.start : span.end], *track)
                self.host.replace_text(text[: span.start] + block + text[span.end :])
                return "the video in this document"
            self.host.insert_text("\n" + ls.video_block(media.id, media.source_url, track=track))
            return "a new video block at the caret"
        islands = dict(copy.properties.get("islands") or {})
        token = ls.find_media_island(islands, "core/video", media.id, media.source_url)
        if token and ls.island_line(text, token) is not None:
            islands[token] = ls.add_track(islands[token], *track)
            where = "the video in this document"
        else:
            token = ls.new_island_token(islands, "video")
            islands[token] = ls.video_block(media.id, media.source_url, track=track)
            self.host.insert_text("\n" + ls.island_fence("core/video", token, "video") + "\n")
            where = "a new video block at the caret"
        self._save_islands(copy, islands)
        return where

    def _save_islands(self, copy: lc.WorkingCopy, islands: dict[str, str]) -> None:
        fresh = self.local.copy_for_path(self.host.current_path()) or copy
        fresh.properties["islands"] = islands
        self.local.save(fresh)

    # ------------------------------------------------------------------ #
    # transcripts (9.6)

    def _review_transcript(
        self, copy: lc.WorkingCopy, profile: st.SiteProfile, media: wpm.MediaItem, result: Any
    ) -> None:
        name = media.title or media.filename
        body = ls.transcript_paragraphs(
            getattr(result, "segments", ()), str(getattr(result, "full_text", "") or "")
        )
        if not body.strip():
            self.host.announce(f"No speech was found in {name}, so there is no transcript.")
            return
        edited = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Review Transcript",
            prompt="&Transcript:",
            value=body,
            multiline=True,
            help_text=TRANSCRIPT_HELP,
        )
        if edited is None or not edited.strip():
            return
        placement = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Insert Transcript",
            prompt="&Insert it:",
            rows=list(PLACEMENTS),
            help_text=(
                "Folded keeps the page short: visitors open Read the transcript when they want "
                "it. In full puts every paragraph on the page."
            ),
        )
        if placement is None:
            return
        snippet = self._transcript_snippet(copy.text_format, edited, folded=placement == 0)
        where = self._place_under_audio(copy, media, snippet)
        self.host.announce(f"Transcript of {name} added {where}.")
        del profile

    @staticmethod
    def _transcript_snippet(text_format: str, body: str, *, folded: bool) -> str:
        if folded:
            if text_format == "html":
                return ls.details_html(TRANSCRIPT_SUMMARY, body)
            return ls.details_markdown(TRANSCRIPT_SUMMARY, body)
        paragraphs = [" ".join(p.split()) for p in body.split("\n\n") if p.strip()]
        if text_format == "html":
            return "".join(
                f"<!-- wp:paragraph -->\n<p>{_esc(p)}</p>\n<!-- /wp:paragraph -->\n\n"
                for p in paragraphs
            ).strip()
        return "\n\n".join(paragraphs)

    def _place_under_audio(self, copy: lc.WorkingCopy, media: wpm.MediaItem, snippet: str) -> str:
        text = self.host.current_text()
        end = -1
        if copy.text_format == "html":
            span = ls.find_media_block(text, "core/audio", media.id, media.source_url)
            end = span.end if span is not None else -1
        else:
            islands = dict(copy.properties.get("islands") or {})
            token = ls.find_media_island(islands, "core/audio", media.id, media.source_url)
            line = ls.island_line(text, token) if token else None
            end = line.end if line is not None else -1
        if end >= 0:
            self.host.go_to_offset(end)
            self.host.insert_text("\n\n" + snippet + "\n")
            return "under its player"
        if copy.text_format == "html":
            player = ls.audio_block(media.id, media.source_url)
        else:
            islands = dict(copy.properties.get("islands") or {})
            token = ls.new_island_token(islands, "audio")
            islands[token] = ls.audio_block(media.id, media.source_url)
            self._save_islands(copy, islands)
            player = ls.island_fence("core/audio", token, "audio")
        self.host.insert_text("\n" + player + "\n\n" + snippet + "\n")
        return "at the caret, under a new player"


def _esc(text: str) -> str:
    import html

    return html.escape(text, quote=False)
