"""Describe a Folder's wx-free half: finding, planning, resuming, keeping, the document."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from quill.core.ai import picture_batch as batch


def _jpeg(path: Path, colour=(200, 40, 40)) -> Path:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (64, 48), colour).save(out, format="JPEG")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out.getvalue())
    return path


def _described(results: Path, folder: Path, picture: Path, text: str = "A red square.", **kw):
    result = batch.with_description(
        batch.new_result(folder, picture),
        batch.Description(text=text, connection=kw.pop("connection", "chatgpt"), **kw),
    )
    batch.save_result(batch.result_path(results, folder, picture), result)
    return result


def test_find_pictures_takes_pictures_in_name_order_and_never_videos(tmp_path: Path) -> None:
    for name in ("img10.jpg", "img2.JPG", "clip.mp4", "notes.txt", ".hidden.png", "b.heic"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.png").write_bytes(b"x")
    names = [p.name for p in batch.find_pictures(tmp_path)]
    assert names == ["b.heic", "img2.JPG", "img10.jpg"]
    deep = [
        p.relative_to(tmp_path).as_posix() for p in batch.find_pictures(tmp_path, subfolders=True)
    ]
    assert "sub/deep.png" in deep


def test_a_folder_that_cannot_be_read_is_a_coded_sentence(tmp_path: Path) -> None:
    with pytest.raises(batch.BatchError) as raised:
        batch.find_pictures(tmp_path / "gone")
    assert raised.value.code == "QUILL-AI-PICTURE-BATCH-FAILED"


def test_results_live_apart_from_the_pictures_one_folder_per_source(tmp_path: Path) -> None:
    root = tmp_path / "data"
    a, b = tmp_path / "one" / "Photos", tmp_path / "two" / "Photos"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    assert batch.results_folder(root, a) != batch.results_folder(root, b)
    assert batch.results_folder(root, a).parent == root
    assert batch.results_folder(root, a).name.startswith("Photos-")


def test_a_second_run_describes_only_what_is_not_done(tmp_path: Path) -> None:
    folder = tmp_path / "pics"
    pictures = [_jpeg(folder / f"p{n}.jpg") for n in range(1, 5)]
    results = tmp_path / "results"
    _described(results, folder, pictures[0])
    _described(results, folder, pictures[2])
    plan = batch.plan_batch(folder, results, ceiling=25)
    assert [p.name for p in plan.pending] == ["p2.jpg", "p4.jpg"]
    assert plan.done == 2 and plan.left_after == 0


def test_a_changed_picture_counts_as_not_described(tmp_path: Path) -> None:
    folder = tmp_path / "pics"
    picture = _jpeg(folder / "p.jpg")
    results = tmp_path / "results"
    _described(results, folder, picture)
    _jpeg(picture, colour=(0, 0, 255))
    picture.write_bytes(picture.read_bytes() + b"\0" * 10)
    assert batch.plan_batch(folder, results, ceiling=5).pending == (picture,)


def test_the_ceiling_caps_one_run_and_the_question_names_count_and_receiver(tmp_path: Path) -> None:
    folder = tmp_path / "pics"
    pictures = [_jpeg(folder / f"p{n:02d}.jpg") for n in range(12)]
    results = tmp_path / "results"
    _described(results, folder, pictures[0])
    plan = batch.plan_batch(folder, results, ceiling=5)
    assert len(plan.to_send) == 5 and plan.left_after == 6
    sentence = batch.confirmation_sentence(
        plan, "OpenAI on your ChatGPT plan", with_what=", with each picture's date, camera and lens"
    )
    assert sentence == (
        "5 pictures will go to OpenAI on your ChatGPT plan, with each picture's date, camera "
        "and lens, one at a time. 1 is described already and not sent again. This run stops "
        "after 5; 6 are left for the next run. Send them?"
    )


def test_default_ceilings_are_small_on_a_plan_and_none_on_the_free_ai() -> None:
    assert batch.default_ceiling("chatgpt") == 25
    assert batch.default_ceiling("own_key", "claude") == 200
    assert batch.default_ceiling("own_key", "ollama") == 1000
    assert batch.default_ceiling("free") == 0


def test_describe_again_plans_by_style_connection_and_model(tmp_path: Path) -> None:
    folder = tmp_path / "pics"
    pictures = [_jpeg(folder / f"p{n}.jpg") for n in range(3)]
    results = tmp_path / "results"
    _described(results, folder, pictures[0], style="technical", model="m")
    _described(results, folder, pictures[1], style="accessibility", model="m")

    def needs(_picture: Path, result) -> bool:
        return result is None or not any(
            d.same_source("technical", "chatgpt", "m") for d in result.descriptions
        )

    plan = batch.plan_batch(folder, results, ceiling=10, needs=needs)
    assert [p.name for p in plan.pending] == ["p1.jpg", "p2.jpg"]
    one = batch.plan_batch(folder, results, ceiling=10, needs=needs, only=(pictures[1],))
    assert one.pending == (pictures[1],)


def test_results_round_trip_and_keep_no_coordinates(tmp_path: Path) -> None:
    folder = tmp_path / "pics"
    picture = _jpeg(folder / "beach.jpg")
    results = tmp_path / "results"
    kept = batch.with_description(
        batch.new_result(folder, picture, taken="14 June 2024", camera="Apple iPhone 15"),
        batch.Description(
            text="A beach at sunset.",
            connection="own_key",
            provider="claude",
            model="claude-sonnet-5",
            style="accessibility",
            style_title="Accessibility",
            details_sent=True,
            location_sent=True,
        ),
    )
    path = batch.result_path(results, folder, picture)
    batch.save_result(path, kept)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1 and "latitude" not in json.dumps(raw)
    assert batch.load_result(path) == kept
    assert batch.load_result(results / "nothing.json") is None


def test_progress_is_spoken_now_and_then_never_per_picture() -> None:
    counter = batch.ProgressCounter(212)
    said = [s for s in (counter.step() for _ in range(212)) if s]
    assert said[0] == "22 of 212 described." and len(said) == 9
    small = batch.ProgressCounter(3)
    assert [small.step(), small.step(skipped=True), small.step()] == ["", "", ""]


def test_the_finished_sentence_counts_skips_and_what_is_left() -> None:
    assert batch.finished_sentence(3, []) == "Described 3 pictures."
    assert batch.finished_sentence(1, ["a.heic"], left=4, stopped=True) == (
        "Stopped. Described 1 picture. 1 picture could not be read: a.heic. 4 still to describe; "
        "run Describe a Folder on it again to carry on."
    )


def test_the_document_has_a_heading_per_picture_and_both_descriptions_side_by_side(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "Holiday"
    picture = _jpeg(folder / "beach.jpg")
    results = tmp_path / "results"
    first = _described(
        results,
        folder,
        picture,
        text="# Scene\nA beach.",
        style="accessibility",
        style_title="Accessibility",
    )
    second = batch.with_description(
        first,
        batch.Description(
            text="Sand and sea.",
            connection="own_key",
            provider="claude",
            model="claude-x",
            style="concise",
            style_title="Concise",
        ),
    )
    batch.save_result(batch.result_path(results, folder, picture), second)
    document = batch.write_document(results, folder)
    text = document.read_text(encoding="utf-8")
    assert text.startswith("# Pictures in Holiday\n")
    assert batch.CREDIT in text
    assert "## beach.jpg" in text
    assert "### Description 1: Accessibility style, My ChatGPT plan" in text
    assert "### Description 2: Concise style, My own key (Anthropic Claude), claude-x" in text
    assert "# Scene" not in text and "Scene\nA beach." in text  # the model's heading flattened
