"""autoupdate — vendored from accessibleapps/app_updater (MIT).

Upstream: https://github.com/accessibleapps/app_updater
License: MIT — see LICENSE in this directory.
"""

import contextlib
import io
import os
import platform
import tempfile
import zipfile
from logging import getLogger

import requests
from platform_utils import paths

logger = getLogger("autoupdate")


def _version_tuple(v: object) -> tuple[int, ...]:
    """Parse a version string into a comparable integer tuple.

    Leading digits of each segment are used so pre-release suffixes like
    "1.2.3rc1" or "2.0.0-beta" compare as (1,2,3) and (2,0,0) rather than
    silently mapping the whole string to (0,).
    """
    import re

    parts = []
    for segment in str(v).split("."):
        m = re.match(r"(\d+)", segment)
        parts.append(int(m.group(1)) if m else 0)
    return tuple(parts) if parts else (0,)


def perform_update(
    endpoint,
    current_version,
    app_name="",
    password=None,
    update_available_callback=None,
    progress_callback=None,
    update_complete_callback=None,
):
    requests_session = create_requests_session(app_name=app_name, version=current_version)
    available_update = find_update(endpoint, requests_session=requests_session)
    if not available_update:
        return
    available_version = available_update["current_version"]
    if (
        not _version_tuple(available_version) > _version_tuple(current_version)
        or platform.system() not in available_update["downloads"]
    ):
        return
    available_description = available_update.get("description", None)
    update_url = available_update["downloads"][platform.system()]
    logger.info(f"A new update is available. Version {available_version}")
    if callable(update_available_callback) and not update_available_callback(
        version=available_version, description=available_description
    ):
        logger.info("User canceled update.")
        return
    base_path = tempfile.mkdtemp()
    download_path = os.path.join(base_path, "update.zip")
    update_path = os.path.join(base_path, "update")
    downloaded = download_update(
        update_url,
        download_path,
        requests_session=requests_session,
        progress_callback=progress_callback,
    )
    extracted = extract_update(downloaded, update_path, password=password)
    bootstrap_path = move_bootstrap(extracted)
    execute_bootstrap(bootstrap_path, extracted)
    logger.info("Update prepared for installation.")
    if callable(update_complete_callback):
        update_complete_callback()


def create_requests_session(app_name=None, version=None):
    user_agent = ""
    session = requests.session()
    if app_name:
        user_agent = f" {app_name}/{version!r}"
    session.headers["User-Agent"] = str(session.headers["User-Agent"]) + user_agent
    return session


def find_update(endpoint, requests_session):
    response = requests_session.get(endpoint)
    response.raise_for_status()
    return response.json()


def download_update(
    update_url,
    update_destination,
    requests_session,
    progress_callback=None,
    chunk_size=io.DEFAULT_BUFFER_SIZE,
):
    total_downloaded = total_size = 0
    with open(update_destination, "w+b") as outfile:
        download = requests_session.get(update_url, stream=True)
        total_size = int(download.headers.get("content-length", 0))
        logger.debug(f"Total update size: {total_size}")
        download.raise_for_status()
        for chunk in download.iter_content(chunk_size):
            outfile.write(chunk)
            total_downloaded += len(chunk)
            if callable(progress_callback):
                _call_callback(progress_callback, total_downloaded, total_size)
    logger.debug("Update downloaded")
    return update_destination


def extract_update(update_archive, destination, password=None):
    # extractall is safe against path-traversal components in Python >= 3.12.
    with contextlib.closing(zipfile.ZipFile(update_archive)) as archive:
        if password:
            archive.setpassword(password)
        archive.extractall(path=destination)
    logger.debug("Update extracted")
    return destination


def move_bootstrap(extracted_path):
    working_path = os.path.abspath(os.path.join(extracted_path, ".."))
    if platform.system() == "Darwin":
        extracted_path = os.path.join(extracted_path, "Contents", "Resources")
    downloaded_bootstrap = os.path.join(extracted_path, bootstrap_name())
    new_bootstrap_path = os.path.join(working_path, bootstrap_name())
    os.rename(downloaded_bootstrap, new_bootstrap_path)
    return new_bootstrap_path


def execute_bootstrap(bootstrap_path, source_path):
    if platform.system() == "Windows":
        pid = os.getpid()
        arguments = rf'"{pid}" "{source_path}" "{paths.app_path()}" "{paths.get_executable()}"'
        import win32api  # type: ignore[import]

        win32api.ShellExecute(0, "open", bootstrap_path, arguments, "", 5)
    else:
        import subprocess

        _make_executable(bootstrap_path)
        # Use an argument list (not shell=True) so paths with spaces are safe.
        subprocess.Popen([
            bootstrap_path,
            str(os.getpid()),
            source_path,
            paths.app_path(),
            paths.get_executable(),
        ])
    logger.info("Bootstrap executed")


def bootstrap_name():
    if platform.system() == "Windows":
        return "bootstrap.exe"
    if platform.system() == "Darwin":
        return "bootstrap-mac.sh"
    return "bootstrap-lin.sh"


def _make_executable(path):
    import stat

    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)


def _call_callback(callback, *args, **kwargs):
    try:
        callback(*args, **kwargs)
    except Exception:
        logger.exception(
            f"Failed calling callback {callback!r} with args {args!r} and kwargs {kwargs!r}"
        )
