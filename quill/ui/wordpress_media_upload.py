"""Uploading: many files, a pasted picture, a file by web address (wordpress.md 6.2, 6.4).

A mixin of :class:`~quill.ui.wordpress_media_commands.WordPressMediaCommands`.
Every upload goes the same way: details first (alt text first, for a
picture), then a check of the library for the same file, then one file at a
time with its progress spoken, a failed file saying why while the rest carry
on, and one sentence at the end.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import media_tools as mt
from quill.core.wordpress import site_media as wpm
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui import wordpress_media_dialogs as mdlg
from quill.ui.wordpress_site_commands import picture_markup

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


@dataclass
class UploadEntry:
    filename: str
    content: bytes
    content_type: str
    title: str = ""
    alt: str = ""
    caption: str = ""
    reuse: wpm.MediaItem | None = None


@dataclass(frozen=True)
class UploadResult:
    entry: UploadEntry
    media: wpm.MediaItem | None
    problem: str = ""


class WordPressMediaUpload:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    # ------------------------------------------------------------------ #
    # the one upload path

    def _upload_batch(
        self,
        profile: st.SiteProfile,
        api: Any,
        entries: list[UploadEntry],
        done: Callable[[list[UploadResult]], None],
    ) -> None:
        """Check for duplicates, then upload one file at a time, saying how far along."""

        def find() -> list[wpm.MediaItem | None]:
            found: list[wpm.MediaItem | None] = []
            for entry in entries:
                try:
                    found.append(wpm.find_duplicate_media(api, entry.filename, len(entry.content)))
                except Exception:  # noqa: BLE001 - a failed check only means "upload it"
                    found.append(None)
            return found

        def ask(duplicates: list[wpm.MediaItem | None]) -> None:
            for entry, twin in zip(entries, duplicates, strict=True):
                if twin is not None and dlg.confirm(
                    self.host.parent,
                    self.host.show_modal,
                    title="Already in the Library",
                    message=(
                        f"{entry.filename} is already in {profile.name}'s Media Library, as "
                        f"{twin.title or twin.filename}. Use the one already there instead of "
                        "uploading a second copy?"
                    ),
                    yes_label="Use the One There",
                ):
                    entry.reuse = twin
            self._upload_next(profile, api, entries, 0, [], done)

        self.background(  # type: ignore[attr-defined]
            f"checking {profile.name}'s library for the same files", find, ask
        )

    def _upload_next(
        self,
        profile: st.SiteProfile,
        api: Any,
        entries: list[UploadEntry],
        index: int,
        results: list[UploadResult],
        done: Callable[[list[UploadResult]], None],
    ) -> None:
        if index >= len(entries):
            done(results)
            return
        entry = entries[index]
        if entry.reuse is not None:
            results.append(UploadResult(entry, entry.reuse))
            self._upload_next(profile, api, entries, index + 1, results, done)
            return
        if len(entries) > 1:
            self.host.announce(f"Uploading {index + 1} of {len(entries)}: {entry.filename}.")
        else:
            self.host.announce(f"Uploading {entry.filename} to {profile.name}.")

        def work() -> UploadResult:
            from quill.ui.wordpress_commands import failure_sentence

            try:
                media = wpm.upload_media(
                    api,
                    entry.filename,
                    entry.content,
                    entry.content_type,
                    title=entry.title,
                    alt_text=entry.alt,
                    caption=entry.caption,
                )
            except Exception as exc:  # noqa: BLE001 - one failed file never stops the rest
                return UploadResult(entry, None, failure_sentence(exc))
            return UploadResult(entry, media)

        def next_one(result: UploadResult) -> None:
            results.append(result)
            self._upload_next(profile, api, entries, index + 1, results, done)

        self.background(f"uploading {entry.filename} to {profile.name}", work, next_one)  # type: ignore[attr-defined]

    def _details_for(self, name: str, content: bytes, site_name: str) -> mdlg.UploadDetails | None:
        """The upload details dialog for one file, with Suggest for a picture."""
        is_image = mt.content_type_for(name).startswith("image/")
        return mdlg.ask_upload_details(
            self.host.parent,
            self.host.show_modal,
            name=name,
            site_name=site_name,
            is_image=is_image,
            title=default_title(name),
            on_suggest_async=(
                (lambda fill: self._suggest_alt(content, None, name, _no_context(), fill))  # type: ignore[attr-defined]
                if is_image
                else None
            ),
            on_describe=(
                (lambda: self._describe(content, None, name)) if is_image else None  # type: ignore[attr-defined]
            ),
        )

    # ------------------------------------------------------------------ #
    # the commands

    def cmd_upload_files(self) -> None:
        target = self._media_site("Upload Files")  # type: ignore[attr-defined]
        if target is None:
            return
        profile, _copy = target
        paths = mdlg.choose_files(self.host.parent, self.host.show_modal, title="Upload Files")
        if not paths:
            return
        entries: list[UploadEntry] = []
        skipped = 0
        for path in paths:
            try:
                content = path.read_bytes()
            except OSError as exc:
                self.host.announce(
                    f"{path.name} could not be read: {exc.strerror or exc}. The others carry on."
                )
                skipped += 1
                continue
            details = self._details_for(path.name, content, profile.name)
            if details is None:
                skipped += 1
                continue
            entries.append(
                UploadEntry(
                    path.name,
                    content,
                    mt.content_type_for(path.name),
                    title=details.title,
                    alt=details.alt,
                    caption=details.caption,
                )
            )
        if not entries:
            self.host.announce(f"Nothing was uploaded to {profile.name}.")
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        self._upload_batch(
            profile,
            api,
            entries,
            lambda results: self.host.announce(upload_summary(profile.name, results, skipped)),
        )

    def cmd_paste_image(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        read = getattr(self.host, "clipboard_image_png", None)
        png = read() if callable(read) else None
        if not png:
            self.host.announce(
                "There is no picture on the clipboard. Copy a picture first, then choose "
                "Paste Image."
            )
            return
        context = self._caret_context()  # type: ignore[attr-defined]
        fuller: list[str] = []
        answer = idlg.ask_image(
            self.host.parent,
            self.host.show_modal,
            name="Pasted picture",
            size_text=bytes_size_text(png),
            on_suggest_async=lambda fill: self._suggest_alt(  # type: ignore[attr-defined]
                png, None, "pasted-picture.png", context, fill, fuller.append
            ),
            on_describe=lambda: self._describe(png, None, "pasted-picture.png"),  # type: ignore[attr-defined]
        )
        if answer is None:
            return
        filename = mt.pasted_picture_name(answer.alt, datetime.now())
        entry = UploadEntry(
            filename,
            png,
            "image/png",
            title=" ".join(answer.alt.split()[:10]) or "Pasted picture",
            alt=answer.alt,
            caption=answer.caption,
        )

        def place(results: list[UploadResult]) -> None:
            result = results[0]
            if result.media is None:
                self.host.announce(f"The picture was not uploaded. {result.problem}")
                return
            media = result.media
            self.host.insert_text(
                picture_markup(copy.text_format, media.source_url, answer, media_id=media.id)
            )
            if answer.featured:
                fresh = self.local.copy_for_path(self.host.current_path()) or copy
                fresh.properties["featured_media"] = media.id
                self.local.save(fresh)
            self.host.announce(f"Picture inserted: {answer.alt or media.filename}.")
            self._offer_fuller(copy, fuller)  # type: ignore[attr-defined]

        self._upload_batch(profile, self.api(profile), [entry], place)  # type: ignore[attr-defined]

    def cmd_upload_from_address(self) -> None:
        target = self._media_site("Upload from Web Address")  # type: ignore[attr-defined]
        if target is None:
            return
        profile, _copy = target
        address = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Upload from Web Address",
            prompt="&Address:",
            help_text=(
                "The https:// address of a picture, sound, video or document. QUILL fetches it "
                f"from that site onto this computer, then uploads it to {profile.name}."
            ),
        )
        if not address or not address.strip():
            return
        try:
            host = mt.check_download_address(address)
        except mt.MediaDownloadError as exc:
            self.host.announce(exc.user_message())
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def got(file: mt.Downloaded) -> None:
            details = self._details_for(file.filename, file.content, profile.name)
            if details is None:
                self.host.announce(f"Nothing was uploaded to {profile.name}.")
                return
            entry = UploadEntry(
                file.filename,
                file.content,
                file.content_type,
                title=details.title,
                alt=details.alt,
                caption=details.caption,
            )
            self._upload_batch(
                profile,
                api,
                [entry],
                lambda results: self.host.announce(upload_summary(profile.name, results)),
            )

        self.host.announce(f"Fetching the file from {host}.")
        self.background(  # type: ignore[attr-defined]
            f"fetching the file from {host}",
            lambda: mt.download_file(api._opener, address, timeout=max(api.timeout, 30.0)),
            got,
        )


# --------------------------------------------------------------------------- #
# helpers with no wx in them, tested directly


def upload_summary(site_name: str, results: list[UploadResult], skipped: int = 0) -> str:
    """One sentence for a finished upload: how many, how many reused, and what failed."""
    uploaded = [r for r in results if r.media is not None and r.entry.reuse is None]
    reused = [r for r in results if r.entry.reuse is not None]
    failed = [r for r in results if r.media is None]
    parts: list[str] = []
    if len(results) == 1 and uploaded:
        parts.append(f"{uploaded[0].entry.filename} uploaded to {site_name}.")
    elif uploaded:
        parts.append(f"{len(uploaded)} of {len(results)} files uploaded to {site_name}.")
    elif not reused:
        parts.append(f"Nothing was uploaded to {site_name}.")
    if reused:
        parts.append(
            f"{len(reused)} {'was' if len(reused) == 1 else 'were'} already there and "
            f"{'is' if len(reused) == 1 else 'are'} used as they are."
        )
    for result in failed:
        parts.append(f"{result.entry.filename} did not upload: {result.problem}")
    if skipped:
        parts.append(f"{skipped} skipped.")
    return " ".join(parts)


def default_title(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    words = " ".join(stem.replace("_", " ").replace("-", " ").split())
    return words[:1].upper() + words[1:]


def bytes_size_text(content: bytes) -> str:
    import io

    from quill.core.wordpress.site import human_size

    try:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
        return f"image is {width} by {height}, {human_size(len(content))}"
    except Exception:  # noqa: BLE001 - a picture Pillow cannot read still uploads
        return human_size(len(content))


def _no_context() -> Any:
    from quill.core.wordpress.media_alt import ImageContext

    return ImageContext()
