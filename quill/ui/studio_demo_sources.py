"""The Sound sources list of the Record a demonstration window.

Split from :mod:`quill.ui.studio_demo_dialog` (GATE-11). A list with a state
column, not check boxes (QUILL's list convention): Space puts the selected
source in or leaves it out; the screen reader's speech asks first.
"""

from __future__ import annotations

from dataclasses import replace

import wx

from quill.core.demo_recording import SoundSource
from quill.core.demo_recording_session import saved_level
from quill.core.studio_capture import CaptureTarget
from quill.ui.sync_guard import SyncGuard

READER_NAMES = {"jfw.exe": "JAWS", "nvda.exe": "NVDA", "narrator.exe": "Narrator"}
_IN, _OUT = "In the recording", "Left out"


def recordable(targets: list[CaptureTarget]) -> list[CaptureTarget]:
    """Version 1 records a named window, one display or the full desktop."""
    return [target for target in targets if target.kind in ("window", "display", "desktop")]


class DemoSourcesMixin:
    @property
    def _showing_level(self) -> SyncGuard:
        """UX-014: held while the level box is set to show the selected source."""
        guard = getattr(self, "_level_guard", None)
        if guard is None:
            guard = self._level_guard = SyncGuard()
        return guard

    def _saved_source(self, source_id: str) -> dict:
        for row in self.preferences.get("sources", []) or []:
            if isinstance(row, dict) and row.get("source_id") == source_id:
                return row
        return {}

    @staticmethod
    def _reader_label(executable: str) -> str:
        return READER_NAMES.get(executable.lower(), executable)

    def _reader(self) -> tuple[str, int]:
        index = self.reader.GetSelection()
        if 0 <= index < len(self.callbacks.readers):
            return self.callbacks.readers[index]
        return ("", 0)

    def _current_target(self) -> CaptureTarget | None:
        index = self.target.GetSelection()
        return self.targets[index] if 0 <= index < len(self.targets) else None

    def _build_sources(self) -> None:
        previous = {s.source_id: s for s in self.sources}
        target = self._current_target()
        sources: list[SoundSource] = []
        if target is not None and target.kind == "window" and target.process_id:
            app = (target.application or "the application").removesuffix(".exe")
            source_id = f"app-{(target.application or str(target.process_id)).lower()}"
            sources.append(
                SoundSource(
                    "application",
                    f"{app} sound",
                    source_id,
                    enabled=target.process_id != self.callbacks.studio_pid,
                    level_db=saved_level(self.preferences, source_id),
                    process_id=target.process_id,
                    process_name=target.application,
                )
            )
        sources.append(
            SoundSource(
                "system", "System sound", "system", level_db=saved_level(self.preferences, "system")
            )
        )
        mic_index = self.microphone.GetSelection()
        device = self.microphone.GetString(mic_index) if mic_index > 0 else ""
        sources.append(
            SoundSource(
                "microphone",
                "Microphone",
                "microphone",
                level_db=saved_level(self.preferences, "microphone"),
                device=device,
            )
        )
        reader, pid = self._reader()
        if reader:
            sources.append(
                SoundSource(
                    "screen_reader",
                    f"{self._reader_label(reader)} speech",
                    "screen-reader",
                    level_db=saved_level(self.preferences, "screen-reader"),
                    process_id=pid,
                    process_name=reader,
                )
            )
        for source in self.sources:
            if source.kind == "application" and source.source_id.startswith("added-"):
                sources.append(source)
        # Keep the user's on/off and level choices across a rebuild.
        self.sources = [
            replace(
                s, enabled=previous[s.source_id].enabled, level_db=previous[s.source_id].level_db
            )
            if s.source_id in previous and s.kind != "application"
            else s
            for s in sources
        ]
        self._fill_sources()

    def _fill_sources(self, select: int = 0) -> None:
        self.source_list.DeleteAllItems()
        for row, source in enumerate(self.sources):
            self.source_list.InsertItem(row, source.label)
            self.source_list.SetItem(row, 1, _IN if source.enabled else _OUT)
            self.source_list.SetItem(row, 2, f"{source.level_db:+.0f} dB")
        if self.sources:
            select = min(max(0, select), len(self.sources) - 1)
            self.source_list.Select(select)
            self.source_list.Focus(select)
            with self._showing_level:
                self.level.SetValue(self.sources[select].level_db)
        self._sync_remove()
        self._stale(None)

    def _selected_source(self) -> int:
        return self.source_list.GetFirstSelected()

    def _source_selected(self, _event: wx.ListEvent) -> None:
        row = self._selected_source()
        if 0 <= row < len(self.sources):
            with self._showing_level:
                self.level.SetValue(self.sources[row].level_db)
        self._sync_remove()

    def _sync_remove(self) -> None:
        row = self._selected_source()
        self.remove.Enable(
            0 <= row < len(self.sources) and self.sources[row].source_id.startswith("added-")
        )

    def _source_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_SPACE and not event.HasAnyModifiers():
            self._toggle_source()
            return
        event.Skip()

    def _toggle_source(self) -> None:
        row = self._selected_source()
        if not 0 <= row < len(self.sources):
            return
        source = self.sources[row]
        if source.kind == "screen_reader" and not source.enabled:
            if not self.callbacks.confirm(
                "Your screen reader's speech will be in the recording, including anything it "
                "reads while you record. Put it in?",
                "Screen reader speech",
            ):
                return
        if source.process_id and source.process_id == self.callbacks.studio_pid:
            wx.Bell()
            return
        self.sources[row] = replace(source, enabled=not source.enabled)
        # The state cell changes on the focused row, which the reader re-reads.
        self.source_list.SetItem(row, 1, _IN if self.sources[row].enabled else _OUT)
        self._stale(None)

    def _level_changed(self, _event: wx.Event) -> None:
        row = self._selected_source()
        if 0 <= row < len(self.sources) and not self._showing_level:
            value = round(self.level.GetValue())
            self.sources[row] = replace(self.sources[row], level_db=float(value))
            self.source_list.SetItem(row, 2, f"{value:+.0f} dB")
            self._stale(None)

    def _add_program(self, _event: wx.Event) -> None:
        chosen = self.callbacks.choose_program()
        if chosen is None:
            return
        kind, identity, name = chosen
        source_id = f"added-{name.lower()}"
        if any(s.source_id == source_id for s in self.sources):
            self._fill_sources(
                next(i for i, s in enumerate(self.sources) if s.source_id == source_id)
            )
            return
        if kind == "device":
            source = SoundSource(
                "device",
                f"Everything playing on {name}",
                source_id,
                enabled=True,
                device=str(identity),
            )
        else:
            source = SoundSource(
                "application",
                f"{name.removesuffix('.exe')} sound",
                source_id,
                enabled=True,
                process_id=int(identity),  # type: ignore[call-overload]
                process_name=name,
            )
        self.sources.append(source)
        self._fill_sources(len(self.sources) - 1)
        self.source_list.SetFocus()

    def _remove_program(self, _event: wx.Event) -> None:
        row = self._selected_source()
        if 0 <= row < len(self.sources) and self.sources[row].source_id.startswith("added-"):
            del self.sources[row]
            self._fill_sources(row - 1)
            self.source_list.SetFocus()

    def _microphone_changed(self, _event: wx.Event) -> None:
        index = self.microphone.GetSelection()
        device = self.microphone.GetString(index) if index > 0 else ""
        self.sources = [
            replace(s, device=device) if s.kind == "microphone" else s for s in self.sources
        ]
        self._stale(None)

    def _reader_changed(self, _event: wx.Event) -> None:
        self._build_sources()

    def _target_changed(self, _event: wx.Event) -> None:
        self._build_sources()

    def _refresh_targets(self, _event: wx.Event) -> None:
        previous = self._current_target()
        try:
            updated = recordable(self.callbacks.list_targets())
        except Exception as error:  # noqa: BLE001 - a refresh failure keeps the old list
            self.summary.ChangeValue(f"Could not refresh the targets: {error}")
            return
        self.targets = updated
        self.target.SetItems([t.friendly_label for t in updated])
        index = 0
        if previous is not None:
            for number, target in enumerate(updated):
                if (target.kind, target.window_handle, target.device) == (
                    previous.kind,
                    previous.window_handle,
                    previous.device,
                ):
                    index = number
                    break
        self.target.SetSelection(index if updated else wx.NOT_FOUND)
        self._build_sources()
