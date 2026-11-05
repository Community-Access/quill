"""File > WordPress > Media and Files: Visual Review, and Preview and Review (wordpress.md 6.11).

A base of :class:`~quill.ui.wordpress_picture_commands.WordPressPictureCommands`
(split for GATE-11), so it reaches the editor only through ``self.host`` and
the site only through ``self.api`` inside ``self.background``.

The order is the honest one. The page is captured first, on this computer,
which sends nothing anywhere but a normal visit to the public page. Then the
person is told exactly what would go to the AI, and only a Yes sends it. The
report says what it could not see: unpublished changes, a cached copy, and
images that failed, had not finished, or were not captured.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import page_capture as pc
from quill.core.wordpress import visual_review as vr
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_picture_ai as pai

_DOC_IMAGE = re.compile(r'!\[[^\]]*\]\(([^\s)"]+)|<img\b[^>]*\bsrc="([^"]+)"', re.IGNORECASE)

NOT_PUBLISHED = (
    "Visual Review looks at the published page, and this is not published on {site} yet. "
    "Publish it first. A draft opens only for someone signed in to WordPress in a browser, "
    "so QUILL cannot capture it."
)


class WordPressReviewCommands:
    host: Any
    local: Any

    def cmd_visual_review(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        if not copy.link or copy.status != "publish":
            self.host.announce(NOT_PUBLISHED.format(site=profile.name))
            return
        self.review(profile, copy.link, copy=copy)

    def cmd_preview_and_review(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        if not copy.link or copy.status != "publish":
            self.host.announce(vr.PREVIEW_NEEDS_PUBLISHED)
            return
        names = document_images(self.host.current_text())
        rows = [f"The picture {name}" for name in names] + ["The site logo"]
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Preview and Review",
            prompt="&Preview a new width for:",
            rows=rows,
            initial=0,
            help_text=(
                "Choose what to show at a different width. The width is put into a captured copy "
                "of the published page only; nothing on the site changes."
            ),
        )
        if index is None:
            return
        width = self.ask_width("Preview and Review")
        if width is None:
            return
        if index < len(names):
            style = vr.image_width_style(names[index], width)
            proposal = f"the picture {names[index]} shown {width} pixels wide"
        else:
            style = vr.logo_width_style(width)
            proposal = f"the site logo shown {width} pixels wide"
        self.review(profile, copy.link, copy=copy, style=style, proposal=proposal)

    # ------------------------------------------------------------------ #

    def ask_width(self, title: str) -> int | None:
        typed = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title=title,
            prompt="&Width in pixels:",
            help_text=(
                "How wide to show it, in pixels, such as 600. The height follows, so the "
                "proportions are kept."
            ),
        )
        if typed is None:
            return None
        text = typed.strip().lower().removesuffix("px").strip()
        if not text.isdigit() or not 16 <= int(text) <= 4000:
            self.host.announce("Type a width in pixels between 16 and 4000, such as 600.")
            return None
        return int(text)

    def review(
        self,
        profile: Any,
        url: str,
        *,
        copy: lc.WorkingCopy | None = None,
        style: str = "",
        proposal: str = "",
    ) -> None:
        """Capture *url*, say what would be sent, and send it only on Yes."""
        title = "Preview and Review" if style else "Visual Review"
        ai = pai.editor_of(self.host)
        if not pai.switched_on(ai, self.host.announce):
            return
        folder = self.local.root / "visual-review" / _safe(profile.id)

        def work() -> tuple[pc.Capture, Path]:
            capture = pc.capture_page(url, folder, style=style)
            return capture, vr.combine_screenshots(capture, folder / "both.png")

        def captured(result: tuple[pc.Capture, Path]) -> None:
            capture, sheet = result
            notes = []
            if copy is not None and self.unpublished_changes(copy):
                notes.append(vr.UNPUBLISHED_NOTE)
            if copy is not None:
                notes.append(pc.cache_note(capture.headers, copy.base_modified_gmt))
            if proposal:
                notes.append(
                    f"This previews {proposal}. It was put into the captured copy only; "
                    "nothing on the site changed."
                )
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title=title,
                message=vr.consent_text(profile.name, url, capture),
                yes_label="Send for Review",
            ):
                self.host.announce(f"Nothing was sent. The screenshots are in {folder}.")
                return
            question = vr.review_instruction(
                capture, proposal=proposal, unpublished=vr.UNPUBLISHED_NOTE in notes
            )

            def show(answer: str) -> None:
                text = vr.report_text(profile.name, capture, answer, notes=notes)
                saved = folder / "review.txt"
                saved.write_text(text, encoding="utf-8")
                text += (
                    f"\n\nThis report is saved as text in {saved}. After you Update the page, "
                    f"choose {title} again to review it again."
                )
                dlg.show_report(
                    self.host.parent,
                    self.host.show_modal,
                    title=title,
                    text=text,
                    help_text=(
                        "What a sighted visitor sees on the published page, on a desktop and a "
                        "phone, then image by image. Each finding is labelled likely a problem, "
                        "a design choice you may want, or worth checking."
                    ),
                )

            self.host.ai_describe_image(sheet, question, show, self.host.announce)

        self.host.announce(f"Capturing the desktop and phone views of {url}.")
        self.background("capturing the page", work, captured)  # type: ignore[attr-defined]

    def unpublished_changes(self, copy: lc.WorkingCopy) -> bool:
        """Whether the editor's text differs from what was last published."""
        published = next(
            (v for v in self.local.versions(copy.key) if v.reason == lc.REASON_PUBLISHED), None
        )
        if published is None:
            return False
        return self.host.current_text().strip() != published.text.strip()


def document_images(text: str) -> list[str]:
    """The file names of the pictures in a document, in order, once each."""
    names: list[str] = []
    for match in _DOC_IMAGE.finditer(text or ""):
        address = match.group(1) or match.group(2) or ""
        name = address.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
        if name and name not in names:
            names.append(name)
    return names


def _safe(part: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in part) or "site"
