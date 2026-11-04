"""The WordPress item windows: New, Properties and the image dialog (wordpress.md 5.1, 5.5, 6.7).

Split from :mod:`quill.ui.wordpress_dialogs`, which holds the shared shapes
(connect, lists, reports, confirmations); the same rules apply: standard
controls only, F1 help on every control, no network.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import wx

from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.wordpress_dialogs import ShowModal, _buttons, _row

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

# --------------------------------------------------------------------------- #
# New Page / New Post (5.1)


class CheckGroup(wx.ScrolledWindow):
    """A titled run of real check boxes, one per term (A11Y-SR-1).

    A check list box reads each row's name but not whether it is checked, so a
    listener cannot tell which categories a post is in. Separate check boxes
    say their state on every move. Scrolls when a site has many terms.
    """

    def __init__(self, parent: wx.Window, names: list[str], *, help_text: str) -> None:
        super().__init__(parent, style=wx.TAB_TRAVERSAL | wx.VSCROLL)
        column = wx.BoxSizer(wx.VERTICAL)
        self.boxes: list[wx.CheckBox] = []
        for name in names:
            box = wx.CheckBox(self, label=name.replace("&", "&&"))
            box.SetHelpText(help_text)
            column.Add(box, 0, wx.ALL, 2)
            self.boxes.append(box)
        self.SetSizer(column)
        self.SetScrollRate(0, 10)
        self.SetMinSize(dip_size(self, 300, 120 if len(names) > 4 else 30 * max(1, len(names))))
        self.SetHelpText(help_text)

    def Check(self, index: int, value: bool = True) -> None:  # noqa: N802 - wx's name
        self.boxes[index].SetValue(value)

    def GetCheckedItems(self) -> list[int]:  # noqa: N802 - wx's name
        return [i for i, box in enumerate(self.boxes) if box.GetValue()]


def _check_group(
    sizer: wx.Sizer, parent: wx.Window, title: str, names: list[str], help_text: str
) -> CheckGroup:
    box = wx.StaticBoxSizer(wx.VERTICAL, parent, title)
    group = CheckGroup(box.GetStaticBox(), names, help_text=help_text)
    box.Add(group, 1, wx.EXPAND | wx.ALL, 4)
    sizer.Add(box, 1, wx.EXPAND | wx.ALL, 8)
    return group


@dataclass
class NewItemAnswer:
    site_index: int
    title: str
    slug: str
    text_format: str  # "markdown" or "html"
    category_ids: list[int] = field(default_factory=list)
    tag_ids: list[int] = field(default_factory=list)


class NewItemDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        kind_label: str,
        sites: Sequence[str],
        site_index: int,
        last_format: str,
        categories: Sequence[tuple[int, str]] = (),
        tags: Sequence[tuple[int, str]] = (),
    ) -> None:
        super().__init__(
            parent, title=f"New {kind_label}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.SetHelpText(
            f"Start a new {kind_label.lower()}. Nothing is sent to the site until you choose Save"
            f" Draft to "
            "Site or Publish."
        )
        self._slug_touched = False
        self._categories = list(categories)
        self._tags = list(tags)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.site = wx.Choice(self, choices=list(sites))
        self.site.SetHelpText(
            "Which of your sites this belongs to. It stays with that site for good."
        )
        self.site.SetSelection(max(0, site_index))
        _row(sizer, self, "&Site:", self.site)
        self.title = wx.TextCtrl(self)
        self.title.SetHelpText(
            "The title. Your theme shows it at the top of the page, so the body does not need it "
            "again as "
            "a heading."
        )
        self.title.Bind(wx.EVT_TEXT, self._on_title)
        _row(sizer, self, "&Title:", self.title)
        self.slug = wx.TextCtrl(self)
        self.slug.SetHelpText(
            "The last part of the web address. It is filled in from the title as you type; leave "
            "it to keep "
            "the suggestion."
        )
        self.slug.Bind(wx.EVT_TEXT, self._on_slug)
        _row(sizer, self, "S&lug:", self.slug)
        self.text_format = wx.RadioBox(
            self,
            label="Write in",
            choices=["Markdown", "HTML"],
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS,
        )
        self.text_format.SetHelpText(
            "Markdown is readable text characters for headings, lists and links; QUILL turns it "
            "into HTML "
            "when you send it. HTML is for exact control. This cannot change later."
        )
        self.text_format.SetSelection(1 if last_format == "html" else 0)
        sizer.Add(self.text_format, 0, wx.EXPAND | wx.ALL, 8)
        self.category_list: CheckGroup | None = None
        self.tag_list: CheckGroup | None = None
        if self._categories or self._tags:
            self.category_list = _check_group(
                sizer,
                self,
                "Categories",
                [name for _i, name in self._categories],
                "Check each category this post belongs to. Space checks or unchecks.",
            )
            self.tag_list = _check_group(
                sizer,
                self,
                "Tags",
                [name for _i, name in self._tags],
                "Check each tag for this post. Space checks or unchecks.",
            )
        sizer.Add(_buttons(self, "Create"), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)

    def _on_title(self, _event: object) -> None:
        if not self._slug_touched:
            from quill.core.wordpress.site import slugify

            self.slug.ChangeValue(slugify(self.title.GetValue()))

    def _on_slug(self, _event: object) -> None:
        self._slug_touched = True

    def answer(self) -> NewItemAnswer:
        def checked(box: CheckGroup | None, items: list[tuple[int, str]]) -> list[int]:
            if box is None:
                return []
            return [items[i][0] for i in box.GetCheckedItems()]

        return NewItemAnswer(
            site_index=self.site.GetSelection(),
            title=self.title.GetValue().strip(),
            slug=self.slug.GetValue().strip(),
            text_format="html" if self.text_format.GetSelection() == 1 else "markdown",
            category_ids=checked(self.category_list, self._categories),
            tag_ids=checked(self.tag_list, self._tags),
        )


def ask_new_item(parent: wx.Window, show_modal: ShowModal, **kwargs: Any) -> NewItemAnswer | None:
    dialog = NewItemDialog(parent, **kwargs)
    try:
        if show_modal(dialog, dialog.GetTitle()) != wx.ID_OK:
            return None
        return dialog.answer()
    finally:
        dialog.Destroy()


# --------------------------------------------------------------------------- #
# Properties (5.5)


@dataclass
class PropertiesAnswer:
    title: str
    slug: str
    status: str
    excerpt: str
    category_ids: list[int]
    tag_ids: list[int]
    comments_open: bool
    sticky: bool
    password: str = field(repr=False, default="")


class PropertiesDialog(wx.Dialog):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("pending", "Pending review"),
        ("publish", "Published"),
        ("private", "Private"),
    )

    def __init__(
        self,
        parent: wx.Window,
        *,
        kind: str,
        title: str,
        slug: str,
        status: str,
        excerpt: str,
        categories: Sequence[tuple[int, str]],
        tags: Sequence[tuple[int, str]],
        chosen_categories: Sequence[int],
        chosen_tags: Sequence[int],
        comments_open: bool,
        sticky: bool,
        facts: str,
    ) -> None:
        super().__init__(
            parent, title="WordPress Properties", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.SetHelpText(
            "Everything about this page or post apart from its text. Changes are kept with your "
            "working "
            "copy and go to the site with your next Save Draft to Site or Publish."
        )
        self._categories = list(categories)
        self._tags = list(tags)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.facts = wx.TextCtrl(self, value=facts, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.facts.SetHelpText(
            "Which site this belongs to, its address, its author and when it last changed."
        )
        self.facts.SetMinSize(dip_size(self, 460, 80))
        _row(sizer, self, "&About:", self.facts)
        self.title = wx.TextCtrl(self, value=title)
        self.title.SetHelpText("The title the theme shows at the top.")
        _row(sizer, self, "&Title:", self.title)
        self.slug = wx.TextCtrl(self, value=slug)
        self.slug.SetHelpText("The last part of the web address.")
        _row(sizer, self, "S&lug:", self.slug)
        labels = [label for _v, label in self.STATUS_CHOICES]
        self.status = wx.Choice(self, choices=labels)
        self.status.SetHelpText(
            "Draft and Pending review are not public. Published is public. Private is visible "
            "only to "
            "editors and administrators."
        )
        values = [v for v, _l in self.STATUS_CHOICES]
        self.status.SetSelection(values.index(status) if status in values else 0)
        _row(sizer, self, "&Status:", self.status)
        self.excerpt = wx.TextCtrl(self, value=excerpt, style=wx.TE_MULTILINE)
        self.excerpt.SetHelpText(
            "A short summary some themes show in lists and search results. Optional."
        )
        _row(sizer, self, "&Excerpt:", self.excerpt)
        self.category_list: CheckGroup | None = None
        self.tag_list: CheckGroup | None = None
        if kind == "post":
            self.category_list = _check_group(
                sizer,
                self,
                "Categories",
                [n for _i, n in self._categories],
                "Check each category this post belongs to. Space checks or unchecks.",
            )
            for index, (term_id, _n) in enumerate(self._categories):
                self.category_list.Check(index, term_id in chosen_categories)
            self.tag_list = _check_group(
                sizer,
                self,
                "Tags",
                [n for _i, n in self._tags],
                "Check each tag for this post. Space checks or unchecks.",
            )
            for index, (term_id, _n) in enumerate(self._tags):
                self.tag_list.Check(index, term_id in chosen_tags)
        self.comments = wx.CheckBox(self, label="Allow co&mments")
        self.comments.SetHelpText("Whether visitors can leave comments on this page or post.")
        self.comments.SetValue(comments_open)
        sizer.Add(self.comments, 0, wx.ALL, 8)
        self.sticky = wx.CheckBox(self, label="Keep at the top of the &blog")
        self.sticky.SetHelpText(
            "A sticky post stays first on the blog page until you uncheck this."
        )
        self.sticky.SetValue(sticky)
        self.sticky.Show(kind == "post")
        sizer.Add(self.sticky, 0, wx.ALL, 8)
        self.password = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.password.SetHelpText(
            "Visitors must type this password to read it. Leave empty for no password."
        )
        _row(sizer, self, "Pass&word to read it (optional):", self.password)
        sizer.Add(_buttons(self), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)

    def answer(self) -> PropertiesAnswer:
        def checked(box: CheckGroup | None, items: list[tuple[int, str]]) -> list[int]:
            return [items[i][0] for i in box.GetCheckedItems()] if box is not None else []

        return PropertiesAnswer(
            title=self.title.GetValue().strip(),
            slug=self.slug.GetValue().strip(),
            status=self.STATUS_CHOICES[max(0, self.status.GetSelection())][0],
            excerpt=self.excerpt.GetValue().strip(),
            category_ids=checked(self.category_list, self._categories),
            tag_ids=checked(self.tag_list, self._tags),
            comments_open=self.comments.GetValue(),
            sticky=self.sticky.GetValue(),
            password=self.password.GetValue(),
        )


def ask_properties(
    parent: wx.Window, show_modal: ShowModal, **kwargs: Any
) -> PropertiesAnswer | None:
    dialog = PropertiesDialog(parent, **kwargs)
    try:
        if show_modal(dialog, "WordPress Properties") != wx.ID_OK:
            return None
        return dialog.answer()
    finally:
        dialog.Destroy()


# --------------------------------------------------------------------------- #
# The image dialog (6.7)


@dataclass
class ImageAnswer:
    alt: str
    decorative: bool
    caption: str
    width: int  # 0 = the theme decides
    featured: bool
    link: str  # "", "file" or an address


class ImageDialog(wx.Dialog):
    WIDTHS = (("The theme's content width", 0), ("Half", -50), ("Full width", -100))

    def __init__(
        self,
        parent: wx.Window,
        *,
        name: str,
        size_text: str,
        alt: str = "",
        caption: str = "",
        on_suggest: Callable[[], str | None] | None = None,
        on_describe: Callable[[], None] | None = None,
        on_suggest_async: Callable[[Callable[[str], None]], None] | None = None,
    ) -> None:
        super().__init__(
            parent, title=f"Picture: {name}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.SetHelpText(
            "Everything about one picture on this page: what it says to someone who cannot see "
            "it, its "
            "caption, how wide it shows, and whether it represents the whole page."
        )
        self._on_suggest = on_suggest
        #: Suggest that answers later (the AI): called with a setter for the field.
        self._on_suggest_async = on_suggest_async
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.alt = wx.TextCtrl(self, value=alt, style=wx.TE_MULTILINE)
        self.alt.SetHelpText(
            "Alternative text: what this picture contributes here, for someone using a screen "
            "reader. One "
            "or two sentences about its purpose. Read out any words it shows. Do not start with "
            "'image of'. "
            "This is for this place only; the same picture elsewhere keeps its own."
        )
        self.alt.SetMinSize(dip_size(self, 460, 60))
        _row(sizer, self, "&Alternative text:", self.alt)
        self.suggest = wx.Button(self, label="&Suggest Alternative Text")
        self.suggest.SetHelpText(
            "Asks your chosen AI to propose alternative text from the picture and the paragraphs "
            "around it. "
            "The proposal goes into the field for you to read and change; it is never saved by "
            "itself."
        )
        self.suggest.Bind(wx.EVT_BUTTON, self._on_suggest_click)
        self.suggest.Enable(on_suggest is not None or on_suggest_async is not None)
        sizer.Add(self.suggest, 0, wx.LEFT | wx.RIGHT, 8)
        self.decorative = wx.CheckBox(self, label="&Decorative: it adds nothing a visitor needs")
        self.decorative.SetHelpText(
            "Check this for a divider, a texture or a purely decorative picture. Screen readers "
            "then skip it, "
            "and the alternative text is left empty on purpose."
        )
        self.decorative.Bind(
            wx.EVT_CHECKBOX, lambda _e: self.alt.Enable(not self.decorative.GetValue())
        )
        sizer.Add(self.decorative, 0, wx.ALL, 8)
        self.caption = wx.TextCtrl(self, value=caption)
        self.caption.SetHelpText(
            "Visible text under the picture: names, credits or context. Optional."
        )
        _row(sizer, self, "&Caption:", self.caption)
        self.width = wx.ComboBox(
            self, choices=[label for label, _w in self.WIDTHS], style=wx.CB_DROPDOWN
        )
        self.width.SetHelpText(
            "How wide the picture shows on the page. Choose one, or type a number of pixels. "
            "Proportions "
            "are always kept and nothing is cropped. " + size_text
        )
        self.width.SetSelection(0)
        _row(sizer, self, f"Display &width ({size_text}):", self.width)
        self.featured = wx.CheckBox(self, label="Use as &featured image")
        self.featured.SetHelpText(
            "The featured image represents the whole page or post. The theme decides where it "
            "appears and "
            "may crop it."
        )
        sizer.Add(self.featured, 0, wx.ALL, 8)
        self.link = wx.ComboBox(self, choices=["Nothing", "The picture file"], style=wx.CB_DROPDOWN)
        self.link.SetHelpText(
            "Where the picture links to, if anywhere. Type an address to link elsewhere. A linked"
            " picture's "
            "alternative text should say where the link goes."
        )
        self.link.SetSelection(0)
        _row(sizer, self, "&Link to:", self.link)
        self.describe = wx.Button(self, label="Describe &Image...")
        self.describe.SetHelpText(
            "A longer description and appraisal of what is actually in the picture, for you: "
            "subject, "
            "arrangement, colours, any words, and problems like awkward cropping."
        )
        self.describe.Enable(on_describe is not None)
        if on_describe is not None:
            self.describe.Bind(wx.EVT_BUTTON, lambda _e: on_describe())
        sizer.Add(self.describe, 0, wx.ALL, 8)
        sizer.Add(_buttons(self, "Insert"), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)
        self.alt.SetFocus()

    def propose_alt(self, proposal: str) -> None:
        """Put a proposal in the field, selected, to be read and changed (6.8)."""
        if proposal and self:
            self.alt.SetValue(proposal)
            self.alt.SetFocus()
            self.alt.SelectAll()

    def _on_suggest_click(self, _event: object) -> None:
        if self._on_suggest_async is not None:
            self._on_suggest_async(self.propose_alt)
            return
        if self._on_suggest is None:
            return
        proposal = self._on_suggest()
        if proposal:
            self.alt.SetValue(proposal)
            self.alt.SetFocus()
            self.alt.SelectAll()

    def answer(self) -> ImageAnswer:
        index = self.width.GetSelection()
        typed = self.width.GetValue().strip()
        width = 0
        if index != wx.NOT_FOUND and self.width.GetString(index) == typed:
            width = self.WIDTHS[index][1]
        elif typed.isdigit():
            width = int(typed)
        link_index = self.link.GetSelection()
        link_text = self.link.GetValue().strip()
        link = (
            ""
            if link_index == 0 and link_text == "Nothing"
            else "file"
            if link_index == 1 and link_text == "The picture file"
            else link_text
        )
        return ImageAnswer(
            alt="" if self.decorative.GetValue() else self.alt.GetValue().strip(),
            decorative=self.decorative.GetValue(),
            caption=self.caption.GetValue().strip(),
            width=width,
            featured=self.featured.GetValue(),
            link=link,
        )


def ask_image(parent: wx.Window, show_modal: ShowModal, **kwargs: Any) -> ImageAnswer | None:
    dialog = ImageDialog(parent, **kwargs)
    try:
        if show_modal(dialog, dialog.GetTitle()) != wx.ID_OK:
            return None
        return dialog.answer()
    finally:
        dialog.Destroy()
