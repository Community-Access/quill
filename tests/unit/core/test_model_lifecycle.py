"""Unit tests for the wx-free model lifecycle policy (Phase 2 runtime memory)."""

from __future__ import annotations

import threading

import pytest

from quill.core.model_lifecycle import (
    UNLIMITED,
    ModelLifecycleManager,
    Unloadable,
    build_manager,
    should_auto_low_resource,
)


class FakeClock:
    """Deterministic, advanceable monotonic clock for tests."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeModel:
    """A loadable handle that records unload() calls."""

    def __init__(self) -> None:
        self.unloaded = 0

    def unload(self) -> None:
        self.unloaded += 1


def test_fakemodel_satisfies_unloadable_protocol() -> None:
    assert isinstance(FakeModel(), Unloadable)


# --- idle sweep ------------------------------------------------------------


def test_sweep_unloads_only_idle_resources() -> None:
    clock = FakeClock()
    mgr = ModelLifecycleManager(idle_timeout=600.0, clock=clock)
    a, b = FakeModel(), FakeModel()
    mgr.note_loaded("a", a)
    clock.advance(300)
    mgr.note_loaded("b", b)  # b loaded 300s after a

    clock.advance(400)  # a idle 700s, b idle 400s
    unloaded = mgr.sweep_idle()

    assert unloaded == ["a"]
    assert a.unloaded == 1
    assert b.unloaded == 0
    assert mgr.loaded_keys() == ["b"]


def test_touch_resets_idle_timer() -> None:
    clock = FakeClock()
    mgr = ModelLifecycleManager(idle_timeout=600.0, clock=clock)
    model = FakeModel()
    mgr.note_loaded("m", model)

    clock.advance(500)
    mgr.touch("m")  # used again
    clock.advance(500)  # only 500s since last touch

    assert mgr.sweep_idle() == []
    assert model.unloaded == 0


def test_sweep_disabled_when_timeout_non_positive() -> None:
    clock = FakeClock()
    mgr = ModelLifecycleManager(idle_timeout=0.0, clock=clock)
    model = FakeModel()
    mgr.note_loaded("m", model)
    clock.advance(10_000)
    assert mgr.sweep_idle() == []
    assert model.unloaded == 0


def test_failing_unload_is_swallowed_and_entry_dropped() -> None:
    clock = FakeClock()
    mgr = ModelLifecycleManager(idle_timeout=1.0, clock=clock)

    class Boom:
        def unload(self) -> None:
            raise RuntimeError("engine wedged")

    mgr.note_loaded("boom", Boom())
    clock.advance(5)
    # Must not raise, and the entry is still cleared.
    assert mgr.sweep_idle() == ["boom"]
    assert mgr.loaded_keys() == []


# --- low-resource eviction -------------------------------------------------


def test_reserve_is_noop_when_mode_off() -> None:
    mgr = ModelLifecycleManager(max_concurrent=UNLIMITED)
    for key in ("a", "b", "c"):
        mgr.note_loaded(key, FakeModel())
    assert mgr.reserve("d") == []
    assert set(mgr.loaded_keys()) == {"a", "b", "c"}


def test_reserve_evicts_lru_to_honor_cap() -> None:
    clock = FakeClock()
    mgr = ModelLifecycleManager(max_concurrent=1, clock=clock)
    a = FakeModel()
    mgr.note_loaded("a", a)
    clock.advance(1)

    evicted = mgr.reserve("b")  # cap is 1, so loading b must evict a

    assert evicted == ["a"]
    assert a.unloaded == 1
    assert mgr.loaded_keys() == []  # a gone; b not yet noted loaded


def test_reserve_evicts_least_recently_used_first() -> None:
    clock = FakeClock()
    mgr = ModelLifecycleManager(max_concurrent=2, clock=clock)
    a, b = FakeModel(), FakeModel()
    mgr.note_loaded("a", a)
    clock.advance(10)
    mgr.note_loaded("b", b)
    clock.advance(10)
    mgr.touch("a")  # a now more recently used than b

    evicted = mgr.reserve("c")  # room for 2, loading c -> evict 1 LRU == b

    assert evicted == ["b"]
    assert b.unloaded == 1
    assert a.unloaded == 0


def test_reserve_already_loaded_key_needs_no_slot() -> None:
    mgr = ModelLifecycleManager(max_concurrent=1)
    a = FakeModel()
    mgr.note_loaded("a", a)
    assert mgr.reserve("a") == []
    assert a.unloaded == 0


# --- single-flight ---------------------------------------------------------


def test_loading_returns_stable_lock_per_key() -> None:
    mgr = ModelLifecycleManager()
    assert mgr.loading("x") is mgr.loading("x")
    assert mgr.loading("x") is not mgr.loading("y")


def test_single_flight_serializes_concurrent_loads() -> None:
    mgr = ModelLifecycleManager()
    loads = 0
    ready = threading.Barrier(2)

    def load_once() -> None:
        nonlocal loads
        ready.wait()
        with mgr.loading("model"):
            if "model" not in mgr.loaded_keys():
                loads += 1
                mgr.note_loaded("model", FakeModel())

    threads = [threading.Thread(target=load_once) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert loads == 1  # the second waiter saw it already loaded


def test_note_unloaded_drops_tracking() -> None:
    mgr = ModelLifecycleManager()
    mgr.note_loaded("m", FakeModel())
    mgr.note_unloaded("m")
    assert mgr.loaded_keys() == []


# --- settings-aware factory ------------------------------------------------


@pytest.mark.parametrize(
    ("ram", "expected"),
    [(0.0, False), (-1.0, False), (2.0, True), (3.9, True), (4.0, False), (16.0, False)],
)
def test_should_auto_low_resource(ram: float, expected: bool) -> None:
    assert should_auto_low_resource(ram) is expected


def test_build_manager_user_enabled_caps_to_one() -> None:
    mgr = build_manager(low_resource_mode=True, idle_unload_minutes=10, total_ram_gb=32.0)
    assert mgr.max_concurrent == 1
    assert mgr.idle_timeout == 600.0


def test_build_manager_auto_enables_on_low_ram() -> None:
    mgr = build_manager(low_resource_mode=False, idle_unload_minutes=5, total_ram_gb=3.0)
    assert mgr.max_concurrent == 1  # auto-enabled despite the setting being off
    assert mgr.idle_timeout == 300.0


def test_build_manager_unlimited_on_capable_machine() -> None:
    mgr = build_manager(low_resource_mode=False, idle_unload_minutes=0, total_ram_gb=16.0)
    assert mgr.max_concurrent == UNLIMITED
    assert mgr.idle_timeout == 0.0  # 0 minutes -> never unload


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
