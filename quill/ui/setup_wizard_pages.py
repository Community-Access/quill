"""Page implementations for the QUILL setup wizard.

Each page is a ``wx.Panel`` subclass. ``SetupWizardDialog`` hosts all pages
inside a single ``wx.Dialog``, showing one at a time with Back/Next/Finish
navigation.

Pages (in presentation order):
  0 - Welcome
  1 - Intent (what kind of writing?)
  2 - Extras (AI / Braille / Automation)
  3 - AI Provider (shown only when AI is wanted)
  4 - Keyboard and Sound
  5 - Data Location (#615)
  6 - Summary

Feature toggles are held in ``_pending_overrides: dict[str, str]`` inside
the dialog and applied to the ``FeatureManager`` only when the user clicks
Finish, keeping the wizard transactional.

If the user cancels on first run, ``SetupWizardDialog.aborted_first_run``
is True and the caller should apply the minimal text_editor defaults.
"""

from __future__ import annotations

import html
import logging
from collections.abc import Callable

import wx

from quill.core import storage_mode
from quill.core.data_location import request_data_location_change, resolve_target
from quill.core.features import (
    FEATURE_STATE_ON,
    FeatureManager,
)
from quill.core.i18n import _, lazy_gettext
from quill.core.onboarding_profiles import (
    DEFAULT_INTENT_ID,
    IntentProfile,
    get_intent_profile,
    list_intent_profiles,
)
from quill.core.settings import Settings
from quill.ui.dialog_contract import apply_modal_ids

_log = logging.getLogger(__name__)

_PREVIEW_MIN_HEIGHT = 230

# ---------------------------------------------------------------------------
# Screen-reader detection (mirrors web_form.py / sticky_notes.py).
# ---------------------------------------------------------------------------

_SR_DETECTED: bool | None = None


def _is_sr_active() -> bool:
    """Return True if a screen reader is currently running.

    Used to choose between a richer webview preview (sighted users) and a
    read-only multi-line ``wx.TextCtrl`` preview (screen-reader users, who can
    arrow through it line by line on both Windows and macOS, like the About
    window).
    """
    global _SR_DETECTED
    if _SR_DETECTED is None:
        try:
            from quill.platform.sr_detect import detect_screen_reader

            _SR_DETECTED = detect_screen_reader().detected
        except Exception:  # noqa: BLE001
            _SR_DETECTED = False
    return bool(_SR_DETECTED)


# ---------------------------------------------------------------------------
# Wizard preview widget (replaces the read-only TextCtrl).
# ---------------------------------------------------------------------------


class _WizardPreview:
    """Adaptive preview block used by every wizard page.

    Screen-reader users get a **read-only multi-line ``wx.TextCtrl``** — the same
    surface the About window uses (``info_pages.py``). It is the only control
    that lets *both* NVDA/JAWS on Windows **and** VoiceOver on macOS arrow
    through the text line by line. (#610 had replaced it with a ``wx.StaticText``
    to avoid VoiceOver's "edit text, read only" announcement, but a StaticText is
    not keyboard-focusable, so Windows screen-reader users could not reach or
    arrow through the text at all — they only landed on the heading. The
    read-only TextCtrl is navigable everywhere; the "read only" announcement is
    accurate and matches the About window, so it is the right trade-off.)

    When no screen reader is active, a sighted user still gets the styled
    ``SidePreview`` (HTML webview). If the webview is unavailable, everyone gets
    the read-only TextCtrl, which renders the text fine visually too.
    """

    def __init__(self, parent: wx.Window, *, name: str, content_html: str) -> None:
        self._parent = parent
        self._content_html = content_html
        self._webview = None
        self._text_ctrl: wx.TextCtrl | None = None
        self.control: wx.Window
        if not _is_sr_active():
            self._webview = self._try_make_side_preview(parent)
        if self._webview is not None:
            self.control = self._webview.control
            self._webview.update(content_html)
        else:
            self._text_ctrl = self._make_readonly_text(parent, name)
            self.control = self._text_ctrl

    @staticmethod
    def _try_make_side_preview(parent: wx.Window):
        try:
            from wx_accessible_webview import SidePreview
        except Exception:  # noqa: BLE001
            return None
        try:
            preview = SidePreview(parent, title="")
        except Exception:  # noqa: BLE001
            return None
        if not getattr(preview, "using_webview", False):
            return None
        return preview

    def _make_readonly_text(self, parent: wx.Window, name: str) -> wx.TextCtrl:
        """A read-only, arrow-navigable text field (NVDA/JAWS + VoiceOver)."""
        text = self._html_to_text(self._content_html)
        ctrl = wx.TextCtrl(
            parent,
            value=text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            name=name,
        )
        ctrl.SetMinSize((-1, _PREVIEW_MIN_HEIGHT))
        return ctrl

    @staticmethod
    def _html_to_text(content_html: str) -> str:
        """Strip a small whitelist of HTML tags to plain text.

        The wizard previews only emit ``<p>``, ``<br>``, ``<b>`` and
        ``<i>`` from the small renderer used by ``update_html``. Anything
        else round-trips verbatim so screen readers do not announce raw
        markup.
        """
        import re

        out = content_html
        out = re.sub(r"(?is)<br\s*/?>", "\n", out)
        out = re.sub(r"(?is)</?p\s*/?>", "", out)
        out = re.sub(r"(?is)</?b\s*/?>", "", out)
        out = re.sub(r"(?is)</?i\s*/?>", "", out)
        return html.unescape(out).strip()

    def update_html(self, content_html: str) -> None:
        self._content_html = content_html
        if self._webview is not None:
            self._webview.update(content_html)
            return
        if self._text_ctrl is not None:
            # ChangeValue (not SetValue) so no EVT_TEXT fires and the control
            # stays read-only/clean.
            self._text_ctrl.ChangeValue(self._html_to_text(content_html))
            self._text_ctrl.GetParent().Layout()


def _render_preview_html(plain_text: str) -> str:
    """Wrap a plain-text preview string in the small HTML dialect that
    ``_WizardPreview`` consumes. Blank lines become paragraph breaks."""
    paragraphs = [html.escape(p.strip()) for p in plain_text.split("\n\n")]
    body = "\n".join(f"<p>{p}</p>" for p in paragraphs if p)
    # Replace remaining single newlines with <br> so the webview honours
    # the original line breaks.
    body = body.replace("\n", "<br>")
    return body


# ---------------------------------------------------------------------------
# Page heading
# ---------------------------------------------------------------------------


def _page_heading(parent: wx.Window, *, label: str, name: str, scale: float = 1.0) -> wx.StaticText:
    """Return a bold ``wx.StaticText`` styled as the page heading.

    A heading is not an interactive control. #610 had made it a no-border
    ``wx.Button`` so it could be the first tab stop, but that announced as a
    do-nothing "button". Now that the page's first *focusable* control is the
    read-only preview field (which the user can arrow through) or the first
    choice, ``_focus_first_page_control`` lands there directly and the heading is
    a plain, non-focusable StaticText again — visible, read on the page, never a
    spurious button.
    """
    heading = wx.StaticText(parent, label=label, name=name)
    base = (
        parent.GetFont()
        if hasattr(parent, "GetFont")
        else wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    )
    heading.SetFont(base.Scaled(scale).Bold())
    return heading


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class _WizardPage(wx.Panel):
    """Base for all wizard page panels."""

    def __init__(self, parent: wx.Window, name: str) -> None:
        super().__init__(parent)
        self.SetName(name)


# ---------------------------------------------------------------------------
# Page 0 - Welcome
# ---------------------------------------------------------------------------


class _WelcomePage(_WizardPage):
    _PREVIEW = lazy_gettext(
        "QUILL is a screen-reader-friendly text editor built from the ground up\n"
        "for people who use NVDA, JAWS, Narrator, or braille displays.\n"
        "\n"
        "This short wizard asks you one question: what kind of writing do you do?\n"
        "Your answer sets a starting point. QUILL will show only what you need\n"
        "and keep everything else out of the way.\n"
        "\n"
        "Nothing here is permanent. You can change your profile any time from\n"
        "Help > Personalise QUILL. The whole wizard takes about two minutes.\n"
        "\n"
        "Press Next to begin."
    )

    def __init__(self, parent: wx.Window, settings: Settings) -> None:
        super().__init__(parent, "Welcome")
        sizer = wx.BoxSizer(wx.VERTICAL)

        # #610: focusable heading is the first tab stop on the page; the
        # plain-text StaticText it replaced could not accept keyboard
        # focus and screen readers landed on the preview (a TextCtrl)
        # first.
        heading = _page_heading(
            self,
            label=_("Welcome to QUILL"),
            name="wizard.welcome_heading",
            scale=1.4,
        )
        sizer.Add(heading, flag=wx.ALL, border=12)

        about_label = wx.StaticText(
            self, label=_("About this wizard:"), name="wizard.welcome_about_label"
        )
        sizer.Add(about_label, flag=wx.LEFT | wx.RIGHT, border=12)

        # Preview is a styled SidePreview (webview) for sighted users, or a
        # read-only multi-line wx.TextCtrl for screen-reader users — arrow-
        # navigable on Windows (NVDA/JAWS) and macOS (VoiceOver), like the
        # About window. (Reverts the #610 StaticText, which Windows screen
        # readers could not focus or arrow through.)
        preview = _WizardPreview(
            self,
            name="wizard.welcome_preview",
            content_html=_render_preview_html(str(self._PREVIEW)),
        )
        sizer.Add(preview.control, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)
        self._preview = preview

        self.SetSizer(sizer)

    def collect(self, _settings: Settings, _overrides: dict) -> None:
        pass


# ---------------------------------------------------------------------------
# Page 1 - Intent
# ---------------------------------------------------------------------------


class _IntentPage(_WizardPage):
    def __init__(self, parent: wx.Window, feature_manager: FeatureManager) -> None:
        super().__init__(parent, "What kind of writing do you do")
        self._profiles = list_intent_profiles()

        sizer = wx.BoxSizer(wx.VERTICAL)

        heading = _page_heading(
            self,
            label=_("What kind of writing do you do?"),
            name="wizard.intent_heading",
        )
        sizer.Add(heading, flag=wx.ALL, border=12)

        desc = wx.StaticText(
            self,
            label=_(
                "Choose the option that best describes you. "
                "Arrow up and down to read about each one."
            ),
            name="wizard.intent_desc",
        )
        desc.Wrap(440)
        sizer.Add(desc, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        self._list = wx.ListBox(
            self,
            choices=[f"{p.name}  -  {p.tagline}" for p in self._profiles],
            style=wx.LB_SINGLE,
            name="wizard.intent_list",
        )
        self._list.SetMinSize((-1, 160))
        sizer.Add(self._list, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        about_label = wx.StaticText(
            self, label=_("About this choice:"), name="wizard.intent_about_label"
        )
        sizer.Add(about_label, flag=wx.LEFT | wx.RIGHT, border=12)

        # Adaptive preview: styled webview for sighted users, read-only
        # arrow-navigable wx.TextCtrl for screen-reader users (both platforms).
        self._preview = _WizardPreview(
            self,
            name="wizard.intent_preview",
            content_html="",
        )
        sizer.Add(self._preview.control, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        self._list.Bind(wx.EVT_LISTBOX, self._on_selection)

        # Pre-select based on current profile
        default_index = 0
        active_id = feature_manager.active_profile_id
        for i, profile in enumerate(self._profiles):
            if profile.technical_profile == active_id:
                default_index = i
                break
        self._list.SetSelection(default_index)
        self._update_preview(default_index)

        self.SetSizer(sizer)

    def _on_selection(self, event: wx.CommandEvent) -> None:
        self._update_preview(event.GetSelection())

    def _update_preview(self, index: int) -> None:
        if 0 <= index < len(self._profiles):
            self._preview.update_html(_render_preview_html(self._profiles[index].preview_text))

    def selected_profile(self) -> IntentProfile:
        index = self._list.GetSelection()
        if 0 <= index < len(self._profiles):
            return self._profiles[index]
        return get_intent_profile(DEFAULT_INTENT_ID)

    def collect(self, _settings: Settings, overrides: dict) -> None:
        overrides["_intent_profile"] = self.selected_profile().id


# ---------------------------------------------------------------------------
# Page 2 - Extras
# ---------------------------------------------------------------------------


class _ExtrasPage(_WizardPage):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, "A few optional extras")
        self._intent: IntentProfile = get_intent_profile(DEFAULT_INTENT_ID)

        sizer = wx.BoxSizer(wx.VERTICAL)

        heading = _page_heading(
            self,
            label=_("A few optional extras"),
            name="wizard.extras_heading",
        )
        sizer.Add(heading, flag=wx.ALL, border=12)

        self._desc = wx.StaticText(
            self,
            label=_("Add these to your starting profile. You can change them any time."),
            name="wizard.extras_desc",
        )
        self._desc.Wrap(440)
        sizer.Add(self._desc, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        self._ai_check = wx.CheckBox(
            self,
            label=_("Include AI writing assistance (Ask Quill, grammar check, prompts)"),
            name="wizard.extras_ai",
        )
        self._ai_check.Bind(wx.EVT_CHECKBOX, self._on_change)
        sizer.Add(self._ai_check, flag=wx.LEFT | wx.BOTTOM, border=12)

        self._braille_check = wx.CheckBox(
            self,
            label=_("Include Braille Mode (BRF and BRL files, braille status bar)"),
            name="wizard.extras_braille",
        )
        self._braille_check.Bind(wx.EVT_CHECKBOX, self._on_change)
        sizer.Add(self._braille_check, flag=wx.LEFT | wx.BOTTOM, border=12)

        self._auto_check = wx.CheckBox(
            self,
            label=_("Include typing automation (Smart Insert templates, abbreviations)"),
            name="wizard.extras_automation",
        )
        self._auto_check.Bind(wx.EVT_CHECKBOX, self._on_change)
        sizer.Add(self._auto_check, flag=wx.LEFT | wx.BOTTOM, border=12)

        what_label = wx.StaticText(
            self, label=_("What this adds:"), name="wizard.extras_what_label"
        )
        sizer.Add(what_label, flag=wx.LEFT | wx.RIGHT, border=12)

        # #610: adaptive preview (SidePreview / StaticText) replaces the
        # read-only TextCtrl.
        self._preview = _WizardPreview(
            self,
            name="wizard.extras_preview",
            content_html="",
        )
        sizer.Add(self._preview.control, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        self.SetSizer(sizer)
        self._update_preview()

    def refresh_for_intent(self, intent: IntentProfile) -> None:
        """Call when the user returns to the Extras page after changing intent."""
        self._intent = intent
        # Hide checkboxes already included in this profile
        self._ai_check.Show(not intent.includes_ai)
        self._braille_check.Show(not intent.includes_braille)
        self._auto_check.Show(not intent.includes_automation)
        # Reset checkboxes for new profile
        if intent.includes_ai:
            self._ai_check.SetValue(False)
        if intent.includes_braille:
            self._braille_check.SetValue(False)
        if intent.includes_automation:
            self._auto_check.SetValue(False)
        self.Layout()
        self._update_preview()

    def _on_change(self, _event: wx.CommandEvent) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        lines: list[str] = []
        wants_ai = self._ai_check.IsShown() and self._ai_check.GetValue()
        wants_braille = self._braille_check.IsShown() and self._braille_check.GetValue()
        wants_auto = self._auto_check.IsShown() and self._auto_check.GetValue()

        if not wants_ai and not wants_braille and not wants_auto:
            lines.append(_("No extras selected.\n"))
            lines.append(
                _(
                    "Press Next to continue. You can add any of these later\n"
                    "from Help > Personalise QUILL."
                )
            )
        else:
            lines.append(_("These extras will be added to your profile:\n"))
            if wants_ai:
                lines.append(
                    _(
                        "AI Writing Assistance:\n"
                        "  - Ask Quill assistant (Alt+Q)\n"
                        "  - AI grammar check and rewrite\n"
                        "  - Writing prompts and skills\n"
                        "  - Prompt Library\n"
                        "  (requires an API key from your AI provider)\n"
                    )
                )
            if wants_braille:
                lines.append(
                    _(
                        "Braille Mode:\n"
                        "  - Open and navigate BRF and BRL files\n"
                        "  - Braille status bar cell\n"
                        "  - Grade 1 and Grade 2 translation\n"
                        "  - QUILL Braille Pack integration\n"
                    )
                )
            if wants_auto:
                lines.append(
                    _(
                        "Typing Automation:\n"
                        "  - Smart Insert triggers (=bug(), =meeting(), =journal())\n"
                        "  - Abbreviation expansion (qbug, qmeet, qlog, qtodo)\n"
                        "  - BRF test content trigger (=brftest())\n"
                    )
                )
        self._preview.update_html(_render_preview_html("\n".join(lines)))

    def wants_ai(self) -> bool:
        return self._intent.includes_ai or (self._ai_check.IsShown() and self._ai_check.GetValue())

    def wants_braille(self) -> bool:
        return self._intent.includes_braille or (
            self._braille_check.IsShown() and self._braille_check.GetValue()
        )

    def wants_automation(self) -> bool:
        return self._intent.includes_automation or (
            self._auto_check.IsShown() and self._auto_check.GetValue()
        )

    def collect(self, _settings: Settings, overrides: dict) -> None:
        overrides["_extras_ai"] = "on" if self.wants_ai() else "off"
        overrides["_extras_braille"] = "on" if self.wants_braille() else "off"
        overrides["_extras_automation"] = "on" if self.wants_automation() else "off"


# ---------------------------------------------------------------------------
# Page 3 - AI Provider (shown only when AI is wanted)
# ---------------------------------------------------------------------------


class _AIProviderPage(_WizardPage):
    def __init__(self, parent: wx.Window, open_ai_hub: Callable[[], None]) -> None:
        super().__init__(parent, "Set up your AI connection")
        self._open_ai_hub = open_ai_hub
        sizer = wx.BoxSizer(wx.VERTICAL)

        heading = _page_heading(
            self,
            label=_("Set up your AI connection"),
            name="wizard.ai_heading",
        )
        sizer.Add(heading, flag=wx.ALL, border=12)

        desc = wx.StaticText(
            self,
            label=_(
                "AI providers, API keys, and models are all managed in AI Hub. "
                "Open it now to choose your provider, enter your key, and verify "
                "the connection — or do it any time from Tools > AI Hub after setup."
            ),
            name="wizard.ai_desc",
        )
        desc.Wrap(440)
        sizer.Add(desc, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        hub_btn = wx.Button(self, label=_("Open AI Hub..."), name="wizard.open_ai_hub")
        hub_btn.SetName("Open AI Hub to configure provider, API key, and model")
        sizer.Add(hub_btn, flag=wx.LEFT | wx.BOTTOM, border=12)
        hub_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_ai_hub())

        self.SetSizer(sizer)

    def collect(self, _settings: Settings, _overrides: dict) -> None:
        pass


# ---------------------------------------------------------------------------
# Page 4 - Keyboard and Sound
# ---------------------------------------------------------------------------


class _KeyboardSoundPage(_WizardPage):
    _INDENT_TONE_CHOICES: tuple[tuple[str, object], ...] = (
        ("", lazy_gettext("Off")),
        ("pentatonic", lazy_gettext("Pentatonic (no dissonance)")),
        ("whole_tone", lazy_gettext("Whole tone (even steps)")),
        ("diatonic", lazy_gettext("Diatonic C major (familiar)")),
        ("chromatic", lazy_gettext("Chromatic (one semitone per level)")),
    )

    def __init__(self, parent: wx.Window, settings: Settings) -> None:
        super().__init__(parent, "Keyboard and Sound")
        sizer = wx.BoxSizer(wx.VERTICAL)

        heading = _page_heading(
            self,
            label=_("Keyboard and Sound"),
            name="wizard.kb_heading",
        )
        sizer.Add(heading, flag=wx.ALL, border=12)

        desc = wx.StaticText(
            self,
            label=_(
                "Choose a keyboard layout and whether QUILL plays sound. "
                "Sound is always optional and never replaces speech."
            ),
            name="wizard.kb_desc",
        )
        desc.Wrap(440)
        sizer.Add(desc, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        # Z-order: StaticText before control in every row
        pack_label = wx.StaticText(self, label=_("Keyboard pack:"), name="wizard.kb_pack_label")
        self._pack = wx.Choice(self, name="wizard.kb_pack_choice")
        for label in (
            _("QUILL Default"),
            _("JAWS Compatible"),
            _("NVDA Compatible"),
            _("Narrator Compatible"),
        ):
            self._pack.Append(label)
        idx = self._pack.FindString(settings.keyboard_pack)
        self._pack.SetSelection(idx if idx != wx.NOT_FOUND else 0)
        grid.Add(pack_label, flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._pack, flag=wx.EXPAND)

        self._sound_enabled = wx.CheckBox(
            self, label=_("Play sound notifications (earcons)"), name="wizard.sound_enabled_check"
        )
        self._sound_enabled.SetValue(bool(getattr(settings, "sound_enabled", True)))
        grid.Add(wx.StaticText(self, label=""), flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._sound_enabled)

        # Sound pack: a dropdown of the packs that ship with QUILL (the file
        # picker could not select them -- bundled packs are folders, not .qsp
        # files). The default pack is QUILL's own; an existing custom pack, if
        # any, is preserved as a final entry so it is not silently lost.
        from quill.core.sound_pack import available_sound_packs

        self._sound_pack_path = str(getattr(settings, "sound_pack_path", "") or "")
        self._pack_row_label = wx.StaticText(
            self, label=_("Sound pack:"), name="wizard.sound_pack_label"
        )
        packs = available_sound_packs()
        pack_labels = [p.name for p in packs]
        self._sound_pack_values = [p.setting_value for p in packs]
        selection = next(
            (i for i, v in enumerate(self._sound_pack_values) if v == self._sound_pack_path),
            -1,
        )
        if selection < 0 and self._sound_pack_path.strip():
            from pathlib import Path as _Path

            pack_labels.append(
                _("Custom: %s") % (_Path(self._sound_pack_path).name or self._sound_pack_path)
            )
            self._sound_pack_values.append(self._sound_pack_path)
            selection = len(self._sound_pack_values) - 1
        self._sound_pack_choice = wx.Choice(
            self, name="wizard.sound_pack_choice", choices=pack_labels
        )
        if pack_labels:
            self._sound_pack_choice.SetSelection(max(0, selection))
        grid.Add(self._pack_row_label, flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._sound_pack_choice, flag=wx.EXPAND)

        self._indent_label = wx.StaticText(
            self, label=_("Indentation tones:"), name="wizard.indent_tone_label"
        )
        self._indent = wx.Choice(
            self,
            name="wizard.indent_tone_choice",
            choices=[str(label) for _value, label in self._INDENT_TONE_CHOICES],
        )
        current_scale = str(getattr(settings, "indent_tone_scale", "") or "")
        indent_idx = next(
            (i for i, (v, _l) in enumerate(self._INDENT_TONE_CHOICES) if v == current_scale), 0
        )
        self._indent.SetSelection(indent_idx)
        grid.Add(self._indent_label, flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._indent, flag=wx.EXPAND)

        self._sound_enabled.Bind(wx.EVT_CHECKBOX, self._on_sound_toggle)

        sizer.Add(grid, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)
        self.SetSizer(sizer)
        self._apply_sound_enabled_state()

    def _apply_sound_enabled_state(self) -> None:
        on = self._sound_enabled.GetValue()
        for ctrl in (
            self._pack_row_label,
            self._sound_pack_choice,
            self._indent_label,
            self._indent,
        ):
            ctrl.Enable(on)

    def _on_sound_toggle(self, _event: wx.CommandEvent) -> None:
        self._apply_sound_enabled_state()

    def collect(self, settings: Settings, _overrides: dict) -> None:
        settings.keyboard_pack = self._pack.GetStringSelection() or "QUILL Default"
        settings.sound_enabled = self._sound_enabled.GetValue()
        pack_index = self._sound_pack_choice.GetSelection()
        if 0 <= pack_index < len(self._sound_pack_values):
            settings.sound_pack_path = self._sound_pack_values[pack_index]
        selection = self._indent.GetSelection()
        if 0 <= selection < len(self._INDENT_TONE_CHOICES):
            settings.indent_tone_scale = self._INDENT_TONE_CHOICES[selection][0]


# ---------------------------------------------------------------------------
# Page 5 - Data Location (#615)
# ---------------------------------------------------------------------------


class _DataLocationPage(_WizardPage):
    """Where QUILL stores settings, autosaves, and other local data.

    A change here is applied through ``request_data_location_change``
    (restart-deferred, see ``core.data_location``) rather than written
    directly, so re-running this wizard on an existing install (Help >
    Personalise QUILL) never moves real data out from under a running
    session -- only a true first run, where the target already equals the
    untouched default, applies immediately.
    """

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, "Where QUILL stores your data")
        self._portable_root = storage_mode.portable_root_dir()
        self._custom_path = ""
        self._pending_summary = ""

        sizer = wx.BoxSizer(wx.VERTICAL)

        heading = _page_heading(
            self,
            label=_("Where should QUILL store your data?"),
            name="wizard.data_location_heading",
        )
        sizer.Add(heading, flag=wx.ALL, border=12)

        desc = wx.StaticText(
            self,
            label=_(
                "Settings, dictionaries, autosaves, and recovery files go here. "
                "You can change this later from Help > Personalise QUILL or Preferences."
            ),
            name="wizard.data_location_desc",
        )
        desc.Wrap(440)
        sizer.Add(desc, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        self._appdata_radio = wx.RadioButton(
            self,
            label=_("In my Windows user profile (recommended)"),
            name="wizard.data_location_appdata",
            style=wx.RB_GROUP,
        )
        self._appdata_radio.SetValue(True)
        sizer.Add(self._appdata_radio, flag=wx.LEFT | wx.BOTTOM, border=12)

        self._portable_radio = wx.RadioButton(
            self,
            label=_("Next to QUILL, on this portable drive"),
            name="wizard.data_location_portable",
        )
        self._portable_radio.Show(self._portable_root is not None)
        sizer.Add(self._portable_radio, flag=wx.LEFT | wx.BOTTOM, border=12)

        self._custom_radio = wx.RadioButton(
            self,
            label=_("Choose a folder:"),
            name="wizard.data_location_custom",
        )
        sizer.Add(self._custom_radio, flag=wx.LEFT | wx.BOTTOM, border=4)

        # #610: a StaticText display (not a TextCtrl) so VoiceOver does not
        # announce this as an editable field -- the path is only ever set
        # via the Choose dialog, mirroring _KeyboardSoundPage's sound-pack
        # picker above.
        custom_row = wx.BoxSizer(wx.HORIZONTAL)
        self._custom_display = wx.StaticText(
            self, label=_("No folder chosen"), name="wizard.data_location_custom_path"
        )
        self._choose_btn = wx.Button(self, label=_("Choose..."), name="wizard.data_location_choose")
        self._choose_btn.Bind(wx.EVT_BUTTON, self._on_choose_folder)
        custom_row.Add(self._custom_display, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        custom_row.Add(self._choose_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(custom_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        self.SetSizer(sizer)

    def _on_choose_folder(self, _event: object) -> None:
        with wx.DirDialog(
            self,
            _("Choose a folder for QUILL's data"),
            defaultPath=self._custom_path,
            style=wx.DD_DEFAULT_STYLE,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            self._custom_path = dlg.GetPath()
        self._custom_display.SetLabel(self._custom_path)
        self.Layout()
        self._custom_radio.SetValue(True)

    def collect(self, _settings: Settings, overrides: dict) -> None:
        from pathlib import Path

        if self._custom_radio.GetValue() and self._custom_path:
            mode = "custom"
            custom_path = Path(self._custom_path)
        elif self._portable_radio.GetValue() and self._portable_root is not None:
            mode = "portable"
            custom_path = None
        else:
            mode = "appdata"
            custom_path = None

        try:
            target = resolve_target(mode, custom_path)
            request_data_location_change(mode, custom_path)
        except (ValueError, OSError) as error:
            _log.warning("Could not record data-location choice %s: %s", mode, error)
            overrides["_data_location_summary"] = ""
            return

        overrides["_data_location_summary"] = _("Data location: {target}").format(target=target)


# ---------------------------------------------------------------------------
# Page 6 - Summary
# ---------------------------------------------------------------------------


class _SummaryPage(_WizardPage):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, "Summary")
        sizer = wx.BoxSizer(wx.VERTICAL)

        heading = _page_heading(
            self,
            label=_("You are all set!"),
            name="wizard.summary_heading",
        )
        sizer.Add(heading, flag=wx.ALL, border=12)

        ready_label = wx.StaticText(
            self, label=_("Your QUILL is ready:"), name="wizard.summary_ready_label"
        )
        sizer.Add(ready_label, flag=wx.LEFT | wx.RIGHT, border=12)

        # #610: adaptive preview (SidePreview / StaticText) replaces the
        # read-only TextCtrl.
        self._summary = _WizardPreview(
            self,
            name="wizard.summary_text",
            content_html="",
        )
        sizer.Add(self._summary.control, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        note = wx.StaticText(
            self,
            label=_(
                "Press Finish to start writing. "
                "Change anything later from Help > Personalise QUILL."
            ),
            name="wizard.summary_note",
        )
        note.Wrap(440)
        sizer.Add(note, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        self.SetSizer(sizer)

    def update_summary(self, settings: Settings, overrides: dict) -> None:
        intent_id = overrides.get("_intent_profile", DEFAULT_INTENT_ID)
        intent = get_intent_profile(intent_id)
        wants_ai = overrides.get("_extras_ai") == "on"
        wants_braille = overrides.get("_extras_braille") == "on"
        wants_auto = overrides.get("_extras_automation") == "on"

        lines: list[str] = []
        lines.append(_("Profile: {name}").format(name=intent.name))
        lines.append("")

        # Base preview (first paragraph only, up to first blank line)
        base_lines = intent.preview_text.split("\n")
        # Skip title line and blank line after it, then take "What you have:" section
        in_what = False
        for line in base_lines:
            if line.strip().startswith("What you have:"):
                in_what = True
                lines.append(line)
                continue
            if in_what:
                recent = lines[-3:] if len(lines) >= 3 else lines
                if line.strip() == "" and any(item.startswith("  -") for item in recent):
                    break
                lines.append(line)

        # Extras
        extras: list[str] = []
        if wants_ai and not intent.includes_ai:
            extras.append("  - AI writing assistance (Ask Quill, prompts, grammar check)")
        if wants_braille and not intent.includes_braille:
            extras.append("  - Braille Mode (BRF/BRL files, status bar)")
        if wants_auto and not intent.includes_automation:
            extras.append("  - Typing automation (Smart Insert, abbreviations)")
        if extras:
            lines.append("")
            lines.append(_("Extras added:"))
            lines.extend(extras)

        lines.append("")
        lines.append(_("Keyboard pack: {pack}").format(pack=settings.keyboard_pack))
        sound_on = bool(getattr(settings, "sound_enabled", True))
        lines.append(
            _("Sound notifications: {state}").format(state=_("On") if sound_on else _("Off"))
        )

        data_location_summary = overrides.get("_data_location_summary")
        if data_location_summary:
            lines.append(str(data_location_summary))

        self._summary.update_html(_render_preview_html("\n".join(lines)))

    def collect(self, _settings: Settings, _overrides: dict) -> None:
        pass


# ---------------------------------------------------------------------------
# Host dialog
# ---------------------------------------------------------------------------


class SetupWizardDialog(wx.Dialog):
    """Multi-page wizard dialog that personalises QUILL.

    Applies choices atomically when the user clicks Finish.  On first-run
    cancel, ``aborted_first_run`` is set to ``True`` so the caller can apply
    the minimal text_editor defaults.
    """

    def __init__(
        self,
        parent: wx.Window,
        settings: Settings,
        feature_manager: FeatureManager,
        *,
        announce_cb: Callable[[str], None] | None = None,
        open_ai_hub: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title=_("Personalise QUILL"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="setup_wizard",
        )
        self._settings = settings
        self._feature_manager = feature_manager
        self._open_ai_hub = open_ai_hub or (lambda: None)
        self._pending_overrides: dict[str, str] = {}
        self._current_idx = 0
        self._announce = announce_cb or (lambda _: None)
        self.aborted_first_run = False

        self._all_pages = self._build_all_pages()
        self._active: list[_WizardPage] = []
        self._rebuild_active()

        self._build_ui()
        self._show_page(0)
        self.SetMinSize((540, 560))
        self.Fit()
        self.CentreOnParent()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.Bind(wx.EVT_INIT_DIALOG, lambda _e: wx.CallAfter(self._focus_first_page_control))

    # -- page list -----------------------------------------------------------

    def _build_all_pages(self) -> list[_WizardPage]:
        welcome = _WelcomePage(self, self._settings)
        intent = _IntentPage(self, self._feature_manager)
        extras = _ExtrasPage(self)
        ai_provider = _AIProviderPage(self, self._open_ai_hub)
        kb_sound = _KeyboardSoundPage(self, self._settings)
        data_location = _DataLocationPage(self)
        summary = _SummaryPage(self)
        # All pages constructed; hide them all until shown by _show_page.
        return [welcome, intent, extras, ai_provider, kb_sound, data_location, summary]

    def _rebuild_active(self) -> None:
        """Rebuild the visible page sequence based on current overrides."""
        want_ai = self._pending_overrides.get("_extras_ai") == "on"
        pages: list[_WizardPage] = [
            self._all_pages[0],  # Welcome
            self._all_pages[1],  # Intent
            self._all_pages[2],  # Extras
        ]
        if want_ai:
            pages.append(self._all_pages[3])  # AI Provider
        pages.append(self._all_pages[4])  # Keyboard & Sound
        pages.append(self._all_pages[5])  # Data Location
        pages.append(self._all_pages[6])  # Summary
        self._active = pages

    # -- UI ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = wx.BoxSizer(wx.VERTICAL)

        self._page_container = wx.BoxSizer(wx.VERTICAL)
        for page in self._all_pages:
            self._page_container.Add(page, proportion=1, flag=wx.EXPAND)
            page.Hide()
            page.Disable()

        outer.Add(self._page_container, proportion=1, flag=wx.EXPAND | wx.ALL, border=4)
        outer.Add(wx.StaticLine(self), flag=wx.EXPAND)

        nav = wx.BoxSizer(wx.HORIZONTAL)
        self._progress = wx.StaticText(self, name="wizard.progress_label")
        nav.Add(self._progress, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=8)
        nav.AddStretchSpacer()

        # #611: Drop the chevron decorations from the accessible name.
        # VoiceOver was reading them as "less than Back" and "Next
        # greater than" — pure noise. The labels now read "Back" and
        # "Next" so screen readers (and JAWS in Forms mode) hear clean
        # button names. Visual decoration is unchanged; this fix is
        # only about what screen readers announce.
        self._back_btn = wx.Button(self, label=_("Back"), name="wizard.back")
        self._next_btn = wx.Button(self, label=_("Next"), name="wizard.next")
        self._finish_btn = wx.Button(self, wx.ID_OK, label=_("Finish"), name="wizard.finish")
        self._cancel_btn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"), name="wizard.cancel")

        nav.Add(self._back_btn, flag=wx.LEFT, border=4)
        nav.Add(self._next_btn, flag=wx.LEFT, border=4)
        nav.Add(self._finish_btn, flag=wx.LEFT, border=4)
        nav.Add(self._cancel_btn, flag=wx.LEFT | wx.RIGHT, border=8)

        outer.Add(nav, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=8)

        self._back_btn.Bind(wx.EVT_BUTTON, self._on_back)
        self._next_btn.Bind(wx.EVT_BUTTON, self._on_next)
        self._finish_btn.Bind(wx.EVT_BUTTON, self._on_finish)
        self.Bind(wx.EVT_BUTTON, self._on_dismiss, id=wx.ID_CANCEL)

        self.SetSizer(outer)

    def _show_page(self, idx: int) -> None:
        if 0 <= self._current_idx < len(self._active):
            old = self._active[self._current_idx]
            old.Hide()
            old.Disable()

        self._current_idx = idx
        page = self._active[idx]
        page.Enable()
        page.Show()
        self.Layout()

        total = len(self._active)
        self._progress.SetLabel(_("Step {step} of {total}").format(step=idx + 1, total=total))
        self._back_btn.Enable(idx > 0)
        self._next_btn.Show(idx < total - 1)
        self._finish_btn.Show(idx == total - 1)

        # Use the page's own name rather than a separately indexed title
        # list: the active page sequence varies (the AI Provider page only
        # appears when wanted), so a position-indexed list drifts out of
        # sync with what is actually shown. Every page already sets a
        # human-readable name via _WizardPage.__init__.
        title = page.GetName() or f"Step {idx + 1}"
        self._announce(f"Step {idx + 1} of {total}: {title}")

        if idx == total - 1:
            summary = self._active[-1]
            if isinstance(summary, _SummaryPage):
                summary.update_summary(self._settings, self._pending_overrides)
            self._finish_btn.SetFocus()
        else:
            self._focus_first_page_control()

    def _focus_first_page_control(self) -> None:
        """Focus the first interactive child of the current page.

        The page heading is a non-focusable ``wx.StaticText`` (see
        ``_page_heading``), so focus lands on the first real focusable control —
        the read-only preview field the user can arrow through, or the first
        choice — rather than a spurious "heading" button. Falls back to the nav
        button when the page has no focusable children.

        Always sets the correct default button first so Enter activates the
        right nav button even when focus is inside a TextCtrl or ListBox.
        """
        total = len(self._active)
        on_last = self._current_idx == total - 1
        if on_last:
            self.SetDefaultItem(self._finish_btn)
        else:
            self.SetDefaultItem(self._next_btn)

        page = self._active[self._current_idx]
        for child in page.GetChildren():
            if child.IsShown() and child.IsEnabled() and child.AcceptsFocusFromKeyboard():
                child.SetFocus()
                return
        self._focus_nav_button()

    def _focus_nav_button(self) -> None:
        total = len(self._active)
        if self._current_idx == total - 1:
            self.SetDefaultItem(self._finish_btn)
            self._finish_btn.SetFocus()
        else:
            self.SetDefaultItem(self._next_btn)
            self._next_btn.SetFocus()

    # -- navigation ----------------------------------------------------------

    def _collect_current(self) -> None:
        page = self._active[self._current_idx]
        page.collect(self._settings, self._pending_overrides)

    def _on_back(self, _: wx.CommandEvent) -> None:
        self._collect_current()
        if self._current_idx > 0:
            self._show_page(self._current_idx - 1)

    def _on_next(self, _: wx.CommandEvent) -> None:
        self._collect_current()
        # After Intent page: refresh Extras for the chosen profile
        current_page = self._active[self._current_idx]
        if isinstance(current_page, _IntentPage):
            intent = current_page.selected_profile()
            extras_page = self._all_pages[2]
            if isinstance(extras_page, _ExtrasPage):
                extras_page.refresh_for_intent(intent)
        # After Extras page: rebuild active list (AI provider page may appear)
        if isinstance(current_page, _ExtrasPage):
            current_idx_in_active = self._current_idx
            self._rebuild_active()
            # Clamp index in case active list shrank
            self._current_idx = min(current_idx_in_active, len(self._active) - 1)
        if self._current_idx < len(self._active) - 1:
            self._show_page(self._current_idx + 1)

    def _on_finish(self, _: wx.CommandEvent) -> None:
        self._collect_current()
        self._apply_pending()
        self.EndModal(wx.ID_OK)

    def _on_dismiss(self, _: wx.CommandEvent) -> None:
        self.aborted_first_run = True
        self.EndModal(wx.ID_CANCEL)

    # -- apply ---------------------------------------------------------------

    def _apply_pending(self) -> None:
        from quill.core.feature_catalog import FEATURE_DEFINITIONS

        intent_id = self._pending_overrides.pop("_intent_profile", DEFAULT_INTENT_ID)
        intent = get_intent_profile(intent_id)

        self._feature_manager.switch_profile(intent.technical_profile)

        for feature_id, state in intent.feature_overrides.items():
            if feature_id not in FEATURE_DEFINITIONS:
                continue
            enabled = state == FEATURE_STATE_ON
            try:
                self._feature_manager.set_feature_enabled(feature_id, enabled)
            except Exception:
                _log.debug("Could not set %s to %s", feature_id, state)

        # Apply extras overrides
        ai_on = self._pending_overrides.pop("_extras_ai", "off") == "on"
        braille_on = self._pending_overrides.pop("_extras_braille", "off") == "on"
        automation_on = self._pending_overrides.pop("_extras_automation", "off") == "on"

        if ai_on and "future.ai" in FEATURE_DEFINITIONS:
            try:
                self._feature_manager.set_feature_enabled("future.ai", True)
            except Exception:
                pass
        if braille_on and "core.braille" in FEATURE_DEFINITIONS:
            try:
                self._feature_manager.set_feature_enabled("core.braille", True)
            except Exception:
                pass

        # Store intent and extras on settings so main_frame can apply Quillins
        self._settings.setup_wizard_intent = intent_id
        self._settings.setup_wizard_wants_ai = ai_on
        self._settings.setup_wizard_wants_braille = braille_on
        self._settings.setup_wizard_wants_automation = automation_on

        # Apply remaining feature overrides (automation affects macros flag)
        if automation_on and "core.macros" in FEATURE_DEFINITIONS:
            try:
                self._feature_manager.set_feature_enabled("core.macros", True)
            except Exception:
                pass
