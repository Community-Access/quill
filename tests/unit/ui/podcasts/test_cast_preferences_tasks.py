"""Preference persistence stays ordered and never writes a live UI-owned record."""

from __future__ import annotations

import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import SimpleQueue
from types import SimpleNamespace

import pytest

from quill.core import family_preferences as family
from quill.core.podcasts import history as podcast_history
from quill.ui.podcasts.preferences_tasks import save_preferences


class Pool:
    def __init__(self):
        self.requests = []

    def submit(self, name, work, **options):
        request = SimpleNamespace(name=name, work=work, options=options)
        self.requests.append(request)
        return request

    def complete(self, request):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(request.work)
            try:
                result = future.result(timeout=5)
            except Exception as error:
                request.options["on_failure"](request.name, error)
            else:
                request.options["on_success"](request.name, result)

    def drain(self):
        while self.requests:
            self.complete(self.requests.pop(0))


@pytest.fixture
def host(monkeypatch, tmp_path):
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("quill.ui.podcasts.preferences_tasks.app_data_dir", lambda: tmp_path)
    pool = Pool()
    spoken = []
    return SimpleNamespace(
        _podcast_history=podcast_history.PodcastHistory(),
        _podcast_record_tasks=pool,
        _podcast_record_failures=SimpleQueue(),
        _cast_closing=False,
        _cast_closed=False,
        _announce=spoken.append,
        spoken=spoken,
        pool=pool,
        data_dir=tmp_path,
    )


def test_blocked_history_write_does_not_block_the_ui_or_receive_live_history(host, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    ui_thread = threading.get_ident()
    writes = []

    def blocked(_path, history):
        assert threading.get_ident() != ui_thread
        assert history is not host._podcast_history
        entered.set()
        assert release.wait(5)
        writes.append(copy.deepcopy(history))

    monkeypatch.setattr(podcast_history, "save_history", blocked)
    host._podcast_history.resume_on_launch = True

    save_preferences(host, {"resume_on_launch": True})

    assert not entered.is_set()
    assert host.spoken == []
    request = host.pool.requests.pop(0)
    assert request.options["safe_to_cancel"] is False
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(request.work)
        try:
            assert entered.wait(5)
            assert not future.done()
            host._podcast_history.episodes.append(
                podcast_history.PlayedEpisode("show", "episode", "Show", "Episode")
            )
        finally:
            release.set()
        result = future.result(timeout=5)
    request.options["on_success"](request.name, result)
    assert host.spoken == []
    host.pool.drain()

    assert writes[-1].resume_on_launch is True
    assert writes[-1].episodes == host._podcast_history.episodes
    assert host.spoken == ["Application preferences saved."]


def test_success_is_not_announced_when_persistence_fails(host, monkeypatch):
    def fail(_path, _history):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(podcast_history, "save_history", fail)
    host._podcast_history.resume_on_launch = True

    save_preferences(host, {"resume_on_launch": True})
    host.pool.drain()

    assert host.spoken == ["Preferences could not be saved. Recent Problems has the details."]
    assert host._podcast_record_failures.get_nowait() == ("preferences", "OSError")


def test_joining_sharing_does_not_overwrite_a_later_explicit_choice(host):
    radio = SimpleNamespace(announce_dialog_transitions=True, action_feedback="speech")
    family.set_sharing(host.data_dir, "radio", True, radio)
    history = host._podcast_history
    history.share_family_prefs = True
    save_preferences(host, {"share_family_prefs": True})
    history.action_feedback = "sound"
    save_preferences(host, {"action_feedback": "sound"})

    host.pool.drain()

    restored = podcast_history.load_history(host.data_dir)
    assert history.action_feedback == restored.action_feedback == "sound"
    assert history.announce_dialog_transitions is True
    assert restored.announce_dialog_transitions is True
    newcomer = SimpleNamespace(announce_dialog_transitions=False, action_feedback="both")
    family.set_sharing(host.data_dir, "newcomer", True, newcomer)
    assert newcomer.announce_dialog_transitions is True
    assert newcomer.action_feedback == "sound"
    assert host.spoken.count("Application preferences saved.") == 1


def test_a_replaced_history_cannot_be_restored_by_an_old_save_completion(host):
    history = host._podcast_history
    history.resume_on_launch = True
    save_preferences(host, {"resume_on_launch": True})
    host._podcast_history = podcast_history.PodcastHistory(close_action="minimize")

    host.pool.drain()

    restored = podcast_history.load_history(host.data_dir)
    assert restored.close_action == "minimize"
    assert restored.resume_on_launch is False


def test_completion_after_close_does_not_speak_or_modify_live_history(host):
    host._podcast_history.resume_on_launch = True
    save_preferences(host, {"resume_on_launch": True})
    host._cast_closing = True

    host.pool.drain()

    assert host.spoken == []
    assert podcast_history.load_history(host.data_dir).resume_on_launch is True
