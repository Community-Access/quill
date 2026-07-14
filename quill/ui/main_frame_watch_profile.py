"""Watch Folder profile editor dialog (extracted from main_frame.py; GATE-11/CQ-1).

The Add/Edit Watch Profile dialog was a self-contained ``self`` method in
main_frame.py with no shared local state, so it moves cleanly to a mixin. This
keeps main_frame.py under its size budget and starts grouping the watch UI for
the ongoing decomposition.
"""

from __future__ import annotations

from quill.core.watch_actions import WatchItem
from quill.core.watch_profiles import (
    POST_DELETE,
    POST_LEAVE,
    POST_MOVE,
    SCHED_ALWAYS,
    SCHED_QUIET,
    SCHED_WINDOW,
    WatchProfile,
)
from quill.ui.dialog_contract import apply_modal_ids


class WatchProfileDialogMixin:
    """Provides MainFrame's Add/Edit Watch Profile dialog."""

    def _edit_watch_profile(self, profile: WatchProfile | None) -> WatchProfile | None:  # noqa: PLR0915
        wx = self._wx
        base = profile if profile is not None else WatchProfile()
        title = "Edit Watch Profile" if profile is not None else "Add Watch Profile"
        with wx.Dialog(self.frame, title=title) as dialog:
            root = wx.BoxSizer(wx.VERTICAL)

            name_row = wx.BoxSizer(wx.HORIZONTAL)
            name_label = wx.StaticText(dialog, label="Profile name")
            name_input = wx.TextCtrl(dialog, value=base.name)
            name_input.SetName("Profile name")
            name_row.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            name_row.Add(name_input, 1, wx.EXPAND)
            root.Add(name_row, 0, wx.EXPAND | wx.ALL, 8)

            enabled = wx.CheckBox(dialog, label="Profile enabled")
            enabled.SetValue(base.enabled)
            enabled.SetName("Profile enabled")
            root.Add(enabled, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            path_row = wx.BoxSizer(wx.HORIZONTAL)
            path_label = wx.StaticText(dialog, label="Watch folder")
            path_input = wx.TextCtrl(dialog, value=base.folder_path)
            path_input.SetName("Watch folder path")
            path_browse = wx.Button(dialog, label="Bro&wse...")
            path_row.Add(path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            path_row.Add(path_input, 1, wx.EXPAND | wx.RIGHT, 8)
            path_row.Add(path_browse, 0)
            root.Add(path_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            include_subfolders = wx.CheckBox(dialog, label="Include subfolders")
            include_subfolders.SetValue(base.include_subfolders)
            include_subfolders.SetName("Include subfolders")
            root.Add(include_subfolders, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            process_existing = wx.CheckBox(dialog, label="Process existing files on start")
            process_existing.SetValue(base.process_existing)
            process_existing.SetName("Process existing files on start")
            root.Add(process_existing, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # --- Filters (WATCH-5) ---
            suffix_row = wx.BoxSizer(wx.HORIZONTAL)
            suffix_label = wx.StaticText(dialog, label="File types (comma separated)")
            suffix_input = wx.TextCtrl(dialog, value=", ".join(base.suffixes))
            suffix_input.SetName("File type suffixes, comma separated")
            suffix_row.Add(suffix_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            suffix_row.Add(suffix_input, 1, wx.EXPAND)
            root.Add(suffix_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            pattern_row = wx.BoxSizer(wx.HORIZONTAL)
            pattern_label = wx.StaticText(dialog, label="Name patterns (comma separated)")
            pattern_input = wx.TextCtrl(dialog, value=", ".join(base.name_patterns))
            pattern_input.SetName("File name patterns, comma separated")
            pattern_row.Add(pattern_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            pattern_row.Add(pattern_input, 1, wx.EXPAND)
            root.Add(pattern_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            size_row = wx.BoxSizer(wx.HORIZONTAL)
            size_label = wx.StaticText(dialog, label="Minimum size (bytes)")
            size_input = wx.SpinCtrl(dialog, min=0, max=1_000_000_000, initial=base.min_size_bytes)
            size_input.SetName("Minimum file size in bytes")
            size_row.Add(size_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            size_row.Add(size_input, 0)
            root.Add(size_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            age_row = wx.BoxSizer(wx.HORIZONTAL)
            age_label = wx.StaticText(dialog, label="Minimum age (seconds)")
            age_input = wx.SpinCtrlDouble(
                dialog, min=0.0, max=3600.0, inc=0.5, initial=base.min_age_seconds
            )
            age_input.SetName("Minimum file age in seconds")
            age_row.Add(age_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            age_row.Add(age_input, 0)
            root.Add(age_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            interval_row = wx.BoxSizer(wx.HORIZONTAL)
            interval_label = wx.StaticText(dialog, label="Poll interval (seconds)")
            interval_input = wx.SpinCtrl(dialog, min=2, max=300, initial=base.poll_interval_seconds)
            interval_input.SetName("Poll interval in seconds")
            interval_row.Add(interval_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            interval_row.Add(interval_input, 0)
            root.Add(interval_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # --- Schedule (WATCH-5) ---
            sched_modes = [SCHED_ALWAYS, SCHED_WINDOW, SCHED_QUIET]
            sched_labels = [
                "Always active",
                "Active only during a daily window",
                "Active except during quiet hours",
            ]
            sched_row = wx.BoxSizer(wx.HORIZONTAL)
            sched_label = wx.StaticText(dialog, label="Schedule")
            sched_choice = wx.Choice(dialog, choices=sched_labels)
            sched_choice.SetName("Schedule mode")
            sched_choice.SetSelection(
                sched_modes.index(base.schedule_mode) if base.schedule_mode in sched_modes else 0
            )
            sched_row.Add(sched_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            sched_row.Add(sched_choice, 1, wx.EXPAND)
            root.Add(sched_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            start_h, start_m = divmod(base.schedule_start_minute, 60)
            end_h, end_m = divmod(base.schedule_end_minute, 60)
            time_row = wx.BoxSizer(wx.HORIZONTAL)
            time_row.Add(
                wx.StaticText(dialog, label="From"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
            )
            start_hour = wx.SpinCtrl(dialog, min=0, max=23, initial=start_h)
            start_hour.SetName("Schedule start hour")
            start_minute = wx.SpinCtrl(dialog, min=0, max=59, initial=start_m)
            start_minute.SetName("Schedule start minute")
            time_row.Add(start_hour, 0, wx.RIGHT, 2)
            time_row.Add(start_minute, 0, wx.RIGHT, 12)
            time_row.Add(
                wx.StaticText(dialog, label="to"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
            )
            end_hour = wx.SpinCtrl(dialog, min=0, max=23, initial=end_h)
            end_hour.SetName("Schedule end hour")
            end_minute = wx.SpinCtrl(dialog, min=0, max=59, initial=end_m)
            end_minute.SetName("Schedule end minute")
            time_row.Add(end_hour, 0, wx.RIGHT, 2)
            time_row.Add(end_minute, 0)
            root.Add(time_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            available = list(self._watch_service.registry.available_actions())
            action_ids = [action.action_id for action in available]
            action_labels = [action.label for action in available]
            action_row = wx.BoxSizer(wx.HORIZONTAL)
            action_label = wx.StaticText(dialog, label="Action")
            action_choice = wx.Choice(dialog, choices=action_labels)
            action_choice.SetName("Watch action")
            if base.action_id in action_ids:
                action_choice.SetSelection(action_ids.index(base.action_id))
            elif action_labels:
                action_choice.SetSelection(0)
            action_row.Add(action_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            action_row.Add(action_choice, 1, wx.EXPAND)
            root.Add(action_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            action_dest_row = wx.BoxSizer(wx.HORIZONTAL)
            action_dest_label = wx.StaticText(dialog, label="Action destination")
            action_dest_input = wx.TextCtrl(
                dialog, value=str(base.action_options.get("destination", ""))
            )
            action_dest_input.SetName("Action destination folder")
            action_dest_browse = wx.Button(dialog, label="Brow&se...")
            action_dest_row.Add(action_dest_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            action_dest_row.Add(action_dest_input, 1, wx.EXPAND | wx.RIGHT, 8)
            action_dest_row.Add(action_dest_browse, 0)
            root.Add(action_dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # --- Per-action options (WATCH-7) ---
            convert_formats = ["markdown", "html", "plain"]
            convert_labels = ["Markdown", "HTML", "Plain text"]
            convert_row = wx.BoxSizer(wx.HORIZONTAL)
            convert_row.Add(
                wx.StaticText(dialog, label="Convert to"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                8,
            )
            convert_choice = wx.Choice(dialog, choices=convert_labels)
            convert_choice.SetName("Convert target format")
            current_fmt = str(base.action_options.get("target_format", "")).strip().lower()
            convert_choice.SetSelection(
                convert_formats.index(current_fmt) if current_fmt in convert_formats else 0
            )
            convert_row.Add(convert_choice, 1, wx.EXPAND)
            root.Add(convert_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # Transcript output format for the offline "Transcribe audio (offline)"
            # action (WATCH-9). SRT/VTT carry timestamps; they fall back to text
            # when the engine returns no timestamped segments.
            transcribe_formats = ["txt", "srt", "vtt", "md"]
            transcribe_labels = [
                "Text (.txt)",
                "SubRip captions (.srt)",
                "WebVTT captions (.vtt)",
                "Markdown (.md)",
            ]
            transcribe_row = wx.BoxSizer(wx.HORIZONTAL)
            transcribe_row.Add(
                wx.StaticText(dialog, label="Transcript format"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                8,
            )
            transcribe_choice = wx.Choice(dialog, choices=transcribe_labels)
            transcribe_choice.SetName("Transcript output format")
            current_tfmt = str(base.action_options.get("output_format", "")).strip().lower()
            transcribe_choice.SetSelection(
                transcribe_formats.index(current_tfmt) if current_tfmt in transcribe_formats else 0
            )
            transcribe_row.Add(transcribe_choice, 1, wx.EXPAND)
            root.Add(transcribe_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # The Listening Companion: optionally run an AI Action on the new
            # transcript and save the result document next to it. Applies to both
            # transcribe actions; "None" keeps just the transcript.
            from quill.core.ai.transcript_actions import BUILTIN_TRANSCRIPT_ACTIONS

            ta_ids = ["", *[a.id for a in BUILTIN_TRANSCRIPT_ACTIONS]]
            ta_labels = [
                "None (just the transcript)",
                *[a.name for a in BUILTIN_TRANSCRIPT_ACTIONS],
            ]
            ta_row = wx.BoxSizer(wx.HORIZONTAL)
            ta_row.Add(
                wx.StaticText(dialog, label="Then make"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                8,
            )
            transcript_action_choice = wx.Choice(dialog, choices=ta_labels)
            transcript_action_choice.SetName("AI action to run on the transcript")
            current_ta = str(base.action_options.get("transcript_action", "")).strip().lower()
            transcript_action_choice.SetSelection(
                ta_ids.index(current_ta) if current_ta in ta_ids else 0
            )
            ta_row.Add(transcript_action_choice, 1, wx.EXPAND)
            root.Add(ta_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            macro_names = sorted(getattr(getattr(self, "macros", None), "macros", {}) or {})
            macro_row = wx.BoxSizer(wx.HORIZONTAL)
            macro_row.Add(
                wx.StaticText(dialog, label="Macro to run"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                8,
            )
            macro_input = wx.ComboBox(
                dialog,
                value=str(base.action_options.get("macro_name", "")),
                choices=macro_names,
            )
            macro_input.SetName("Macro name to run")
            macro_row.Add(macro_input, 1, wx.EXPAND)
            root.Add(macro_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            root.Add(
                wx.StaticText(dialog, label="Python transform (sandboxed)"),
                0,
                wx.LEFT | wx.RIGHT,
                8,
            )
            python_code = wx.TextCtrl(
                dialog,
                value=str(base.action_options.get("code", "")),
                style=wx.TE_MULTILINE,
                size=(-1, 80),
            )
            python_code.SetName("Python transform code")
            root.Add(python_code, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            py_opts_row = wx.BoxSizer(wx.HORIZONTAL)
            py_opts_row.Add(
                wx.StaticText(dialog, label="Output suffix"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                4,
            )
            python_suffix = wx.TextCtrl(
                dialog, value=str(base.action_options.get("output_suffix", ""))
            )
            python_suffix.SetName("Python transform output suffix")
            py_opts_row.Add(python_suffix, 1, wx.EXPAND | wx.RIGHT, 12)
            py_opts_row.Add(
                wx.StaticText(dialog, label="Timeout (s)"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                4,
            )
            python_timeout = wx.SpinCtrlDouble(
                dialog,
                min=0.1,
                max=60.0,
                inc=0.5,
                initial=float(base.action_options.get("timeout_seconds", 5.0) or 5.0),
            )
            python_timeout.SetName("Python transform timeout in seconds")
            py_opts_row.Add(python_timeout, 0)
            root.Add(py_opts_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            ai_modes = ["summarize", "tag", "rewrite"]
            ai_labels = ["Summarize", "Tag", "Rewrite"]
            ai_row = wx.BoxSizer(wx.HORIZONTAL)
            ai_row.Add(
                wx.StaticText(dialog, label="AI action"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                8,
            )
            ai_choice = wx.Choice(dialog, choices=ai_labels)
            ai_choice.SetName("AI action mode")
            current_ai = str(base.action_options.get("mode", "")).strip().lower()
            ai_choice.SetSelection(ai_modes.index(current_ai) if current_ai in ai_modes else 0)
            ai_row.Add(ai_choice, 1, wx.EXPAND)
            root.Add(ai_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            consent_detail = self._watch_ai_consent_detail()
            consent = wx.CheckBox(
                dialog,
                label="I consent to send this folder's files to the AI model",
            )
            consent.SetValue(bool(base.action_options.get("consent", False)))
            consent.SetName("AI consent for this profile")
            root.Add(consent, 0, wx.LEFT | wx.RIGHT, 8)
            consent_text = wx.StaticText(dialog, label=consent_detail)
            consent_text.SetName("AI consent details")
            root.Add(consent_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            post_choices = ["Leave file in place", "Move to folder", "Delete file"]
            post_values = [POST_LEAVE, POST_MOVE, POST_DELETE]
            post_row = wx.BoxSizer(wx.HORIZONTAL)
            post_label = wx.StaticText(dialog, label="After processing")
            post_choice = wx.Choice(dialog, choices=post_choices)
            post_choice.SetName("After processing")
            post_choice.SetSelection(
                post_values.index(base.post_action) if base.post_action in post_values else 0
            )
            post_row.Add(post_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            post_row.Add(post_choice, 1, wx.EXPAND)
            root.Add(post_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            post_dest_row = wx.BoxSizer(wx.HORIZONTAL)
            post_dest_label = wx.StaticText(dialog, label="Move destination")
            post_dest_input = wx.TextCtrl(dialog, value=base.post_action_destination)
            post_dest_input.SetName("Post-action move destination")
            post_dest_browse = wx.Button(dialog, label="Brows&e...")
            post_dest_row.Add(post_dest_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            post_dest_row.Add(post_dest_input, 1, wx.EXPAND | wx.RIGHT, 8)
            post_dest_row.Add(post_dest_browse, 0)
            root.Add(post_dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            preview_button = wx.Button(dialog, label="Pre&view (dry run)")
            preview_button.SetName("Preview the action without changing files")
            root.Add(preview_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            def _pick_folder(target: object) -> None:
                with wx.DirDialog(
                    dialog,
                    "Choose folder",
                    defaultPath=target.GetValue().strip(),
                    style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
                ) as picker:
                    if self._show_modal_dialog(picker, title) == wx.ID_OK:
                        target.SetValue(picker.GetPath())

            def _selected_action_id() -> str:
                index = action_choice.GetSelection()
                return action_ids[index] if 0 <= index < len(action_ids) else base.action_id

            def _collect_options(action_id: str) -> dict[str, object]:
                options: dict[str, object] = {}
                if action_id in {"move", "copy"}:
                    destination = action_dest_input.GetValue().strip()
                    if destination:
                        options["destination"] = destination
                elif action_id == "convert":
                    fmt_index = convert_choice.GetSelection()
                    options["target_format"] = convert_formats[fmt_index if fmt_index >= 0 else 0]
                elif action_id == "bw_transcribe":
                    t_index = transcribe_choice.GetSelection()
                    options["output_format"] = transcribe_formats[t_index if t_index >= 0 else 0]
                    ta_index = transcript_action_choice.GetSelection()
                    if ta_index > 0:
                        options["transcript_action"] = ta_ids[ta_index]
                elif action_id == "cloud_transcribe":
                    ta_index = transcript_action_choice.GetSelection()
                    if ta_index > 0:
                        options["transcript_action"] = ta_ids[ta_index]
                elif action_id == "run_macro":
                    macro_name = macro_input.GetValue().strip()
                    if macro_name:
                        options["macro_name"] = macro_name
                elif action_id == "run_python":
                    code = python_code.GetValue()
                    if code.strip():
                        options["code"] = code
                    suffix = python_suffix.GetValue().strip()
                    if suffix:
                        options["output_suffix"] = suffix
                    options["timeout_seconds"] = float(python_timeout.GetValue())
                elif action_id == "ai":
                    ai_index = ai_choice.GetSelection()
                    options["mode"] = ai_modes[ai_index if ai_index >= 0 else 0]
                    options["consent"] = bool(consent.GetValue())
                return options

            def _build_profile() -> WatchProfile:
                action_id = _selected_action_id()
                post_index = post_choice.GetSelection()
                post_action = (
                    post_values[post_index] if 0 <= post_index < len(post_values) else POST_LEAVE
                )
                sched_index = sched_choice.GetSelection()
                schedule_mode = (
                    sched_modes[sched_index]
                    if 0 <= sched_index < len(sched_modes)
                    else SCHED_ALWAYS
                )
                suffixes = tuple(
                    part.strip() for part in suffix_input.GetValue().split(",") if part.strip()
                )
                name_patterns = tuple(
                    part.strip() for part in pattern_input.GetValue().split(",") if part.strip()
                )
                return WatchProfile(
                    profile_id=base.profile_id,
                    name=name_input.GetValue().strip() or "Untitled profile",
                    enabled=bool(enabled.GetValue()),
                    folder_path=path_input.GetValue().strip(),
                    include_subfolders=bool(include_subfolders.GetValue()),
                    process_existing=bool(process_existing.GetValue()),
                    suffixes=suffixes,
                    name_patterns=name_patterns,
                    min_size_bytes=int(size_input.GetValue()),
                    min_age_seconds=float(age_input.GetValue()),
                    poll_interval_seconds=int(interval_input.GetValue()),
                    action_id=action_id,
                    action_options=_collect_options(action_id),
                    schedule_mode=schedule_mode,
                    schedule_start_minute=int(start_hour.GetValue()) * 60
                    + int(start_minute.GetValue()),
                    schedule_end_minute=int(end_hour.GetValue()) * 60 + int(end_minute.GetValue()),
                    post_action=post_action,
                    post_action_destination=post_dest_input.GetValue().strip(),
                ).normalized()

            def _on_preview(_event: object) -> None:
                candidate = _build_profile()
                sample = self._watch_dry_run_sample(candidate)
                preview = self._watch_service.registry.dry_run(
                    candidate.action_id,
                    WatchItem(source_path=sample, profile_id=candidate.profile_id),
                    candidate.action_options,
                )
                self._show_message_box(preview, "Dry-run preview", wx.ICON_INFORMATION | wx.OK)

            path_browse.Bind(wx.EVT_BUTTON, lambda _event: _pick_folder(path_input))
            action_dest_browse.Bind(wx.EVT_BUTTON, lambda _event: _pick_folder(action_dest_input))
            post_dest_browse.Bind(wx.EVT_BUTTON, lambda _event: _pick_folder(post_dest_input))
            preview_button.Bind(wx.EVT_BUTTON, _on_preview)

            ok_cancel = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
            root.Add(dialog, 1, wx.EXPAND | wx.ALL, 8)
            if ok_cancel is not None:
                root.Add(ok_cancel, 0, wx.EXPAND | wx.ALL, 8)
            dialog.SetSizerAndFit(root)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None

            updated = _build_profile()
            problems = updated.validate()
            if problems:
                self._show_message_box(
                    "Please fix the following:\n\n- " + "\n- ".join(problems),
                    title,
                    wx.ICON_WARNING | wx.OK,
                )
                return None
            return updated
