"""Listening versions, named embeds, documents as pages, and the family apps' posts.

Split from :mod:`quill.ui.wordpress_listen_commands` for size (GATE-11); the
same mixin rules apply (wordpress.md 9.6, 15 item 9):

* **Make a Listening Version** reads the page with the person's own Read Aloud
  voice into an MP3 on this computer, uploads it, and puts an audio block at the
  top with a plain label. Asked again, it says whether the recording is still
  up to date, and a new one replaces the old.
* **Name Embeds** asks the site's oEmbed proxy what each embedded link is and
  gives every unnamed embed a caption, so no visitor meets an unnamed frame.
* **Publish a Document as a Page** converts a PDF or Word file with Import /
  Convert Document, uploads the original, and opens the text as a new page
  draft linked to it.
* :meth:`post_episode` and :meth:`upload_file` are what QUILL Cast, QUILL Studio
  and Quill Converter reach through :mod:`quill.ui.wordpress_family`: the same
  code, with a host that has no editor.
"""

from __future__ import annotations

import mimetypes
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import episode as ep
from quill.core.wordpress import listening as ls
from quill.core.wordpress import local as lc
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_media as wpm
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.listen_engines import Converted, ListenEngines, default_engines
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_listen_dialogs as ldlg

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class WordPressListenPages:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    def listen_engines(self) -> ListenEngines:
        """Transcription, speech and conversion; tests set ``_listen_engines``."""
        engines = getattr(self, "_listen_engines", None)
        return engines if engines is not None else default_engines()

    # ------------------------------------------------------------------ #
    # Make a Listening Version

    def cmd_listening_version(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        noun = "page" if copy.kind == "page" else "post"
        islands = dict(copy.properties.get("islands") or {})
        copy.text = ls.strip_listening_block(self.host.current_text(), copy.text_format, islands)
        html_text = self.to_html(copy)[0]  # type: ignore[attr-defined]
        if not wp.plain_text(html_text):
            self.host.announce(
                f"There is nothing to read yet. Write the {noun} first, then make its "
                "listening version."
            )
            return
        stamp = ls.fingerprint(copy.title + " " + wp.plain_text(html_text))
        previous = copy.properties.get("listening_version") or {}
        if previous:
            if previous.get("fingerprint") == stamp:
                message = (
                    f"The listening version is up to date with this {noun}. Make it again anyway?"
                )
            else:
                message = (
                    f"The listening version is out of date: the {noun} has changed since it was "
                    "recorded. Make it again? The new recording replaces the old one at the top."
                )
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Make a Listening Version",
                message=message,
                yes_label="Make Again",
            ):
                return
        self.host.announce(
            "Recording the listening version on this computer with your Read Aloud voice. "
            "This can take a few minutes."
        )
        engines = self.listen_engines()
        api = self.api(profile)  # type: ignore[attr-defined]
        file_name = f"{wp.slugify(copy.title) or 'untitled'}-listen.mp3"

        def work() -> tuple[wpm.MediaItem, int]:
            with tempfile.TemporaryDirectory(prefix="quill-wp-listen-") as folder:
                out = Path(folder) / file_name
                length = engines.speak(copy.title, html_text, out)
                media = wpm.upload_media(
                    api,
                    file_name,
                    out.read_bytes(),
                    "audio/mpeg",
                    title=f"Listening version: {copy.title or 'untitled'}",
                    post=copy.remote_id,
                )
            return media, length

        def done(answer: tuple[wpm.MediaItem, int]) -> None:
            media, length = answer
            label = ls.listening_label(copy.kind, length)
            block = ls.listening_audio_block(media.id, media.source_url, label)
            fresh = self.local.copy_for_path(self.host.current_path()) or copy
            isles = dict(fresh.properties.get("islands") or {})
            body = ls.strip_listening_block(self.host.current_text(), copy.text_format, isles)
            if copy.text_format == "html":
                self.host.replace_text(block + "\n\n" + body.lstrip("\n"))
            else:
                for token in [t for t, markup in isles.items() if ls.LISTEN_MARK in markup]:
                    del isles[token]
                token = ls.new_island_token(isles, "listen")
                isles[token] = block
                fence = ls.island_fence("core/audio", token, "listen")
                self.host.replace_text(fence + "\n\n" + body.lstrip("\n"))
                fresh.properties["islands"] = isles
            fresh.properties["listening_version"] = {
                "media_id": media.id,
                "url": media.source_url,
                "fingerprint": stamp,
            }
            self.local.save(fresh)
            length_text = ls.minutes_label(length)
            said = f", {length_text}" if length_text else ""
            self.host.announce(
                f"Listening version uploaded to {profile.name}{said}. It is at the top of the "
                f"{noun}, labelled {label}."
            )

        self.background("recording the listening version", work, done)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Name Embeds

    def cmd_name_embeds(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        text = self.host.current_text()
        islands = dict(copy.properties.get("islands") or {})
        embeds = ls.find_embeds(text, copy.text_format, islands)
        if not embeds:
            self.host.announce("This document has no embeds to name.")
            return
        todo = [e for e in embeds if not e.captioned]
        if not todo:
            self.host.announce("Every embed in this document already has a caption.")
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        urls = list(dict.fromkeys(e.url for e in todo))

        def work() -> dict[str, ls.OEmbedInfo | str]:
            answers: dict[str, ls.OEmbedInfo | str] = {}
            for url in urls:
                try:
                    answers[url] = ls.oembed(api, url)
                except WordPressApiError as exc:
                    answers[url] = exc.plain
            return answers

        def done(answers: dict[str, ls.OEmbedInfo | str]) -> None:
            self._apply_embed_names(copy, profile, text, islands, todo, answers, len(embeds))

        self.background(f"asking {profile.name} what each embed is", work, done)  # type: ignore[attr-defined]

    def _apply_embed_names(
        self,
        copy: lc.WorkingCopy,
        profile: st.SiteProfile,
        text: str,
        islands: dict[str, str],
        todo: list[ls.Embed],
        answers: dict[str, ls.OEmbedInfo | str],
        total: int,
    ) -> None:
        from quill.core.wordpress import fences

        lines: list[str] = []
        named = 0
        new_text = text
        for embed in sorted(todo, key=lambda e: e.span.start, reverse=True):
            info = answers.get(embed.url)
            if not isinstance(info, ls.OEmbedInfo):
                lines.append(f"{embed.url}: not named. {info or 'The site did not answer.'}")
                continue
            if not info.title:
                lines.append(
                    f"{embed.url}: {profile.name} could not say what this is. Add a caption "
                    "by hand."
                )
                continue
            caption = info.caption()
            if embed.where == "island":
                islands[embed.token] = ls.caption_embed(islands[embed.token], caption)
            elif embed.where == "html":
                piece = ls.caption_embed(new_text[embed.span.start : embed.span.end], caption)
                new_text = new_text[: embed.span.start] + piece + new_text[embed.span.end :]
            else:
                line = new_text[embed.span.start : embed.span.end]
                markup = ls.caption_embed(fences.markdown_to_blocks(line).strip(), caption)
                token = ls.new_island_token(islands, "embed")
                islands[token] = markup
                fence = ls.island_fence("core/embed", token, embed.url)
                new_text = new_text[: embed.span.start] + fence + new_text[embed.span.end :]
            named += 1
            by = f", by {info.author}" if info.author else ""
            lines.append(f"{info.provider or 'Link'}: {info.title}{by}. Caption added.")
        if new_text != text:
            self.host.replace_text(new_text)
        if copy.text_format == "markdown" and named:
            fresh = self.local.copy_for_path(self.host.current_path()) or copy
            fresh.properties["islands"] = islands
            self.local.save(fresh)
        already = total - len(todo)
        head = f"{named} of {len(todo)} embeds named"
        head += f"; {already} already had a caption." if already else "."
        dlg.show_report(
            self.host.parent,
            self.host.show_modal,
            title="Name Embeds",
            text=head + "\n\n" + "\n".join(reversed(lines)),
            help_text=(
                "What each embedded link is, as the site's oEmbed service describes it, and "
                "whether a caption was added. Captions go to the site with your next send."
            ),
        )

    # ------------------------------------------------------------------ #
    # Publish a Document as a Page

    def cmd_document_as_page(self) -> None:
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return
        found = self.local.copy_for_path(self.host.current_path())
        profile = store.get(found.site_id) if found else None
        profile = profile or self.pick_site(store, "Publish a Document as a Page")  # type: ignore[attr-defined]
        if profile is None:
            return
        path = ldlg.pick_file(
            self.host.parent,
            self.host.show_modal,
            title="Publish a Document as a Page",
            wildcard=ldlg.DOCUMENT_WILDCARD,
        )
        if path is not None:
            self.document_as_page(profile, path)

    def document_as_page(self, profile: st.SiteProfile, path: Path) -> None:
        title = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Publish a Document as a Page",
            prompt="Page &title:",
            value=ep.title_from_file(path.name),
            help_text=(
                "The new page's title. The document is converted on this computer, the original "
                "is uploaded to the Media Library, and the page opens as a draft linked to it."
            ),
        )
        if not title or not title.strip():
            return
        title = title.strip()
        self.host.announce(f"Converting {path.name} on this computer.")
        engines = self.listen_engines()

        def converted(result: Converted) -> None:
            if result.needs_ocr and dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Publish a Document as a Page",
                message=(
                    f"{path.name} has no readable text: it looks scanned. Read its pages with "
                    "OCR on this computer? Nothing is uploaded to read them."
                ),
                yes_label="Read the Pages",
            ):
                self.background(  # type: ignore[attr-defined]
                    f"reading the pages of {path.name}",
                    lambda: engines.convert_ocr(path),
                    lambda again: self._upload_document(profile, path, title, again),
                )
                return
            self._upload_document(profile, path, title, result)

        self.background(f"converting {path.name}", lambda: engines.convert(path), converted)  # type: ignore[attr-defined]

    def _upload_document(
        self, profile: st.SiteProfile, path: Path, title: str, result: Converted
    ) -> None:
        if not result.text.strip():
            self.host.announce(
                f"{path.name} has no text QUILL could read, so there is nothing to make a page "
                "from. Nothing was uploaded."
            )
            return
        self.upload_with_reuse(
            profile,
            path,
            title=title,
            then=lambda media: self._open_document_page(profile, path, title, result, media),
        )

    def _open_document_page(
        self,
        profile: st.SiteProfile,
        path: Path,
        title: str,
        result: Converted,
        media: wpm.MediaItem,
    ) -> None:
        size = media.filesize or _size(path)
        copy = lc.WorkingCopy(
            site_id=profile.id,
            kind="page",
            local_id=lc.new_local_id(),
            title=title,
            text=ep.document_page(
                result.text, file_name=path.name, src=media.source_url, size=size
            ),
            text_format="markdown",
            properties={"slug": wp.slugify(title), "source_document": media.id},
        )
        self.host.open_path(self.local.write_document(copy))
        self.host.announce(
            f"{path.name} is in {profile.name}'s Media Library, and its text is open as a new "
            "page draft. Nothing is published until you choose Publish."
        )

    # ------------------------------------------------------------------ #
    # uploads shared by the documents and the family apps

    def upload_with_reuse(
        self, profile: st.SiteProfile, path: Path, *, title: str, then: Any
    ) -> None:
        """Upload *path*, offering the library's own copy when it is already there (6.2)."""
        api = self.api(profile)  # type: ignore[attr-defined]
        size = _size(path)

        def upload() -> None:
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.background(  # type: ignore[attr-defined]
                f"uploading {path.name} to {profile.name}",
                lambda: wpm.upload_media(
                    api, path.name, path.read_bytes(), content_type, title=title
                ),
                then,
            )

        def checked(existing: wpm.MediaItem | None) -> None:
            if existing is not None and dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Already in the Library",
                message=(
                    f"{path.name} is already in {profile.name}'s Media Library. Use the one "
                    "already there? Cancel uploads a second copy."
                ),
                yes_label="Use That One",
            ):
                then(existing)
                return
            upload()

        self.background(  # type: ignore[attr-defined]
            f"looking for {path.name} in {profile.name}'s Media Library",
            lambda: wpm.find_duplicate_media(api, path.name, size),
            checked,
        )

    def upload_file(self, path: Path) -> None:
        self.upload_files([path])

    def upload_files(self, paths: list[Path]) -> None:
        """Quill Converter's Upload to WordPress: files to the library, addresses copied."""
        present = [p for p in paths if p.is_file()]
        if not present:
            names = ", ".join(p.name for p in paths) or "That file"
            self.host.announce(f"{names} is not on this computer any more, so nothing was sent.")
            return
        profile = self._family_site("Upload to WordPress")
        if profile is None:
            return
        addresses: list[str] = []

        def finish() -> None:
            self.host.set_clipboard_text("\n".join(addresses))
            if len(present) == 1:
                self.host.announce(
                    f"{present[0].name} is in {profile.name}'s Media Library. Its address is "
                    "copied."
                )
            else:
                self.host.announce(
                    f"{len(present)} files are in {profile.name}'s Media Library. Their "
                    "addresses are copied, one on each line."
                )

        def send(index: int) -> None:
            if index >= len(present):
                finish()
                return
            path = present[index]
            if len(present) > 1:
                self.host.announce(f"Uploading {index + 1} of {len(present)}: {path.name}.")

            def sent(media: wpm.MediaItem) -> None:
                addresses.append(media.source_url)
                send(index + 1)

            self.upload_with_reuse(profile, path, title=ep.title_from_file(path.name), then=sent)

        send(0)

    def post_episode(self, episode: ep.Episode) -> None:
        """Post This Episode: upload the audio, then draft a post around its player."""
        audio = episode.audio_path
        if audio is None or not audio.is_file():
            self.host.announce(
                f"{episode.title or 'This episode'} has no audio file on this computer yet. "
                "Download or export it first, then try again."
            )
            return
        profile = self._family_site("Post This Episode")
        if profile is None:
            return
        if episode.transcript.strip() or not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Post This Episode",
            message=(
                f"{episode.title} has no transcript. Make one on this computer first, so the "
                "post carries it? Cancel posts the episode without one."
            ),
            yes_label="Make a Transcript",
        ):
            self._post_episode_audio(profile, episode)
            return
        self.host.announce(
            f"Making a transcript of {episode.title} on this computer. This can take a few minutes."
        )
        engines = self.listen_engines()

        def transcribed(result: Any) -> None:
            body = ls.transcript_paragraphs(
                getattr(result, "segments", ()), str(getattr(result, "full_text", "") or "")
            )
            from dataclasses import replace

            self._post_episode_audio(profile, replace(episode, transcript=body))

        self.background(  # type: ignore[attr-defined]
            f"transcribing {episode.title}", lambda: engines.transcribe(audio), transcribed
        )

    def _post_episode_audio(self, profile: st.SiteProfile, episode: ep.Episode) -> None:
        audio = episode.audio_path
        assert audio is not None

        def uploaded(media: wpm.MediaItem) -> None:
            text, islands = ep.episode_post(episode, media_id=media.id, src=media.source_url)
            copy = lc.WorkingCopy(
                site_id=profile.id,
                kind="post",
                local_id=lc.new_local_id(),
                title=episode.title,
                text=text,
                text_format="markdown",
                properties={"slug": wp.slugify(episode.title), "islands": islands},
            )
            path = self.local.write_document(copy)
            self.host.announce(
                f"{episode.title} is uploaded to {profile.name}, and its post is a local draft "
                "with the player, show notes, chapters and transcript. Nothing is published "
                "until you choose Publish."
            )
            self.host.open_path(path)

        self.upload_with_reuse(profile, audio, title=episode.title, then=uploaded)

    def _family_site(self, title: str) -> st.SiteProfile | None:
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return None
        return self.pick_site(store, title)  # type: ignore[no-any-return,attr-defined]


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
