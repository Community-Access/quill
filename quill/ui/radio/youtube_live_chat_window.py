"""YouTube Live Chat: a stream's chat as a list that never moves under you.

Screen-reader-first, because a live chat is the most hostile thing a list can
show: hundreds of rows an hour, arriving while somebody is reading.

* **New rows never take focus, never move the selection, never make the list
  re-read itself.** They are appended at the bottom with ``InsertItem`` and
  nothing else -- no ``Set``, no rebuild, no ``SetItemState``. The one
  exception is the listener's own choice: with **Follow new messages** on, and
  only while focus is on the list's last row, the selection steps down onto
  the newest row so it is read.
* **A row reads author, message, labels** -- "Sam: great show, moderator".
  The time is on demand: in Full text, and on Ctrl+T.
* **Speaking new messages is off by default** and goes through the
  rate-limited announcer in :mod:`quill.core.radio.youtube_live_chat`: one
  sentence every few seconds at most, a burst as a count, Quiet Hours
  honoured. Ctrl+S turns it on and off.
* **Pause** (the check box, or Space on the list) holds the list still and
  counts what arrives.

Keys: Home/End and the arrows in the list; Ctrl+Up/Down to the previous/next
message by the same author; Ctrl+J to the newest message; Ctrl+L reads the
newest without moving; Ctrl+T says when the selected message was sent; Space
pauses and resumes; Ctrl+S turns speaking on or off; F6 and Shift+F6 move
between the list, Full text, the filter and the send box; Escape, Ctrl+W or
Ctrl+F4 close and return focus. The send box (shown when Quill Radio may act on
YouTube) sends on Enter; YouTube's chat takes one line, so Shift+Enter adds no
newline. A failed send keeps what you typed.

The reading itself is :class:`quill.core.radio.youtube_live_chat_reader.ChatReader`,
on its own thread; this window drains its queue on a timer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import youtube_live_chat as lc
from quill.core.radio.youtube_live_chat_reader import ChatReader

TITLE = "YouTube Live Chat"

#: How often the window drains the reader's queue and lets the announcer speak.
DRAIN_MS = 500


class YouTubeLiveChatWindow:
    """One video's live chat (or chat replay), in a peer window."""

    def __init__(
        self,
        parent: Any,
        *,
        video_title: str,
        page_url: str,
        announce: Callable[[str], None],
        reader: ChatReader | None = None,
        held_back: Callable[[], bool] = lambda: False,
        can_send: bool = False,
        send: Callable[[str, Callable[[], None], Callable[[str], None]], object] | None = None,
        playback_seconds: Callable[[], float | None] = lambda: None,
        on_failure: Callable[[str], None] | None = None,
        copy_text: Callable[[str], object] | None = None,
        return_focus: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._title = video_title.strip() or "this video"
        self._announce = announce
        self._reader = reader or ChatReader(
            page_url,
            on_error=lambda m: wx.CallAfter(self._failed, m),
            on_end=lambda: wx.CallAfter(self._ended),
        )
        self._feed = lc.ChatFeed()
        self._shown: list[lc.ChatMessage] = []
        self._replay_wait: list[lc.ChatMessage] = []
        self._announcer = lc.ChatAnnouncer(announce, held_back=held_back)
        self._remembered_mode = lc.SPEAK_ALL
        self._can_send = can_send
        self._send = send
        self._playback_seconds = playback_seconds
        self._on_failure = on_failure or (lambda _m: None)
        self._copy_text = copy_text
        self._return_focus = return_focus
        self._closed = False
        self._said_failure = False

        self.frame = wx.Frame(parent, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
        self.frame.SetMinSize((600, 480))
        self._panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        self._build()
        self._timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, lambda _e: self.drain(), self._timer)
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)

    # -- construction ----------------------------------------------------------

    def _build(self) -> None:
        wx = self._wx
        panel = self._panel
        root = wx.BoxSizer(wx.VERTICAL)
        self._status = wx.StaticText(panel, label=f"Connecting to the chat for {self._title}...")
        root.Add(self._status, 0, wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="F&ilter messages:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._filter = wx.TextCtrl(panel)
        self._filter.SetName("Filter messages")
        self._filter.SetHelpText(
            "Type words to show only the messages that contain all of them, in "
            "the message or its author's name. New messages that match keep "
            "arriving at the bottom. Clear the box to see everything again."
        )
        row.Add(self._filter, 1, wx.LEFT | wx.RIGHT, 6)
        root.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        speak_row = wx.BoxSizer(wx.HORIZONTAL)
        speak_row.Add(
            wx.StaticText(panel, label="S&peak new messages:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._speak = wx.Choice(panel, choices=[label for _v, label in lc.SPEAK_CHOICES])
        self._speak.SetSelection(0)
        self._speak.SetName("Speak new messages")
        self._speak.SetHelpText(
            "Off by default. Every message, only paid messages and those from "
            "moderators and the owner, or only messages that mention the word "
            "below. Quill Radio speaks at most once every few seconds and says a "
            "burst as a count, so a busy chat never floods your screen reader; "
            "paid messages and mentions keep their own words. Quiet Hours "
            "silence it. Ctrl+S turns speaking on and off from anywhere here."
        )
        speak_row.Add(self._speak, 0, wx.LEFT | wx.RIGHT, 6)
        speak_row.Add(
            wx.StaticText(panel, label="&Word to listen for:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._word = wx.TextCtrl(panel)
        self._word.SetName("Word to listen for")
        self._word.SetHelpText(
            "A word, such as your name, that makes a message worth hearing. "
            "Used by Only messages that mention a word, and a message with it "
            "is spoken in its own words whichever choice is made."
        )
        speak_row.Add(self._word, 1, wx.LEFT, 6)
        root.Add(speak_row, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(panel, label="Messa&ges:"), 0, wx.LEFT, 8)
        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        self._list.InsertColumn(0, "Message", width=900)
        self._list.SetName("Messages")
        self._list.SetHelpText(
            "The chat, oldest at the top and newest at the bottom: who wrote "
            "it, what they said, then whether it was paid or from a member, a "
            "moderator or the owner. New messages are added at the bottom "
            "without moving you. Home and End go to the first and newest; "
            "Ctrl+Up and Ctrl+Down go to the same person's previous or next "
            "message; Ctrl+J jumps to the newest; Ctrl+L reads the newest "
            "without moving; Ctrl+T says when the selected one was sent; Space "
            "pauses and resumes the list."
        )
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="Full te&xt:"), 0, wx.LEFT | wx.TOP, 8)
        self._full = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._full.SetName("Full text of the selected message")
        self._full.SetHelpText(
            "The selected message in full, with who wrote it, its labels and "
            "when it was sent. Links are written out whole here. Read it with "
            "the arrow keys; it cannot be changed."
        )
        root.Add(self._full, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._send_box: Any = None
        self._send_button: Any = None
        if self._can_send:
            send_row = wx.BoxSizer(wx.HORIZONTAL)
            send_row.Add(
                wx.StaticText(panel, label="&Send a message:"), 0, wx.ALIGN_CENTER_VERTICAL
            )
            self._send_box = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
            self._send_box.SetMaxLength(200)
            self._send_box.SetName("Send a message")
            self._send_box.SetHelpText(
                "Type a message for the chat and press Enter to send it as your "
                "YouTube account. YouTube allows one line of up to 200 "
                "characters. The box stays here after sending, and if sending "
                "fails what you typed is kept."
            )
            send_row.Add(self._send_box, 1, wx.LEFT | wx.RIGHT, 6)
            self._send_button = wx.Button(panel, label="Se&nd")
            self._send_button.SetHelpText("Sends what is in the box to the chat.")
            send_row.Add(self._send_button, 0)
            root.Add(send_row, 0, wx.EXPAND | wx.ALL, 8)

        checks = wx.BoxSizer(wx.HORIZONTAL)
        self._pause = wx.CheckBox(panel, label="Pa&use")
        self._pause.SetHelpText(
            "Holds the list still. New messages are counted instead of added, "
            "and arrive together when you turn this off. Space on the list does "
            "the same."
        )
        self._follow = wx.CheckBox(panel, label="&Follow new messages")
        self._follow.SetHelpText(
            "Off by default. When on, and you are on the newest message in the "
            "list, the selection moves down onto each new message so it is "
            "read. Anywhere else in the list nothing moves."
        )
        checks.Add(self._pause, 0, wx.RIGHT, 12)
        checks.Add(self._follow, 0)
        root.Add(checks, 0, wx.LEFT | wx.RIGHT, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._copy = wx.Button(panel, label="Cop&y Message")
        self._copy.SetHelpText("Puts the selected message, with its author, on the clipboard.")
        self._close = wx.Button(panel, wx.ID_CLOSE, label="Close")
        self._close.SetHelpText("Stops reading the chat and goes back to where you were.")
        buttons.Add(self._copy, 0, wx.RIGHT, 6)
        buttons.Add(self._close, 0)
        root.Add(buttons, 0, wx.ALL, 8)
        panel.SetSizer(root)

        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, self._close, modeless=True)
        self._filter.Bind(wx.EVT_TEXT, lambda _e: self.apply_filter())
        self._speak.Bind(wx.EVT_CHOICE, lambda _e: self._sync_speech())
        self._word.Bind(wx.EVT_TEXT, lambda _e: self._sync_speech())
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: self._show_selected())
        self._pause.Bind(
            wx.EVT_CHECKBOX, lambda _e: self.set_paused(self._pause.GetValue(), from_box=True)
        )
        self._copy.Bind(wx.EVT_BUTTON, lambda _e: self.copy_selected())
        if self._send_box is not None:
            self._send_box.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.send_typed())
            self._send_button.Bind(wx.EVT_BUTTON, lambda _e: self.send_typed())

    # -- reading ---------------------------------------------------------------

    def start(self) -> None:
        self._reader.start()
        self._timer.Start(DRAIN_MS)

    def drain(self) -> None:
        """Move what the reader has into the list; let the announcer speak."""
        if self._closed:
            return
        incoming = self._reader.drain()
        position = self._playback_seconds()
        if position is not None:
            replay = [m for m in incoming if m.offset_seconds >= 0]
            live = [m for m in incoming if m.offset_seconds < 0]
            self._replay_wait.extend(replay)
            due, self._replay_wait = lc.release_replay(self._replay_wait, position)
            incoming = live + due
        if incoming:
            self.receive(incoming)
        if not self._feed.paused:
            self._announcer.tick()

    def receive(self, messages: list[lc.ChatMessage]) -> None:
        """Append *messages* without moving the listener (see module doc)."""
        appended = self._feed.add(messages)
        if not appended:
            self._update_status()
            return
        words = self._filter.GetValue()
        visible = lc.filter_messages(appended, words)
        self._append_rows(visible)
        self._feed.trim()
        self._announcer.offer(appended)
        self._update_status()

    def _append_rows(self, messages: list[lc.ChatMessage]) -> None:
        if not messages:
            return
        list_ctrl = self._list
        last_before = list_ctrl.GetItemCount() - 1
        selected = list_ctrl.GetFirstSelected()
        following = (
            self._follow.GetValue()
            and self._list_has_focus()
            and last_before >= 0
            and selected == last_before
        )
        for message in messages:
            list_ctrl.InsertItem(list_ctrl.GetItemCount(), lc.row_label(message))
            self._shown.append(message)
        if following:
            newest = list_ctrl.GetItemCount() - 1
            list_ctrl.Select(newest)
            list_ctrl.Focus(newest)
            list_ctrl.EnsureVisible(newest)

    def _list_has_focus(self) -> bool:
        try:
            return self._wx.Window.FindFocus() is self._list
        except Exception:  # noqa: BLE001 - no focus is a valid answer
            return False

    def apply_filter(self) -> None:
        """Rebuild the visible rows for the filter words -- only when they change."""
        keep = self._selected()
        self._shown = lc.filter_messages(self._feed.messages, self._filter.GetValue())
        self._list.DeleteAllItems()
        for index, message in enumerate(self._shown):
            self._list.InsertItem(index, lc.row_label(message))
        if keep in self._shown:
            index = self._shown.index(keep)
            self._list.Select(index)
            self._list.Focus(index)
        self._show_selected()

    def _selected(self) -> lc.ChatMessage | None:
        index = self._list.GetFirstSelected()
        return self._shown[index] if 0 <= index < len(self._shown) else None

    def _show_selected(self) -> None:
        message = self._selected()
        self._full.SetValue(lc.full_text(message) if message is not None else "")

    def _update_status(self) -> None:
        count = len(self._feed.messages)
        text = f"Chat for {self._title}: {count:,} message{'' if count == 1 else 's'}"
        if self._feed.paused:
            text += f", paused, {self._feed.unseen:,} waiting"
        if self._status.GetLabel() != text:
            self._status.SetLabel(text)

    # -- commands --------------------------------------------------------------

    def set_paused(self, paused: bool, *, from_box: bool = False) -> None:
        """Pause or resume. From the check box itself the reader already says
        checked or not checked (GATE-13), so only the count is added."""
        if paused == self._feed.paused:
            return
        self._pause.SetValue(paused)
        if paused:
            self._feed.pause()
            self._announcer.clear()
            if not from_box:
                self._announce("Paused. New messages are counted.")
        else:
            released = self._feed.resume()
            self._append_rows(lc.filter_messages(released, self._filter.GetValue()))
            count = len(released)
            said = f"{count} new message{'' if count == 1 else 's'} while paused." if count else ""
            if not from_box:
                said = f"Resumed. {said}".strip()
            if said:
                self._announce(said)
        self._update_status()

    def toggle_speech(self) -> None:
        """Ctrl+S: off <-> the last choice that was on."""
        index = self._speak.GetSelection()
        mode = lc.SPEAK_CHOICES[max(0, index)][0]
        if mode != lc.SPEAK_OFF:
            self._remembered_mode = mode
            new = lc.SPEAK_OFF
        else:
            new = self._remembered_mode
        values = [value for value, _label in lc.SPEAK_CHOICES]
        self._speak.SetSelection(values.index(new))
        self._sync_speech()
        label = dict(lc.SPEAK_CHOICES)[new]
        self._announce(
            "Not speaking new messages."
            if new == lc.SPEAK_OFF
            else f"Speaking new messages: {label.lower()}."
        )

    def _sync_speech(self) -> None:
        index = max(0, self._speak.GetSelection())
        self._announcer.mode = lc.SPEAK_CHOICES[index][0]
        self._announcer.word = self._word.GetValue()
        if self._announcer.mode == lc.SPEAK_OFF:
            self._announcer.clear()

    def jump(self, step: int) -> None:
        """Ctrl+Up/Down: the same author's previous or next message."""
        start = self._list.GetFirstSelected()
        if start < 0:
            self._announce("Select a message first.")
            return
        index = lc.same_author_index(self._shown, start, step)
        if index < 0:
            who = self._shown[start].author
            self._announce(f"No {'earlier' if step < 0 else 'later'} message from {who}.")
            return
        self._select(index)

    def jump_to_newest(self) -> None:
        count = self._list.GetItemCount()
        if not count:
            self._announce("No messages yet.")
            return
        self._list.SetFocus()
        self._select(count - 1)

    def _select(self, index: int) -> None:
        self._list.Select(index)
        self._list.Focus(index)
        self._list.EnsureVisible(index)
        self._show_selected()

    def read_newest(self) -> None:
        """Ctrl+L: say the newest message without moving."""
        if not self._feed.messages:
            self._announce("No messages yet.")
            return
        newest = self._feed.messages[-1]
        said = lc.when_said(newest)
        self._announce(lc.row_label(newest) + (f", {said}" if said else ""))

    def say_time(self) -> None:
        message = self._selected()
        if message is None:
            self._announce("Select a message first.")
            return
        self._announce(lc.when_said(message).capitalize() or "YouTube did not say when.")

    def copy_selected(self) -> None:
        message = self._selected()
        if message is None:
            self._announce("Select a message first.")
            return
        text = lc.full_text(message)
        ok = self._copy_text(text) if self._copy_text is not None else _clipboard(self._wx, text)
        self._announce("Message copied." if ok is not False else "The clipboard is busy.")

    def send_typed(self) -> None:
        """Send the send box's text; clear it only once YouTube accepted it."""
        if self._send_box is None or self._send is None:
            return
        text = self._send_box.GetValue().strip()
        if not text:
            self._announce("Type a message first.")
            return
        box = self._send_box

        def _sent() -> None:
            if self._closed:
                return
            if box.GetValue().strip() == text:
                box.SetValue("")
            self._announce("Message sent.")

        def _failed(_reason: str) -> None:
            return  # the reason was already spoken; the text stays put

        self._send(text, _sent, _failed)

    # -- failures --------------------------------------------------------------

    def _failed(self, sentence: str) -> None:
        if self._closed or self._said_failure:
            return
        self._said_failure = True
        self._status.SetLabel(f"Chat for {self._title}: {sentence}")
        # announce-punctuation: exempt -- each part is a whole sentence
        self._announce(f"Live chat stopped. {sentence}")
        self._on_failure(sentence)

    def _ended(self) -> None:
        if self._closed:
            return
        self._status.SetLabel(f"Chat for {self._title} has ended.")
        self._announce("The live chat has ended.")

    # -- keys and closing --------------------------------------------------------

    def _focus_ring(self) -> list[Any]:
        ring = [self._list, self._full, self._filter]
        if self._send_box is not None:
            ring.append(self._send_box)
        return ring

    def cycle_focus(self, backwards: bool = False) -> None:
        ring = self._focus_ring()
        current = self._wx.Window.FindFocus()
        index = ring.index(current) if current in ring else -1
        step = -1 if backwards else 1
        ring[(index + step) % len(ring)].SetFocus()

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        ctrl = event.ControlDown()
        if key == wx.WXK_ESCAPE or (ctrl and key in (ord("W"), wx.WXK_F4)):
            self.frame.Close()
            return
        if key == wx.WXK_F6:
            self.cycle_focus(backwards=event.ShiftDown())
            return
        on_list = self._list_has_focus()
        if ctrl and not event.ShiftDown() and not event.AltDown():
            handled = {
                ord("S"): self.toggle_speech,
                ord("J"): self.jump_to_newest,
                ord("L"): self.read_newest,
                ord("T"): self.say_time,
            }.get(key)
            if handled is not None:
                handled()
                return
            if on_list and key in (wx.WXK_UP, wx.WXK_DOWN):
                self.jump(-1 if key == wx.WXK_UP else 1)
                return
        if on_list and key == wx.WXK_SPACE and not ctrl:
            self.set_paused(not self._feed.paused)
            return
        event.Skip()

    def _on_close(self, event: Any) -> None:
        self._closed = True
        try:
            self._timer.Stop()
        except Exception:  # noqa: BLE001 - a dying timer must not block closing
            pass
        self._reader.stop(timeout=0.5)
        target = self._return_focus
        event.Skip()
        if target is not None:
            self._wx.CallAfter(_refocus, target)


def _refocus(target: Any) -> None:
    try:
        if target:
            target.SetFocus()
    except Exception:  # noqa: BLE001 - the opener may have closed meanwhile
        return


def _clipboard(wx: Any, text: str) -> bool:
    try:
        if not wx.TheClipboard.Open():
            return False
        try:
            return bool(wx.TheClipboard.SetData(wx.TextDataObject(text)))
        finally:
            wx.TheClipboard.Close()
    except Exception:  # noqa: BLE001 - a busy clipboard is an answer, not a crash
        return False


__all__ = ["TITLE", "YouTubeLiveChatWindow"]
