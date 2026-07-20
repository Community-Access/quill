"""Native messaging host -- the capture bridge's loopback fallback (PRD 46).

When a browser or security tool blocks the localhost HTTP capture bridge, the
extension can fall back to the `WebExtension` / `nativeMessaging` API, which
spawns this host as a stdio subprocess. The browser itself enforces which
extension may talk to the host (via the manifest's ``allowed_origins`` for
Chromium and ``allowed_extensions`` for Firefox), so the host trusts the stdio
channel and does not re-check the bearer token.

Wire format (the standard browser native-messaging protocol): each message is a
4-byte little-endian unsigned length prefix followed by that many bytes of
UTF-8 JSON. The host reads one message, dispatches it to the same
``CaptureBridge.handle_capture`` / ``handle_batch`` the HTTP bridge uses, and
writes one reply in the same framing. The host never starts the HTTP server --
it is the fallback for when that server is unreachable.

This module is fail-safe: protocol and registration functions return JSON-able
dicts and never raise out of the top level.

CLI::

    python -m quill.apps.beacon.native_messaging run
    python -m quill.apps.beacon.native_messaging register [--browser chrome|edge|firefox|all]
    python -m quill.apps.beacon.native_messaging unregister [--browser ...]
    python -m quill.apps.beacon.native_messaging status
"""

from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

from quill.apps.beacon.paths import data_dir

HOST_NAME = "com.communityaccess.quillbeacon"
MAX_MESSAGE = 1024 * 1024  # 1 MiB, the Chrome native-messaging cap.
_LENGTH = struct.Struct("<I")  # 4-byte little-endian unsigned int.

BROWSERS = ("chrome", "edge", "firefox")


# -- protocol (pure, testable) ------------------------------------------------


def read_message(stream_in) -> dict | None:
    """Read one framed native-messaging message. Return None at clean EOF."""
    header = stream_in.read(4)
    if not header or len(header) < 4:
        return None
    (length,) = _LENGTH.unpack(header)
    if length <= 0 or length > MAX_MESSAGE:
        return None  # protocol violation / oversize: stop the host
    body = stream_in.read(length)
    if len(body) < length:
        return None  # truncated: stop
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"__invalid__": True}


def write_message(stream_out, obj: dict) -> None:
    """Write one framed native-messaging message and flush."""
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    stream_out.write(_LENGTH.pack(len(body)))
    stream_out.write(body)
    try:
        stream_out.flush()
    except Exception:
        pass


# -- dispatch -----------------------------------------------------------------


def handle_message(msg: dict, bridge) -> dict:
    """Dispatch one inbound message to the capture bridge. Fail-safe."""
    if not isinstance(msg, dict) or msg.get("__invalid__"):
        return {"ok": False, "error": "invalid message"}
    kind = msg.get("type") or ""
    if kind == "capture":
        return bridge.handle_capture(msg)
    if kind == "capture-batch":
        return bridge.handle_batch(msg)
    if kind == "ping":
        return {"ok": True, "service": "QuillBeacon", "version": "1"}
    return {"ok": False, "error": f"unknown type: {kind!r}"}


def serve(bridge, *, stream_in=None, stream_out=None) -> int:
    """Read/handle/write loop until the browser closes stdin. Returns 0."""
    sin = stream_in if stream_in is not None else sys.stdin.buffer
    sout = stream_out if stream_out is not None else sys.stdout.buffer
    while True:
        try:
            msg = read_message(sin)
        except Exception as exc:  # stdin broken: stop cleanly
            write_message(sout, {"ok": False, "error": f"read failed: {exc}"})
            return 1
        if msg is None:
            return 0
        try:
            reply = handle_message(msg, bridge)
        except Exception as exc:  # never let one message kill the host
            reply = {"ok": False, "error": f"handler failed: {exc}"}
        write_message(sout, reply)


# -- host construction -------------------------------------------------------


def make_bridge():
    """Build a CaptureBridge for stdio handling (HTTP server NOT started)."""
    from quill.apps.beacon.capture_bridge import CaptureBridge

    base = data_dir()
    return CaptureBridge(base / "beacons.db", data_dir=str(base))


def run_host() -> int:
    bridge = make_bridge()
    try:
        return serve(bridge)
    finally:
        try:
            bridge.stop()  # closes the store handle
        except Exception:
            pass


# -- manifest + wrapper ------------------------------------------------------


def _wrapper_path() -> Path:
    suffix = ".cmd" if sys.platform.startswith("win") else ".sh"
    return data_dir() / f"native-messaging-host{suffix}"


def _wrapper_content(wrapper: Path) -> str:
    """A launcher that runs this module's ``run`` subcommand via stdio."""
    py = sys.executable
    if sys.platform.startswith("win"):
        # %~dp0 = script dir; quote python path; -u for unbuffered binary stdio.
        return f'@echo off\r\n"{py}" -u -m quill.apps.beacon.native_messaging run\r\n'
    return f'#!/bin/sh\nexec "{py}" -u -m quill.apps.beacon.native_messaging run "$@"\n'


def write_wrapper() -> Path:
    """Write the host wrapper script and return its path (chmod +x on POSIX)."""
    wrapper = _wrapper_path()
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(
        _wrapper_content(wrapper),
        encoding="utf-8",
        newline="" if sys.platform.startswith("win") else "\n",
    )
    if not sys.platform.startswith("win"):
        try:
            os.chmod(wrapper, 0o755)
        except OSError:
            pass
    return wrapper


def build_manifest(
    wrapper_path: Path, *, browser: str, extension_ids: list[str] | None = None
) -> dict:
    """Build the native-messaging host manifest for one browser.

    Chromium uses ``allowed_origins`` (``chrome-extension://<id>``); Firefox uses
    ``allowed_extensions`` (raw extension IDs). ``extension_ids`` lets the caller
    pin the allowed extension(s); when empty the host is open to any extension
    the user has granted the ``nativeMessaging`` permission to.
    """
    manifest = {
        "name": HOST_NAME,
        "description": "QuillBeacon capture bridge (native messaging fallback)",
        "path": str(wrapper_path),
        "type": "stdio",
    }
    ids = extension_ids or []
    if browser == "firefox":
        manifest["allowed_extensions"] = ids or ["quillbeacon@communityaccess.org"]
    else:  # chrome / edge (both Chromium)
        manifest["allowed_origins"] = ids or ["chrome-extension://quillbeacon/"]
    return manifest


# -- registration paths -------------------------------------------------------


def _manifest_filename() -> str:
    return f"{HOST_NAME}.json"


def _win_reg_path(browser: str) -> str:
    product = "NativeMessagingHosts"
    if browser == "chrome":
        product = r"Google\Chrome\NativeMessagingHosts"
    elif browser == "edge":
        product = r"Microsoft\Edge\NativeMessagingHosts"
    elif browser == "firefox":
        product = r"Mozilla\NativeMessagingHosts"
    return rf"Software\{product}"


def _posix_manifest_dir(browser: str) -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        if browser == "firefox":
            return home / "Library" / "Application Support" / "Mozilla" / "NativeMessagingHosts"
        return (
            home / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts"
            if browser == "chrome"
            else home
            / "Library"
            / "Application Support"
            / "Microsoft"
            / "Edge"
            / "NativeMessagingHosts"
        )
    # Linux
    if browser == "firefox":
        return home / ".mozilla" / "native-messaging-hosts"
    if browser == "edge":
        return home / ".config" / "microsoft-edge" / "NativeMessagingHosts"
    return home / ".config" / "google-chrome" / "NativeMessagingHosts"


# -- Windows registry --------------------------------------------------------


def _win_write_manifest(browser: str, manifest_path: str) -> dict:
    import winreg  # local import so tests can inject a fake via sys.modules

    root = winreg.HKEY_CURRENT_USER
    base = _win_reg_path(browser)
    try:
        with winreg.CreateKeyEx(root, base, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, HOST_NAME, 0, winreg.REG_SZ, manifest_path)
    except OSError as exc:
        return {"error": f"registry write failed: {exc}"}
    return {
        "ok": True,
        "browser": browser,
        "key": f"HKCU\\{base}\\{HOST_NAME}",
        "manifest": manifest_path,
    }


def _win_delete_tree(root, path: str, winreg) -> None:
    try:
        with winreg.OpenKeyEx(root, path, 0, winreg.KEY_READ) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _win_delete_tree(root, path + "\\" + sub, winreg)
        winreg.DeleteKey(root, path)
    except FileNotFoundError:
        pass


def _win_remove_manifest(browser: str) -> dict:
    import winreg

    root = winreg.HKEY_CURRENT_USER
    base = _win_reg_path(browser)
    try:
        with winreg.OpenKeyEx(root, base, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, HOST_NAME)
    except FileNotFoundError:
        return {"error": "not registered", "browser": browser}
    except OSError as exc:
        return {"error": f"registry delete failed: {exc}", "browser": browser}
    return {"ok": True, "browser": browser}


def _win_status(browser: str) -> dict:
    import winreg

    root = winreg.HKEY_CURRENT_USER
    base = _win_reg_path(browser)
    try:
        with winreg.OpenKeyEx(root, base, 0, winreg.KEY_READ) as key:
            value, _t = winreg.QueryValueEx(key, HOST_NAME)
        return {"registered": True, "browser": browser, "manifest": value}
    except FileNotFoundError:
        return {"registered": False, "browser": browser}


# -- POSIX file --------------------------------------------------------------


def _posix_write_manifest(browser: str, manifest: dict) -> dict:
    path = _posix_manifest_dir(browser) / _manifest_filename()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except OSError as exc:
        return {"error": f"manifest write failed: {exc}", "browser": browser}
    return {"ok": True, "browser": browser, "manifest": str(path)}


def _posix_remove_manifest(browser: str) -> dict:
    path = _posix_manifest_dir(browser) / _manifest_filename()
    try:
        if path.exists():
            path.unlink()
        else:
            return {"error": "not registered", "browser": browser}
    except OSError as exc:
        return {"error": f"manifest remove failed: {exc}", "browser": browser}
    return {"ok": True, "browser": browser}


def _posix_status(browser: str) -> dict:
    path = _posix_manifest_dir(browser) / _manifest_filename()
    return {
        "registered": path.exists(),
        "browser": browser,
        "manifest": str(path) if path.exists() else None,
    }


# -- public API --------------------------------------------------------------


def _resolve_browsers(browser: str) -> list[str]:
    if browser == "all":
        return list(BROWSERS)
    if browser in BROWSERS:
        return [browser]
    return []


def register(browser: str = "all", *, extension_ids: list[str] | None = None) -> dict:
    """Write the wrapper + manifest for one or all browsers. Fail-safe."""
    browsers = _resolve_browsers(browser)
    if not browsers:
        return {"error": f"unknown browser: {browser}"}
    try:
        wrapper = write_wrapper()
    except OSError as exc:
        return {"error": f"wrapper write failed: {exc}"}
    results = []
    for b in browsers:
        manifest = build_manifest(wrapper, browser=b, extension_ids=extension_ids)
        if sys.platform.startswith("win"):
            # Windows registry holds the manifest JSON path on disk too.
            mf_file = data_dir() / f"{HOST_NAME}.{b}.json"
            try:
                mf_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                res = _win_write_manifest(b, str(mf_file))
            except OSError as exc:
                res = {"error": str(exc), "browser": b}
        else:
            res = _posix_write_manifest(b, manifest)
        results.append(res)
    return {"ok": all(r.get("ok") for r in results), "wrapper": str(wrapper), "results": results}


def unregister(browser: str = "all") -> dict:
    """Remove the manifest for one or all browsers. Fail-safe."""
    browsers = _resolve_browsers(browser)
    if not browsers:
        return {"error": f"unknown browser: {browser}"}
    results = []
    for b in browsers:
        results.append(
            _win_remove_manifest(b) if sys.platform.startswith("win") else _posix_remove_manifest(b)
        )
    return {"ok": all(r.get("ok") for r in results), "results": results}


def status(browser: str = "all") -> dict:
    """Report registration state for one or all browsers."""
    browsers = _resolve_browsers(browser)
    if not browsers:
        return {"error": f"unknown browser: {browser}"}
    return {
        "results": [
            _win_status(b) if sys.platform.startswith("win") else _posix_status(b) for b in browsers
        ]
    }


# -- CLI ---------------------------------------------------------------------


def _cli(argv: list[str]) -> int:
    args = argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    action = args[0]
    browser = "all"
    if "--browser" in args:
        i = args.index("--browser")
        if i + 1 < len(args):
            browser = args[i + 1]
    if action == "run":
        return run_host()
    if action == "register":
        print(register(browser))
        return 0
    if action == "unregister":
        print(unregister(browser))
        return 0
    if action == "status":
        print(status(browser))
        return 0
    print(f"unknown action: {action}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv))
