"""Non-elevating JAWS/NVDA runtime diagnostics for Windows.

Requires psutil and pywin32. NVDA Controller Client DLL is optional and must
match the Python process architecture. No start timestamps are returned.
"""

from __future__ import annotations

import ctypes
import os
import platform
import sys
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

_NAMES = {"jfw.exe": "JAWS", "nvda.exe": "NVDA"}
_FIELDS = (
    "ProductName",
    "FileDescription",
    "CompanyName",
    "ProductVersion",
    "FileVersion",
    "OriginalFilename",
    "LegalCopyright",
)


def _windows_version(path: str) -> dict[str, str | None]:
    result = {name: None for name in _FIELDS}
    result["FixedFileVersion"] = None
    result["FixedProductVersion"] = None
    try:
        import win32api

        fixed = win32api.GetFileVersionInfo(path, "\\")
        for prefix in ("File", "Product"):
            ms, ls = fixed[f"{prefix}VersionMS"], fixed[f"{prefix}VersionLS"]
            result[f"Fixed{prefix}Version"] = f"{ms >> 16}.{ms & 65535}.{ls >> 16}.{ls & 65535}"
        try:
            translations = win32api.GetFileVersionInfo(path, r"\VarFileInfo\Translation")
        except (OSError, Exception):
            translations = []
        # Prefer first available localized resource, fallback to standard en-US.
        for lang, codepage in list(translations) + [(0x0409, 0x04B0), (0x0409, 0x04E4)]:
            for field in _FIELDS:
                if result[field]:
                    continue
                key = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\{field}"
                try:
                    result[field] = win32api.GetFileVersionInfo(path, key) or None
                except Exception:
                    pass
    except Exception:
        pass
    return result


def _client_arch() -> str:
    machine = platform.machine().lower()
    if "arm" in machine and sys.maxsize > 2**32:
        return "arm64"
    return "x64" if sys.maxsize > 2**32 else "x86"


def probe_nvda_controller(dll_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Check NVDA via its official Controller Client. Never triggers speech.

    Returns controller presence, communication state, optional PID and status.
    The caller must supply a compatible DLL or place it in nvda_client/<arch>/.
    """
    output: dict[str, Any] = {
        "available": False,
        "connected": False,
        "pid": None,
        "status": "Controller Client library not found",
    }
    if sys.platform != "win32":
        output["status"] = "Windows required"
        return output
    if dll_path is None:
        dll_path = (
            Path(__file__).resolve().parent
            / "nvda_client"
            / _client_arch()
            / "nvdaControllerClient.dll"
        )
    path = Path(dll_path).resolve()
    if not path.is_file():
        return output
    try:
        # Load a trusted local absolute path; do not consult DLL search path.
        client = ctypes.WinDLL(str(path))
        client.nvdaController_testIfRunning.argtypes = []
        client.nvdaController_testIfRunning.restype = ctypes.c_ulong
        output["available"] = True
        rc = client.nvdaController_testIfRunning()
        if rc:
            output["status"] = f"NVDA Controller Client returned Windows error {rc}"
            return output
        output["connected"] = True
        output["status"] = "NVDA Controller Client connected"
        try:
            get_pid = client.nvdaController_getProcessId
            get_pid.argtypes = [ctypes.POINTER(ctypes.c_ulong)]
            get_pid.restype = ctypes.c_ulong
            pid = ctypes.c_ulong()
            rc = get_pid(ctypes.byref(pid))
            if rc == 0 and pid.value:
                output["pid"] = pid.value
            elif rc == 1717:
                output["status"] += "; PID API unsupported (NVDA older than 2024.1)"
            elif rc:
                output["status"] += f"; PID API returned error {rc}"
        except AttributeError:
            output["status"] += "; PID API absent from DLL"
    except (OSError, ValueError, AttributeError) as exc:
        output["status"] = f"Controller Client load/call failed: {exc}"
    return output


def get_running_screen_readers(
    *, dll_path: str | os.PathLike[str] | None = None
) -> list[dict[str, Any]]:
    """Return all discoverable JAWS/NVDA processes, without start times."""
    if sys.platform != "win32" or psutil is None:
        return []
    controller = probe_nvda_controller(dll_path)
    readers: list[dict[str, Any]] = []
    for process in psutil.process_iter(["pid", "name"]):
        try:
            name = (process.info.get("name") or "").lower()
            if name not in _NAMES:
                continue
            pid = process.info["pid"]
            # Process.exe may be inaccessible without elevation. Preserve the partial report.
            try:
                exe = process.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                exe = None
            version = _windows_version(exe) if exe else {key: None for key in _FIELDS}
            if not exe:
                version.update(FixedFileVersion=None, FixedProductVersion=None)
            item: dict[str, Any] = {
                "name": _NAMES[name],
                "process_name": name,
                "pid": pid,
                "executable": exe,
                "version": (
                    version.get("ProductVersion")
                    or version.get("FixedProductVersion")
                    or version.get("FileVersion")
                    or version.get("FixedFileVersion")
                ),
                "product_version": version.get("ProductVersion")
                or version.get("FixedProductVersion"),
                "file_version": version.get("FileVersion") or version.get("FixedFileVersion"),
                "fixed_product_version": version.get("FixedProductVersion"),
                "fixed_file_version": version.get("FixedFileVersion"),
                "product_name": version.get("ProductName"),
                "description": version.get("FileDescription"),
                "publisher": version.get("CompanyName"),
                "original_filename": version.get("OriginalFilename"),
                "copyright": version.get("LegalCopyright"),
            }
            if name == "nvda.exe":
                item["nvda_api_available"] = controller["available"]
                item["nvda_api_connected"] = controller["connected"]
                item["nvda_api_matched_process"] = (
                    controller["pid"] == pid if controller["pid"] else None
                )
                item["nvda_api_status"] = controller["status"]
            readers.append(item)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
    return sorted(readers, key=lambda item: (item["name"], item["pid"]))


def get_screen_reader_info(*, dll_path: str | os.PathLike[str] | None = None) -> str:
    """Return complete readable diagnostic information as ONE string; no start time."""
    if sys.platform != "win32":
        return "Screen reader detection requires Windows."
    if psutil is None:
        return "Screen reader detection unavailable: install psutil and pywin32."
    readers = get_running_screen_readers(dll_path=dll_path)
    if not readers:
        probe = probe_nvda_controller(dll_path)
        if probe["connected"]:
            return (
                "NVDA is connected through its Controller Client API, "
                "but its process details are unavailable."
            )
        return "No running JAWS or NVDA process detected."
    labels = [
        ("Name", "name"),
        ("Version", "version"),
        ("Product version", "product_version"),
        ("File version", "file_version"),
        ("Fixed product version", "fixed_product_version"),
        ("Fixed file version", "fixed_file_version"),
        ("Product name", "product_name"),
        ("Description", "description"),
        ("Publisher", "publisher"),
        ("Original filename", "original_filename"),
        ("Copyright", "copyright"),
        ("Process name", "process_name"),
        ("Process ID", "pid"),
        ("Executable", "executable"),
    ]
    lines = [f"Running screen readers: {len(readers)}"]
    for index, reader in enumerate(readers, 1):
        lines.extend(["", f"Screen reader {index}:"])
        lines.extend(
            f"{label}: {reader.get(field) if reader.get(field) is not None else 'Unavailable'}"
            for label, field in labels
        )
        if reader["name"] == "NVDA":
            lines.extend([
                f"NVDA API available: {'Yes' if reader['nvda_api_available'] else 'No'}",
                f"NVDA API connected: {'Yes' if reader['nvda_api_connected'] else 'No'}",
                "NVDA API matched process: "
                + (
                    "Unknown"
                    if reader["nvda_api_matched_process"] is None
                    else ("Yes" if reader["nvda_api_matched_process"] else "No")
                ),
                f"NVDA API status: {reader['nvda_api_status']}",
            ])
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_screen_reader_info())
