"""File > WordPress > Media and Files: the Picture Maker and the site logo.

Plan: wordpress.md 6.9, 6.10 (Visual Review, 6.11, is the base class in
:mod:`quill.ui.wordpress_review_commands`).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``.

The Picture Maker is the one Studio has always had: the window is
:class:`quill.ui.studio_picture_maker.PictureMakerDialog` and the work is
:mod:`quill.core.ai.picture_maker`, so there is one implementation for
three apps. A made picture is saved on this computer only; it reaches the
site when the person chooses Insert into Document (or Use as Site Logo).
"""

from __future__ import annotations

import mimetypes
import os
import shutil
from collections.abc import Callable
from itertools import islice
from pathlib import Path
from typing import Any

from quill.core.ai import picture_maker as pm
from quill.core.wordpress import local as lc
from quill.core.wordpress import site_media as wpm
from quill.core.wordpress import visual_review as vr
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.media_alt import DESCRIBE_QUESTION
from quill.ui import studio_picture_maker as maker
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui import wordpress_picture_ai as pai
from quill.ui.wordpress_review_commands import WordPressReviewCommands

_LIBRARY_LIMIT = 300


class WordPressPictureCommands(WordPressReviewCommands):
    # ------------------------------------------------------------------ #
    # the Picture Maker (6.9)

    def cmd_picture_maker(self) -> None:
        self.open_picture_maker()

    def open_picture_maker(
        self, *, use: Callable[[Path], None] | None = None, use_label: str = "", use_help: str = ""
    ) -> None:
        ai = pai.editor_of(self.host)
        if not pai.switched_on(ai, self.host.announce):
            return
        connection = pm.picture_connection(own_key_provider=pai.own_key_provider(ai))
        if isinstance(connection, str):
            self.host.announce(connection)
            return
        folder = self.local.root / "pictures"
        warned: list[bool] = []

        def request(
            turns: list[str],
            size: str,
            done: Callable[[Path, str], None],
            failed: Callable[[str], None],
            background: str = "normal",
            colour: str = "",
        ) -> None:
            if pm.asks_for_screenshot(" ".join(turns)) and not warned:
                warned.append(True)
                failed(pm.SCREENSHOT_NOTE)
                return
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Make the Picture",
                message=pm.consent_message(connection, described_by="your chosen AI"),
                yes_label="Make the Picture",
            ):
                failed("Nothing was sent.")
                return
            self.host.announce("Making the picture. This can take a minute.")

            def made(picture: pm.MadePicture) -> None:
                done(picture.path, f"Asked for:\n{picture.prompt}")
                self.describe_picture(picture.path)

            self.host.run_task(
                "WordPress: making a picture",
                lambda: pm.make_picture(
                    connection, turns, size, folder, background=background, colour=colour
                ),
                made,
                lambda exc: failed(f"No picture was made: {exc}"),
            )

        page = maker.PageExtras(
            transparent=connection.can_make_transparent,
            suggest=lambda fill: self.suggest_picture(ai, fill),
            describe=self.describe_picture,
            open_viewer=lambda path: open_in_viewer(path),
            save_as=self.save_picture_as,
            insert=use or self.insert_made_picture,
            **({"insert_label": use_label, "insert_help": use_help} if use_label else {}),
        )
        maker.open_picture_maker(
            self.host.parent,
            self.host.show_modal,
            request=request,
            make_video=None,
            announce=self.host.announce,
            title="Picture Maker",
            page=page,
        )

    def suggest_picture(self, ai: Any, fill: Callable[[pm.PictureSuggestion], None]) -> None:
        """Suggest from Page Content: the selection, or the whole page, to the chosen AI."""
        selected = self.host.selected_text().strip()
        text = selected or self.host.current_text().strip()
        if not text:
            self.host.announce("There is no text on the page to suggest a picture from.")
            return

        def answered(answer: str) -> None:
            suggestion = pm.parse_suggestion(answer)
            if suggestion is None:
                self.host.announce(
                    "The AI's answer had no picture description in it, so nothing was changed. "
                    "Try again, or describe the picture yourself."
                )
                return
            fill(suggestion)
            self.host.announce(f"Suggestion ready. {suggestion.why}".strip())

        what = "the selection" if selected else "the page's text"
        self.host.announce(f"Sending {what} to your chosen AI for a picture suggestion.")
        pai.ask_text(ai, pm.suggestion_prompt(text), answered, self.host.announce)

    def describe_picture(self, path: Path) -> None:
        """Describe Image on a made picture: a fresh look at the actual file (6.8)."""

        def show(answer: str) -> None:
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title=f"Describe Image: {path.name}",
                text=answer,
                help_text=(
                    "What is actually in the picture, from a separate look by your chosen AI, "
                    "not the description it was made from."
                ),
            )

        self.host.ai_describe_image(path, DESCRIBE_QUESTION, show, self.host.announce)

    def save_picture_as(self, path: Path) -> None:
        target = ask_save_picture(self.host, path)
        if target is None:
            return
        try:
            shutil.copyfile(path, target)
        except OSError as exc:
            self.host.announce(f"The copy was not saved: {exc}. Choose another folder.")
            return
        self.host.announce(f"Saved a copy as {target.name}.")

    def insert_made_picture(self, path: Path) -> None:
        """Insert into Document: the image dialog, then upload on Insert (6.7)."""
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        answer = idlg.ask_image(
            self.host.parent,
            self.host.show_modal,
            name=path.name,
            size_text=picture_size_text(path),
            on_describe=lambda: self.describe_picture(path),
        )
        if answer is None:
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def upload() -> wpm.MediaItem:
            return wpm.upload_media(
                api,
                path.name,
                path.read_bytes(),
                mimetypes.guess_type(path.name)[0] or "image/png",
                alt_text=answer.alt,
                caption=answer.caption,
                post=copy.remote_id,
            )

        def inserted(item: wpm.MediaItem) -> None:
            self.host.insert_text(
                vr.picture_markup(
                    copy.text_format, item.source_url, answer.alt, answer.caption, item.id
                )
            )
            if answer.featured:
                fresh = self.local.copy_for_path(self.host.current_path()) or copy
                fresh.properties["featured_media"] = item.id
                self.local.save(fresh)
            self.host.announce(f"Picture uploaded to {profile.name} and inserted.")

        self.background("uploading the picture", upload, inserted)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # the site logo (6.10)

    def cmd_site_logo(self) -> None:
        found = self.local.copy_for_path(self.host.current_path())
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return
        profile = store.get(found.site_id) if found is not None else None
        profile = profile or self.pick_site(store, "Site Logo")  # type: ignore[attr-defined]
        if profile is None:
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        self.background(
            "reading the site logo",
            lambda: read_logos(api),
            lambda state: self.show_logos(profile, api, state),
        )

    def show_logos(self, profile: Any, api: Any, state: LogoState) -> None:
        if state.refused:
            self.host.announce(
                f"Site Logo needs the Administrator role on {profile.name}: changing the logo "
                "needs the manage_options permission, and your account does not have it."
            )
            return
        settings = [s for s in state.settings if s.supported]
        if not any(s.key == "site_logo" for s in settings):
            self.host.announce(
                f"{profile.name} does not use the standard site logo. Its theme uses a header "
                "image or a page builder's own logo, which belong to the theme's own controls."
            )
            return

        def rows() -> list[str]:
            return [
                f"{s.label}: "
                + (
                    state.media[s.key].spoken()
                    if s.key in state.media
                    else ("media item " + str(s.media_id) if s.media_id else "none set")
                )
                for s in settings
            ]

        def chosen(index: int | None) -> vr.LogoSetting:
            return settings[index if index is not None and index < len(settings) else 0]

        def from_library(index: int | None) -> object:
            setting = chosen(index)

            def pick(items: list[wpm.MediaItem]) -> None:
                if not items:
                    self.host.announce(
                        f"There are no images in the Media Library on {profile.name}."
                    )
                    return
                picked = dlg.ask_choice(
                    self.host.parent,
                    self.host.show_modal,
                    title=f"{setting.label} from the Library",
                    prompt="&Image:",
                    rows=[i.spoken() for i in items],
                    initial=0,
                    help_text="Images in the site's Media Library, newest first.",
                )
                if picked is not None:
                    item = items[picked]
                    self.replace_logo(profile, api, setting, item.id, item.title or item.filename)

            self.background(
                "reading the Media Library",
                lambda: list(islice(wpm.list_media(api, media_type="image"), _LIBRARY_LIMIT)),
                pick,
            )
            return None

        def from_file(index: int | None) -> object:
            path = ask_open_picture(self.host)
            if path is not None:
                self.replace_logo_with_file(profile, api, chosen(index), path)
            return None

        def from_maker(index: int | None) -> object:
            setting = chosen(index)
            self.open_picture_maker(
                use=lambda path: self.replace_logo_with_file(profile, api, setting, path),
                use_label=f"&Use as {setting.label}...",
                use_help=f"Upload the chosen version and make it the {setting.label.lower()} on "
                f"{profile.name}, after you confirm.",
            )
            return None

        def preview(_index: int | None) -> object:
            width = self.ask_width("Preview a Logo Width")
            if width is not None:
                self.review(
                    profile,
                    profile.site_url,
                    style=vr.logo_width_style(width),
                    proposal=f"the site logo shown {width} pixels wide",
                )
            return None

        def restore(_index: int | None) -> object:
            history = vr.load_logo_history(self.local.root, profile.id)
            if not history:
                self.host.announce(f"QUILL has not replaced a logo or icon on {profile.name}.")
                return None
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Restore Earlier",
                prompt="&Earlier logos and icons:",
                rows=[
                    f"{r['label']} {r['media_id'] or 'none'}, replaced {r['when']}" for r in history
                ],
                initial=0,
                help_text="What QUILL replaced on this site, newest first.",
            )
            if picked is None:
                return None
            row = history[picked]
            setting = next((s for s in settings if s.key == row["key"]), None)
            if setting is not None:
                earlier = int(row["media_id"])
                self.replace_logo(
                    profile,
                    api,
                    setting,
                    earlier,
                    f"media item {earlier}" if earlier else f"no {setting.label.lower()}",
                )
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Site Logo: {profile.name}",
            purpose=(
                "The logo the theme shows on every page, and the small site icon. Replacing "
                "one never removes the old image from the Media Library."
            ),
            list_label="&Logo and icon:",
            list_help="The site's logo and icon: the file, its real size and its alt text.",
            rows=rows(),
            actions=[
                dlg.Action(
                    "From the &Library...",
                    "Replace the selected one with an image already in the Media Library.",
                    from_library,
                ),
                dlg.Action(
                    "From a &File...", "Upload a picture from this computer and use it.", from_file
                ),
                dlg.Action(
                    "From the &Picture Maker...", "Make a picture with AI and use it.", from_maker
                ),
                dlg.Action(
                    "Pre&view a Width...",
                    "Visual Review of the home page with the logo "
                    "at a width you choose; nothing on the site changes.",
                    preview,
                    needs_row=False,
                ),
                dlg.Action(
                    "&Restore Earlier...",
                    "Put back a logo or icon QUILL replaced.",
                    restore,
                    needs_row=False,
                ),
            ],
        )
        window.Destroy()

    def replace_logo_with_file(
        self, profile: Any, api: Any, setting: vr.LogoSetting, path: Path
    ) -> None:
        self.replace_logo(profile, api, setting, 0, path.name, path=path)

    def replace_logo(
        self,
        profile: Any,
        api: Any,
        setting: vr.LogoSetting,
        media_id: int,
        name: str,
        *,
        path: Path | None = None,
    ) -> None:
        """Named confirmation, a fresh read (conflict-safe), then the setting; never a delete."""
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title=f"Replace {setting.label}",
            message=(
                f"Make {name} the {setting.label.lower()} on {profile.name}? The current one "
                "stays in the Media Library, and Restore Earlier can put it back."
            ),
            yes_label=f"Replace {setting.label}",
        ):
            return

        def work() -> str:
            now = read_logos(api)
            current = next((s for s in now.settings if s.key == setting.key), None)
            if current is None or current.media_id != setting.media_id:
                return "changed"
            new_id = media_id
            if path is not None:
                new_id = wpm.upload_media(
                    api,
                    path.name,
                    path.read_bytes(),
                    mimetypes.guess_type(path.name)[0] or "image/png",
                    title=path.stem,
                ).id
            api.post("wp/v2/settings", {setting.key: new_id})
            vr.remember_logo(
                self.local.root,
                profile.id,
                key=setting.key,
                media_id=setting.media_id,
                label=setting.label,
                when=lc.now_stamp(),
            )
            return "done"

        def done(outcome: str) -> None:
            if outcome == "changed":
                self.host.announce(
                    f"Nothing was sent: the {setting.label.lower()} on {profile.name} was changed "
                    "since this window opened. Close it and open Site Logo again."
                )
                return
            self.host.announce(f"The {setting.label.lower()} on {profile.name} is now {name}.")

        self.background(f"replacing the {setting.label.lower()}", work, done)  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# helpers


class LogoState:
    def __init__(
        self, settings: list[vr.LogoSetting], media: dict[str, wpm.MediaItem], refused: bool = False
    ) -> None:
        self.settings = settings
        self.media = media
        self.refused = refused


def read_logos(api: Any) -> LogoState:
    """The logo and icon settings and the media behind them; ``refused`` without the right."""
    try:
        payload = api.get("wp/v2/settings")
    except WordPressApiError as exc:
        if exc.status in (401, 403):
            return LogoState([], {}, refused=True)
        raise
    settings = vr.logo_settings(payload)
    media: dict[str, wpm.MediaItem] = {}
    for setting in settings:
        if setting.media_id:
            try:
                media[setting.key] = wpm.media_from_payload(
                    api.get(f"wp/v2/media/{setting.media_id}", context="edit")
                )
            except WordPressApiError:
                pass  # said as "media item N"
    return LogoState(settings, media)


def picture_size_text(path: Path) -> str:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return f"Image is {image.width} by {image.height}"
    except (OSError, ValueError):
        return "Image size unknown"


def open_in_viewer(path: Path) -> None:
    """Open a picture in the viewer Windows uses for it."""
    os.startfile(str(path))  # noqa: S606 - the user's own picture, opened by its association


def ask_open_picture(host: Any) -> Path | None:
    import wx

    dialog = wx.FileDialog(
        host.parent,
        "Choose a Picture",
        wildcard="Pictures|*.png;*.jpg;*.jpeg;*.gif;*.webp",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    )
    try:
        if host.show_modal(dialog, "Choose a Picture") != wx.ID_OK:
            return None
        return Path(dialog.GetPath())
    finally:
        dialog.Destroy()


def ask_save_picture(host: Any, path: Path) -> Path | None:
    import wx

    dialog = wx.FileDialog(
        host.parent,
        "Save the Picture As",
        defaultFile=path.name,
        wildcard="PNG picture|*.png",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    )
    try:
        if host.show_modal(dialog, "Save the Picture As") != wx.ID_OK:
            return None
        return Path(dialog.GetPath())
    finally:
        dialog.Destroy()
