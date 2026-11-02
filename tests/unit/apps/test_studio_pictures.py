"""Describe a Folder, Describe Again and Save Described Copies in the real Studio window.

The AI is a stand-in on the real service, so nothing leaves the machine; the
task manager runs each task at once, the way the UI would see it finish.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.usefixtures("closed_machine_doors")

_DIALOGS = "quill.ui.audio_studio.studio_picture_dialogs"


class _Account:
    def __init__(self) -> None:
        self.signed_in = True
        self.model = ""
        self.slug = "quill-studio"
        self.web_search = False
        self.ended_by_openai = False


class _Tasks:
    def submit(self, name, work, *, on_success=None, on_failure=None, **_kw):
        from quill.stability.task_manager import CancellationToken

        handle = SimpleNamespace(cancellation_token=CancellationToken())
        try:
            result = work(cancellation_token=handle.cancellation_token)
        except Exception as error:  # noqa: BLE001 - delivered like the real one
            if on_failure is not None:
                on_failure(name, error)
            return handle
        if on_success is not None:
            on_success(name, result)
        return handle


def _jpeg(path: Path, *, gps: bool = False, colour=(10, 120, 200)) -> Path:
    from PIL import Image

    image = Image.new("RGB", (900, 600), colour)
    exif = image.getexif()
    exif[0x010F] = "Canon"
    exif[0x0110] = "Canon EOS R6"
    exif.get_ifd(0x8769)[0x9003] = "2023:12:25 09:30:00"
    if gps:
        place = exif.get_ifd(0x8825)
        place.update({1: "N", 2: (40.0, 0.0, 0.0), 3: "W", 4: (75.0, 0.0, 0.0)})
    out = io.BytesIO()
    image.save(out, format="JPEG", exif=exif.tobytes())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out.getvalue())
    return path


@pytest.fixture
def studio(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.studio import StudioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: True)
    frame = StudioAppFrame()
    frame.said = []
    frame._announce = lambda message, **_kw: frame.said.append(str(message))
    frame.boxes = []
    frame.box_answer = wx.YES

    def box(message, _caption, _style=None, parent=None):
        frame.boxes.append(str(message))
        return frame.box_answer

    frame._show_message_box = box
    service = frame._ai_service()
    service._chatgpt = _Account()
    frame._ai_host().settings.ai_connection = ""
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame._task_manager = _Tasks()
    frame.opened = []
    frame.open_in_quill = lambda *paths: frame.opened.extend(paths)
    frame.asked = []

    def describe(path, question, *, on_done, on_error, requires):
        frame.asked.append((Path(path).name, question, requires))
        hook = getattr(frame, "on_describe", None)
        if hook is not None:
            hook()
        on_done(f"Description {len(frame.asked)}.")

    service.describe_image = describe
    frame._show_modal_dialog = lambda dialog, title=None: wx.ID_OK
    try:
        yield frame
    finally:
        for window in list(getattr(frame, "_ai_windows", {}).values()):
            if window:
                window.Destroy()
        remove = getattr(frame, "_remove_tray_icon", None)
        if callable(remove):
            remove()
        set_transition_announcement_policy(None)
        frame.frame.Destroy()


def _choices(folder: Path | str = "", **changes):
    from quill.core.ai.vision_prompts import PROMPT_ACCESSIBILITY
    from quill.ui.audio_studio.studio_picture_dialogs import PictureChoices

    values = {
        "style": "accessibility",
        "style_title": "Accessibility",
        "prompt": PROMPT_ACCESSIBILITY,
        "details": True,
        "location": False,
        "ceiling": 25,
        "folder": str(folder),
    }
    values.update(changes)
    return PictureChoices(**values)


def _fake_dialog(monkeypatch, name: str, choices) -> list:
    made: list = []

    class Dialog:
        def __init__(self, _parent, **kwargs) -> None:
            made.append(kwargs)

        def choices(self):
            return choices

        def Destroy(self) -> None:  # noqa: N802 - wx's name
            pass

    monkeypatch.setattr(f"{_DIALOGS}.{name}", Dialog)
    return made


def _results(quill_data_dir: Path) -> list[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in (quill_data_dir / "studio-descriptions").rglob("*.json")
    ]


def _ai_menu(frame) -> list[str]:
    bar = frame.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("AI"))
    return [item.GetItemLabel() for item in menu.GetMenuItems() if not item.IsSeparator()]


def test_the_four_rows_are_on_the_ai_menu_with_their_keys(studio) -> None:
    studio._ai_connection_refresh()
    labels = _ai_menu(studio)
    for label in (
        "Describe a &Folder...\tCtrl+Shift+F5",
        "Stop Describing the Fo&lder\tAlt+Shift+F5",
        "Describ&e Again...\tCtrl+Alt+F5",
        "Sa&ve Described Copies...\tCtrl+Alt+F6",
    ):
        assert label in labels


def test_a_folder_is_described_after_one_question_naming_count_and_receiver(
    studio, monkeypatch, tmp_path: Path, quill_data_dir: Path
) -> None:
    folder = tmp_path / "Holiday"
    for n in range(3):
        _jpeg(folder / f"p{n}.jpg", gps=True)
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder))
    studio.cmd_studio_describe_folder()
    assert studio.boxes[0].startswith("Pictures you ask about in QUILL Studio go to OpenAI")
    assert studio.boxes[1] == (
        "3 pictures will go to OpenAI on your ChatGPT plan, with each picture's date, camera "
        "and lens, one at a time. Send them?"
    )
    assert [name for name, _q, _r in studio.asked] == ["picture.jpg"] * 3
    _name, prompt, requires = studio.asked[0]
    assert requires == ("text", "pictures")
    assert prompt.startswith("Photo details, read from the file: taken 25 December 2023")
    assert "latitude" not in prompt  # GPS stays here unless the box is checked
    kept = _results(quill_data_dir)
    assert len(kept) == 3 and all(len(r["descriptions"]) == 1 for r in kept)
    assert kept[0]["descriptions"][0]["style"] == "accessibility"
    assert studio.opened and studio.opened[0].endswith("Holiday - descriptions.md")
    assert "Described 3 pictures. The descriptions open in QUILL." in studio.said
    assert "## p0.jpg" in Path(studio.opened[0]).read_text(encoding="utf-8")


def test_running_the_folder_again_sends_only_what_is_new(studio, monkeypatch, tmp_path) -> None:
    folder = tmp_path / "pics"
    _jpeg(folder / "a.jpg")
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder))
    studio.cmd_studio_describe_folder()
    _jpeg(folder / "b.jpg")
    studio.cmd_studio_describe_folder()
    assert len(studio.asked) == 2
    assert "1 is described already and not sent again." in studio.boxes[-1]


def test_saying_no_to_the_question_sends_nothing(studio, monkeypatch, tmp_path) -> None:
    folder = tmp_path / "pics"
    _jpeg(folder / "a.jpg")
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder))
    studio._ai_host().settings.ai_picture_consent = ["chatgpt"]
    studio.box_answer = wx.NO
    studio.cmd_studio_describe_folder()
    assert studio.asked == [] and studio.opened == []


def test_the_ceiling_stops_a_run_and_says_what_is_left(studio, monkeypatch, tmp_path) -> None:
    folder = tmp_path / "pics"
    for n in range(4):
        _jpeg(folder / f"p{n}.jpg")
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder, ceiling=2))
    studio.cmd_studio_describe_folder()
    assert len(studio.asked) == 2
    assert "This run stops after 2; 2 are left for the next run." in studio.boxes[-1]
    assert any("2 still to describe" in s for s in studio.said)


def test_location_goes_only_when_its_box_is_checked(studio, monkeypatch, tmp_path) -> None:
    folder = tmp_path / "pics"
    _jpeg(folder / "a.jpg", gps=True)
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder, location=True))
    studio.cmd_studio_describe_folder()
    assert "place it was taken" in studio.boxes[-1]
    assert "at latitude 40.0, longitude -75.0" in studio.asked[0][1]


def test_photo_details_unchecked_sends_only_the_style_prompt(studio, monkeypatch, tmp_path) -> None:
    from quill.core.ai.vision_prompts import PROMPT_ACCESSIBILITY

    folder = tmp_path / "pics"
    _jpeg(folder / "a.jpg", gps=True)
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder, details=False))
    studio.cmd_studio_describe_folder()
    assert studio.asked[0][1] == PROMPT_ACCESSIBILITY


def test_stop_ends_the_run_after_the_picture_in_hand(studio, monkeypatch, tmp_path) -> None:
    folder = tmp_path / "pics"
    for n in range(3):
        _jpeg(folder / f"p{n}.jpg")
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder))
    studio.on_describe = studio.cmd_studio_describe_folder_stop
    studio.cmd_studio_describe_folder()
    assert len(studio.asked) == 1
    assert "Stopping after the picture being described." in studio.said
    assert any(s.startswith("Stopped. Described 1 picture.") for s in studio.said)
    assert studio.opened == []  # the document is written, not opened, after a Stop


def test_stop_with_nothing_running_says_so(studio) -> None:
    studio.cmd_studio_describe_folder_stop()
    assert studio.said == ["No folder is being described."]


def test_an_unreadable_picture_is_skipped_by_name(studio, monkeypatch, tmp_path) -> None:
    folder = tmp_path / "pics"
    _jpeg(folder / "a.jpg")
    (folder / "broken.jpg").write_bytes(b"not a picture")
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder))
    studio.cmd_studio_describe_folder()
    assert len(studio.asked) == 1
    assert any("1 picture could not be read: broken.jpg." in s for s in studio.said)


def test_the_free_ai_sends_nothing_and_opens_no_window(studio, monkeypatch, tmp_path) -> None:
    studio._ai_host().settings.ai_connection = "free"
    monkeypatch.setattr(type(studio._ai_service()), "signed_in", property(lambda self: True))
    monkeypatch.setattr("quill.ui.hosted_ai_connections.ask_yes_no", lambda *a, **k: False)
    made = _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(tmp_path))
    again = _fake_dialog(monkeypatch, "DescribeAgainDialog", _choices())
    for command in (studio.cmd_studio_describe_folder, studio.cmd_studio_describe_again):
        command()
    assert made == [] and again == [] and studio.asked == []


def test_safe_mode_refuses_the_picture_commands(studio, monkeypatch, tmp_path) -> None:
    studio._safe_mode = True
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(tmp_path))
    for command in (
        lambda s: s.cmd_studio_describe_folder(),
        lambda s: s.cmd_studio_describe_again(),
    ):
        studio.said.clear()
        command(studio)
        assert studio.said == ["AI is off in Safe Mode."]
    assert studio.asked == []


def test_describe_again_keeps_the_last_picture_s_descriptions_side_by_side(
    studio, monkeypatch, tmp_path
) -> None:
    from quill.core.ai.vision_prompts import PROMPT_TECHNICAL

    picture = _jpeg(tmp_path / "frame.jpg")
    monkeypatch.setattr(type(studio), "_studio_choose_picture", lambda self: picture)
    shown: list[str] = []
    monkeypatch.setattr(
        "quill.ui.hosted_ai_app_ask.show_picture_answer", lambda _host, text: shown.append(text)
    )
    studio.cmd_studio_describe_picture()
    made = _fake_dialog(
        monkeypatch,
        "DescribeAgainDialog",
        _choices(style="technical", style_title="Technical", prompt=PROMPT_TECHNICAL),
    )
    studio.cmd_studio_describe_again()
    assert made[0]["targets"][0] == "The picture you described last, frame.jpg"
    assert studio.asked[-1][1].endswith(PROMPT_TECHNICAL)
    both = shown[-1]
    assert both.startswith("Description 2: Technical style, My ChatGPT plan")
    assert "Description 1: Describe a Picture, My ChatGPT plan" in both
    studio.cmd_studio_describe_again()  # the same style again: from the cache
    assert len(studio.asked) == 2
    assert "Nothing was sent: this was asked already." in shown[-1]


def test_describe_again_over_a_folder_adds_a_second_description(
    studio, monkeypatch, tmp_path, quill_data_dir: Path
) -> None:
    from quill.core.ai.vision_prompts import PROMPT_CONCISE

    folder = tmp_path / "pics"
    _jpeg(folder / "a.jpg")
    _jpeg(folder / "b.jpg")
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder))
    studio.cmd_studio_describe_folder()
    made = _fake_dialog(
        monkeypatch,
        "DescribeAgainDialog",
        _choices(style="concise", style_title="Concise", prompt=PROMPT_CONCISE, target=0),
    )
    studio.cmd_studio_describe_again()
    assert made[0]["targets"][:3] == ["Every picture in pics", "a.jpg, in pics", "b.jpg, in pics"]
    assert len(studio.asked) == 4
    kept = _results(quill_data_dir)
    assert all(
        [d["style"] for d in r["descriptions"]] == ["accessibility", "concise"] for r in kept
    )
    text = Path(studio.opened[-1]).read_text(encoding="utf-8")
    assert "### Description 2: Concise style, My ChatGPT plan" in text


def test_describe_again_on_one_picture_of_the_folder(studio, monkeypatch, tmp_path) -> None:
    folder = tmp_path / "pics"
    _jpeg(folder / "a.jpg")
    _jpeg(folder / "b.jpg")
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder))
    studio.cmd_studio_describe_folder()
    _fake_dialog(monkeypatch, "DescribeAgainDialog", _choices(style="mood", target=2))
    studio.cmd_studio_describe_again()
    assert len(studio.asked) == 3
    assert studio.boxes[-1].startswith("1 picture will go to OpenAI on your ChatGPT plan")


def test_save_described_copies_writes_copies_and_never_into_the_folder(
    studio, monkeypatch, tmp_path
) -> None:
    from PIL import Image

    folder = tmp_path / "pics"
    original = _jpeg(folder / "a.jpg")
    before = original.read_bytes()
    _fake_dialog(monkeypatch, "DescribeFolderDialog", _choices(folder))
    studio.cmd_studio_describe_folder()
    copies = tmp_path / "copies"
    copies.mkdir()
    answers = iter([str(folder), str(folder)])
    monkeypatch.setattr(
        type(studio), "_studio_choose_folder", lambda self, *_a, **_k: next(answers)
    )
    studio.cmd_studio_save_described_copies()
    assert any("different folder" in b for b in studio.boxes)
    answers = iter([str(folder), str(copies)])
    studio.cmd_studio_save_described_copies()
    assert original.read_bytes() == before
    with Image.open(copies / "a.jpg") as opened:
        assert opened.getexif()[0x010E] == "Description 1."
    assert studio.said[-1] == "Saved 1 described copy in copies."


def test_save_described_copies_on_a_folder_never_described(studio, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        type(studio), "_studio_choose_folder", lambda self, *_a, **_k: str(tmp_path)
    )
    studio.cmd_studio_save_described_copies()
    assert studio.said[-1].startswith(f"No descriptions were found for {tmp_path.name}.")
