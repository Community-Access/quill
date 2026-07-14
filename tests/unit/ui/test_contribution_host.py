"""Tests for the first-party Host facade and the migrated line-transform feature.

These pin Wave 2 of the Quillin migration (``docs/quillins.md``
§9): the ``number_lines`` / ``hard_wrap_lines`` handlers now act through the
wx-free :class:`quill.core.contributions.Host` facade. A fake host exercises the
handler logic with no ``wx`` at all, and the live :class:`MainFrameHost` adapter
is checked to satisfy the protocol and delegate to ``MainFrame`` helpers.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.contributions import Host
from quill.ui.contribution_host import MainFrameHost
from quill.ui.features import line_transforms


class FakeHost:
    """In-memory ``Host`` that records edits without any wx dependency."""

    def __init__(self, text: str = "", selection: tuple[int, int] | None = None) -> None:
        self.text = text
        self.selection = selection if selection is not None else (0, 0)
        self.read_only = False
        self.status: list[str] = []
        self.announcements: list[str] = []
        self._answers: list[str | None] = []
        self.prompts: list[tuple[str, str, str]] = []

    def queue_prompt_answer(self, *answers: str | None) -> None:
        self._answers.extend(answers)

    # --- Host protocol -------------------------------------------------
    def get_text(self) -> str:
        return self.text

    def get_selection(self) -> tuple[int, int]:
        return self.selection

    def is_read_only(self) -> bool:
        return self.read_only

    def set_status(self, message: str) -> None:
        self.status.append(message)

    def announce(self, message: str) -> None:
        self.announcements.append(message)

    def is_verbosity_speech_enabled(self) -> bool:
        return True

    def prompt(self, title: str, label: str, value: str = "") -> str | None:
        self.prompts.append((title, label, value))
        return self._answers.pop(0) if self._answers else value

    def transform_block(self, transform: Callable[[str], str], status: str) -> None:
        if self.read_only:
            self.status.append("Document is read-only")
            return
        start, end = self.selection
        if start == end:
            start, end = 0, len(self.text)
        block = transform(self.text[start:end])
        self.text = self.text[:start] + block + self.text[end:]
        self.selection = (start, start + len(block))
        self.status.append(status)


def test_fake_host_satisfies_protocol() -> None:
    assert isinstance(FakeHost(), Host)


def test_main_frame_host_satisfies_protocol_structurally() -> None:
    # The adapter need not be instantiated (it wraps a live frame); assert it
    # implements every Host method so the live wiring type-checks.
    for name in (
        "get_text",
        "get_selection",
        "is_read_only",
        "set_status",
        "announce",
        "prompt",
        "transform_block",
    ):
        assert callable(getattr(MainFrameHost, name))


def test_number_lines_numbers_whole_document() -> None:
    host = FakeHost(text="alpha\nbeta")
    host.queue_prompt_answer("1")
    line_transforms.number_lines(host)
    assert host.text == "1. alpha\n2. beta"
    assert host.status[-1] == "Numbered lines"


def test_number_lines_honours_custom_start() -> None:
    host = FakeHost(text="a\nb")
    host.queue_prompt_answer("5")
    line_transforms.number_lines(host)
    assert host.text == "5. a\n6. b"


def test_number_lines_rejects_non_integer_start() -> None:
    host = FakeHost(text="a")
    host.queue_prompt_answer("not-a-number")
    line_transforms.number_lines(host)
    assert host.text == "a"
    assert host.status == ["Start value must be a whole number"]


def test_number_lines_cancel_is_a_no_op() -> None:
    host = FakeHost(text="a")
    host.queue_prompt_answer(None)
    line_transforms.number_lines(host)
    assert host.text == "a"
    assert host.status == []


def test_number_lines_respects_read_only_guard() -> None:
    host = FakeHost(text="a")
    host.read_only = True
    host.queue_prompt_answer("1")
    line_transforms.number_lines(host)
    assert host.text == "a"
    assert host.status == ["Document is read-only"]


def test_hard_wrap_defaults_width_to_widest_line() -> None:
    host = FakeHost(text="aaaa bbbb")
    line_transforms.hard_wrap_lines(host)
    # The prompt's default is offered from the widest line width.
    assert host.prompts[0][2] == str(len("aaaa bbbb"))


def test_hard_wrap_wraps_at_requested_width() -> None:
    host = FakeHost(text="aaaa bbbb")
    host.queue_prompt_answer("4")
    line_transforms.hard_wrap_lines(host)
    assert host.text == "aaaa\nbbbb"
    assert host.status[-1] == "Hard-wrapped at 4 characters"


def test_hard_wrap_rejects_non_positive_width() -> None:
    host = FakeHost(text="aaaa bbbb")
    host.queue_prompt_answer("0")
    line_transforms.hard_wrap_lines(host)
    assert host.text == "aaaa bbbb"
    assert host.status == ["Wrap width must be greater than zero"]


def test_hard_wrap_rejects_non_integer_width() -> None:
    host = FakeHost(text="aaaa bbbb")
    host.queue_prompt_answer("wide")
    line_transforms.hard_wrap_lines(host)
    assert host.text == "aaaa bbbb"
    assert host.status == ["Wrap width must be a whole number"]
