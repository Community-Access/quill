"""sherpa-onnx and Python onnxruntime in one process (dict.md, "The two-runtime
question, resolved", and D-26).

sherpa-onnx ships its own ``onnxruntime.dll`` (1.28.2 when this was written);
Python ``onnxruntime`` (1.31.0, Kokoro read-aloud) runs from its own
``onnxruntime_pybind11_state.pyd``. Measured 2026-10-13: in both import orders
both load and run, and only sherpa's ``onnxruntime.dll`` is mapped. That is the
fact QUILL relies on, and the latent risk is Windows' loaded-module rule: any
future package that loads an ``onnxruntime.dll`` *by name* would bind to
whichever copy loaded first. This test fails loudly the day that changes.

Each import order runs in a fresh interpreter, because which DLL loads first is
process state. Windows only, and it needs both runtimes installed and the
bundled ``silero_vad.onnx`` (``QUILL_DICTATION_MODELS``, ``build/dictation-models``
or an installed copy); it skips otherwise and never downloads anything. The VAD
model serves both runtimes: sherpa-onnx runs it as its voice detector, Python
onnxruntime as an ordinary session.

Plus the thread policy (``quill/core/onnx_threads.py``) that keeps the two pools
from oversubscribing a two-core computer, which needs neither runtime.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from quill.core.onnx_threads import kokoro_threads, kokoro_with_threads, session_options

_PROBE = r"""
import ctypes, ctypes.wintypes as wt, json, sys
import numpy as np

order, vad_path = sys.argv[1], sys.argv[2]

def run_sherpa():
    import sherpa_onnx
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = vad_path
    config.sample_rate = 16000
    vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=5)
    vad.accept_waveform(np.zeros(512, dtype=np.float32))

def run_onnxruntime():
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    session = ort.InferenceSession(vad_path, sess_options=options,
                                   providers=["CPUExecutionProvider"])
    feeds = {}
    for item in session.get_inputs():
        shape = [d if isinstance(d, int) and d > 0 else 1 for d in item.shape]
        if "int64" in item.type:
            feeds[item.name] = np.array(16000, dtype=np.int64).reshape(shape or ())
        else:
            if item.name == "input":
                shape = [1, 512]
            feeds[item.name] = np.zeros(shape, dtype=np.float32)
    session.run(None, feeds)

steps = [run_sherpa, run_onnxruntime]
for step in steps if order == "sherpa-first" else steps[::-1]:
    step()

psapi = ctypes.WinDLL("psapi")
kernel = ctypes.WinDLL("kernel32")
kernel.GetCurrentProcess.restype = wt.HANDLE
psapi.EnumProcessModules.argtypes = [
    wt.HANDLE, ctypes.POINTER(wt.HMODULE), wt.DWORD, ctypes.POINTER(wt.DWORD)
]
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, wt.HMODULE, wt.LPWSTR, wt.DWORD]
process = kernel.GetCurrentProcess()
modules = (wt.HMODULE * 2048)()
needed = wt.DWORD()
psapi.EnumProcessModules(process, modules, ctypes.sizeof(modules), ctypes.byref(needed))
names = []
for handle in modules[: needed.value // ctypes.sizeof(wt.HMODULE)]:
    buffer = ctypes.create_unicode_buffer(1024)
    psapi.GetModuleFileNameExW(process, handle, buffer, 1024)
    names.append(buffer.value)
print(json.dumps([n for n in names if n.lower().endswith("\\onnxruntime.dll")]))
"""


def _vad_model():
    from quill.core.windows_dictation.engines import vad_model_path

    return vad_model_path()


@pytest.mark.skipif(sys.platform != "win32", reason="the loaded-module rule is Windows'")
@pytest.mark.parametrize("order", ["sherpa-first", "onnxruntime-first"])
def test_both_runtimes_load_run_and_map_one_onnxruntime_dll(order: str, tmp_path) -> None:
    for module in ("sherpa_onnx", "onnxruntime", "numpy"):
        if importlib.util.find_spec(module) is None:
            pytest.skip(f"{module} is not installed here")
    vad = _vad_model()
    if vad is None:
        pytest.skip("the bundled silero_vad.onnx is not on this computer")
    probe = tmp_path / "probe.py"
    probe.write_text(_PROBE, encoding="utf-8")
    completed = subprocess.run(  # noqa: S603 - our own interpreter and script
        [sys.executable, "-I", str(probe), order, str(vad)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    mapped = json.loads(completed.stdout.strip().splitlines()[-1])
    assert len(mapped) == 1, mapped
    assert "sherpa_onnx" in mapped[0].lower()


# -- the thread policy ----------------------------------------------------------


@pytest.mark.parametrize(("cores", "threads"), [(1, 1), (2, 1), (4, 2), (8, 4), (32, 4)])
def test_kokoro_takes_half_the_cores_at_most_four(cores: int, threads: int) -> None:
    assert kokoro_threads(cores) == threads


def test_session_options_set_the_intra_op_pool() -> None:
    fake = SimpleNamespace(SessionOptions=lambda: SimpleNamespace())
    options = session_options(fake, 2)
    assert options.intra_op_num_threads == 2
    assert options.inter_op_num_threads == 1


def test_a_stand_in_kokoro_is_built_the_plain_way() -> None:
    made: list[tuple[str, str]] = []

    class OldKokoro:
        def __init__(self, model: str, voices: str) -> None:
            made.append((model, voices))

    kokoro_with_threads(OldKokoro, "m.onnx", "v.bin")
    assert made == [("m.onnx", "v.bin")]


def test_kokoro_is_built_on_a_thread_limited_session(monkeypatch) -> None:
    sessions: list[dict] = []

    class FakeOrt:
        @staticmethod
        def SessionOptions():  # noqa: N802 - onnxruntime's name
            return SimpleNamespace()

        @staticmethod
        def InferenceSession(path, sess_options, providers):  # noqa: N802
            sessions.append({"path": path, "threads": sess_options.intra_op_num_threads})
            return "session"

    class Kokoro:
        @classmethod
        def from_session(cls, session, voices):
            return (session, voices)

    monkeypatch.setitem(sys.modules, "onnxruntime", FakeOrt)
    monkeypatch.setitem(
        sys.modules, "kokoro_onnx", SimpleNamespace(resolve_providers=lambda: ["CPU"])
    )
    assert kokoro_with_threads(Kokoro, "m.onnx", "v.bin") == ("session", "v.bin")
    assert sessions == [{"path": "m.onnx", "threads": kokoro_threads()}]
