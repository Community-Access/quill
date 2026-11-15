"""A local WordPress Playground practice site (PRD 15.1, W7).

WordPress Playground runs a whole WordPress in WebAssembly with no server of
its own. Its command-line tool (``@wp-playground/cli``) is staged, pinned,
beside the bundled Node in ``tools/wp-playground-cli`` by
``scripts/fetch_build_deps.py --only wp-playground-cli``; nothing is ever
downloaded while QUILL runs. The runtime carries one pinned PHP WebAssembly
version and the matching WordPress core files. This module:

- finds the tool and Node (:func:`find_cli`), and says plainly when either
  is missing (:func:`missing_words`);
- builds the command that starts a site on ``127.0.0.1`` only
  (:func:`start_command`; a ``--require`` preload pins Playground's listener,
  which otherwise binds every interface, to loopback), with a blueprint
  (:func:`blueprint`) that signs in, makes an application password for QUILL
  and writes it to a folder on this computer the site can see (mounted), so
  QUILL connects with no password typed;
- keeps the site's files in one folder (:func:`practice_dir`), which Reset
  empties;
- starts the server (:func:`start_process`) only when its port is free, in a
  kill-on-close job so no server outlives QUILL, and stops the whole process
  tree (:func:`stop_process`);
- owns the one narrow exception to HTTPS (:func:`is_practice_address`).

The window decides when to start and stop. Wx-free.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

__all__ = [
    "CLI_DIR_NAME",
    "LOOPBACK_HOST",
    "PLAYGROUND_CLI_VERSION",
    "PRACTICE_PHP_VERSION",
    "PRACTICE_WORDPRESS_SHA1",
    "PRACTICE_WORDPRESS_SHA256",
    "PRACTICE_WORDPRESS_VERSION",
    "PORT",
    "PRACTICE_NAME",
    "PracticeTools",
    "blueprint",
    "clear_password",
    "crossing_warning",
    "together_warning",
    "find_cli",
    "is_practice_address",
    "missing_words",
    "practice_label",
    "practice_dir",
    "read_password",
    "site_url",
    "start_command",
]

CLI_DIR_NAME = "wp-playground-cli"
CLI_SCRIPT = Path("node_modules") / "@wp-playground" / "cli" / "wp-playground.js"
PLAYGROUND_CLI_VERSION = "3.1.64"
PRACTICE_PHP_VERSION = "8.3"
PRACTICE_WORDPRESS_VERSION = "7.1.4"
PRACTICE_WORDPRESS_SHA1 = "b552c39cd95d89895b4e7a55af53a03687aff4f6"
PRACTICE_WORDPRESS_SHA256 = "a147146c159362778ecbbbfb07bb20ddf4e85b130f971c824e656a8f938c5f87"
PORT = 9400
LOOPBACK_HOST = "127.0.0.1"
PRACTICE_NAME = "Practice Site"
_PASSWORD_FILE = "quill-practice-password.json"
_HANDOFF_DIR = "handoff"
_SETUP_MARKER = ".quill-practice-initialized"
_LOOPBACK_PRELOAD = "loopback-only.cjs"
_MU_PLUGIN = Path("wp-content") / "mu-plugins" / "quill-practice-site.php"
# WordPress accepts application passwords only over HTTPS or when the site's
# environment type is "local"; the Practice Site is plain HTTP on loopback, so
# without this a freshly made password is refused with 401 on every request.
# Written on every start, so it survives a blueprint that already ran.
_MU_PLUGIN_SOURCE = """<?php
/*
 * Plugin Name: QUILL Practice Site
 * Description: Written by QUILL. This WordPress runs only on 127.0.0.1, so
 * application passwords are allowed over its plain-HTTP loopback address.
 */
add_filter('wp_is_application_passwords_available', '__return_true');
"""
#: The host names that mean "this computer" (urlparse strips IPv6 brackets).
_LOOPBACK_NAMES = frozenset({"127.0.0.1", "localhost", "::1"})

# Playground's server calls ``listen(port)`` with no host, which Node binds to
# every network interface: anyone on the same Wi-Fi could reach the practice
# site and its well-known admin password. The CLI has no host option, so this
# preload, loaded with ``node --require`` before the CLI, pins every TCP
# listen in the process (and its worker threads, which inherit execArgv) to
# the loopback address. Named pipes and Unix sockets pass through untouched.
_LOOPBACK_PRELOAD_SOURCE = """'use strict';
// Written by QUILL for the Practice Site: listen on this computer only.
const net = require('net');
const original = net.Server.prototype.listen;
const HOST = '127.0.0.1';
function isPort(value) {
  return typeof value === 'number' || (typeof value === 'string' && /^\\d+$/.test(value));
}
net.Server.prototype.listen = function (...args) {
  if (args.length === 0 || typeof args[0] === 'function') {
    args = [0, HOST, ...args];
  } else if (args[0] === undefined || args[0] === null) {
    args = [0, HOST, ...args.slice(1)];
  } else if (isPort(args[0])) {
    if (typeof args[1] === 'string') {
      args[1] = HOST;
    } else {
      args.splice(1, 0, HOST);
    }
  } else if (typeof args[0] === 'object' && args[0].path === undefined && args[0].fd === undefined
             && args[0]._handle === undefined && args[0].handle === undefined) {
    args[0] = Object.assign({}, args[0], { host: HOST });
  }
  return original.apply(this, args);
};
"""


@dataclass(frozen=True)
class PracticeTools:
    node: Path | None
    cli: Path | None
    wordpress: Path | None = None
    wordpress_archive: Path | None = None

    @property
    def ready(self) -> bool:
        return (
            self.node is not None
            and self.cli is not None
            and (
                (self.wordpress is not None and (self.wordpress / "wp-load.php").is_file())
                or (self.wordpress_archive is not None and self.wordpress_archive.is_file())
            )
        )


def _tools_dirs(name: str) -> list[Path]:
    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / name)
    beside = Path(sys.executable).parent / "tools" / name
    if beside not in dirs:
        dirs.append(beside)
    build_deps = os.environ.get("QUILL_BUILD_DEPS_DIR", "").strip()
    if build_deps:
        dirs.append(Path(build_deps) / name)
    # Source runs use the same ignored staging cache as the release builder.
    # Installed builds find their copy above, beside the application runtime.
    repo_staged = Path(__file__).resolve().parents[3] / "build" / "deps" / name
    if repo_staged not in dirs:
        dirs.append(repo_staged)
    override = os.environ.get("QUILL_PLAYGROUND_CLI_DIR", "").strip()
    if override and name == CLI_DIR_NAME:
        dirs.insert(0, Path(override))
    return dirs


def find_cli() -> PracticeTools:
    """The bundled Node, Playground CLI and WordPress core payload, each or None."""
    cli_dirs = _tools_dirs(CLI_DIR_NAME)
    cli = next((d / CLI_SCRIPT for d in cli_dirs if (d / CLI_SCRIPT).is_file()), None)
    wordpress = next(
        (d / "wordpress" for d in cli_dirs if (d / "wordpress" / "wp-load.php").is_file()),
        None,
    )
    wordpress_archive = next(
        (
            d / f"wordpress-{PRACTICE_WORDPRESS_VERSION}.zip"
            for d in cli_dirs
            if (d / f"wordpress-{PRACTICE_WORDPRESS_VERSION}.zip").is_file()
        ),
        None,
    )
    node = next((d / "node.exe" for d in _tools_dirs("nodejs") if (d / "node.exe").is_file()), None)
    if node is None:
        found = shutil.which("node")
        node = Path(found) if found else None
    return PracticeTools(node, cli, wordpress, wordpress_archive)


def missing_words(tools: PracticeTools) -> str:
    if tools.ready:
        return ""
    if tools.cli is None:
        return (
            "The practice site needs WordPress Playground's tool, which this build of QUILL "
            "does not include yet. A build made with scripts/fetch_build_deps.py --only "
            "wp-playground-cli has it."
        )
    if tools.node is None:
        return "The practice site needs Node.js, which ships with QUILL's shared runtime."
    if (tools.wordpress is None or not (tools.wordpress / "wp-load.php").is_file()) and (
        tools.wordpress_archive is None or not tools.wordpress_archive.is_file()
    ):
        return "The practice site needs its pinned WordPress core files in this build of QUILL."
    return ""


def practice_dir(base: Path) -> Path:
    """Where the practice site keeps its files and the password it hands QUILL."""
    return base / "practice-site"


def site_url(port: int = PORT) -> str:
    return f"http://{LOOPBACK_HOST}:{port}"


def is_practice_address(url: str) -> bool:
    """True only for plain HTTP to this computer on the Practice Site's own port.

    This is the whole of QUILL's exception to "HTTPS only" for WordPress: a
    password may travel unencrypted solely to the local Playground server,
    which never leaves this computer. Another port on 127.0.0.1, a
    ``.localhost`` or ``.test`` name, or any LAN address still needs HTTPS.
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse((url or "").strip())
        port = parsed.port
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme.lower() == "http" and host in _LOOPBACK_NAMES and port == PORT


def practice_label(name: str, url: str) -> str:
    """The name the Workbench shows for a site: a practice site always says so.

    The Workbench keys every row, preview, history entry and status line by
    this name, so labelling it once here labels it everywhere. A practice
    profile renamed to "My Blog" shows as "My Blog (practice)"; a name that
    already says practice, and every real site, is left alone.
    """
    clean = (name or "").strip()
    if not is_practice_address(url) or "practice" in clean.lower():
        return clean
    return f"{clean} (practice)" if clean else PRACTICE_NAME


def _names(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def crossing_warning(action: str, practice: list[str], real: list[str]) -> str:
    """The question asked before practice work goes to a real site ("" when none does).

    *practice* are the source sites that are practice sites, *real* the
    target sites that are not. Content only crosses from the one to the other
    when the person answers this, by name, with the default on No.
    """
    if not practice or not real:
        return ""
    many = len(real) > 1
    return (
        f"{action} would send what is on {_names(practice)}, the practice site on this "
        f"computer, to {_names(real)}: {'real sites' if many else 'a real site'} that other "
        "people can see. Work on the practice site never goes anywhere else unless you choose "
        f"it here. Send it to {_names(real)}?"
    )


def together_warning(action: str, practice: list[str], real: list[str]) -> str:
    """The question asked before one action changes the practice site and real ones together.

    Promote to Network and Revoke Everywhere send no content between sites,
    but run on every site in scope at once: what was tried on the practice
    site would be done to real sites in the same step. "" when it would not.
    """
    if not practice or not real:
        return ""
    many = len(real) > 1
    return (
        f"{action} would change {_names(real)}, {'real sites' if many else 'a real site'} that "
        f"other people can see, in the same step as {_names(practice)}, the practice site on "
        "this computer. Practice and real sites are changed together only if you choose it "
        f"here. Change {_names(real)} too?"
    )


def _extract_wordpress_core(archive: Path, target: Path) -> None:
    """Verify and safely unpack the pinned core once into the practice site's data folder."""
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != PRACTICE_WORDPRESS_SHA256:
        raise RuntimeError(
            "The bundled WordPress core failed its SHA-256 check. Re-stage the Practice Site."
        )

    target.mkdir(parents=True, exist_ok=False)
    seen: set[str] = set()
    try:
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                path = PurePosixPath(info.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in info.filename
                    or not path.parts
                    or path.parts[0] != "wordpress"
                ):
                    raise RuntimeError(
                        f"The WordPress archive contains an unsafe path: {info.filename!r}"
                    )
                relative = path.parts[1:]
                if not relative:
                    continue
                name = "/".join(relative)
                if name in seen:
                    raise RuntimeError(f"The WordPress archive repeats a path: {name!r}")
                seen.add(name)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise RuntimeError(f"The WordPress archive contains a symbolic link: {name!r}")
                destination = target.joinpath(*relative)
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(info) as source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output)
    except (OSError, zipfile.BadZipFile) as exc:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError(
            "The bundled WordPress core could not be unpacked. Reset the Practice Site."
        ) from exc
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
    if not (target / "wp-load.php").is_file() or not (target / "license.txt").is_file():
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError("The bundled WordPress core is incomplete. Re-stage the Practice Site.")


def blueprint(handoff_mount: str = "/quill") -> dict[str, object]:
    """A small starter site with example content and a QUILL app password."""
    php = (
        "<?php require_once '/wordpress/wp-load.php';"
        "update_option('blogname', 'Practice Site');"
        "$category = term_exists('QUILL Practice', 'category');"
        "if (!$category) { $category = wp_insert_term('QUILL Practice', 'category'); }"
        "$category_id = is_array($category) && isset($category['term_id']) "
        "? (int) $category['term_id'] : (int) $category;"
        "$welcome = get_posts(array('name' => 'welcome-to-your-practice-site', "
        "'post_type' => 'page', 'post_status' => 'any', 'numberposts' => 1));"
        "if (!$welcome) { $page_id = wp_insert_post(array("
        "'post_type' => 'page', 'post_status' => 'publish', "
        "'post_name' => 'welcome-to-your-practice-site', "
        "'post_title' => 'Welcome to Your Practice Site', "
        "'post_content' => '<p>This local site is a safe place to learn the "
        "WordPress Workbench.</p>"
        "<h2>Try these steps</h2><ol><li>Open a post and read its properties.</li>"
        "<li>Change a draft, then preview it.</li><li>Explore media and comments.</li></ol>'"
        ")); update_option('show_on_front', 'page'); update_option('page_on_front', $page_id); }"
        "$post = get_posts(array('name' => 'a-first-practice-post', 'post_type' => 'post', "
        "'post_status' => 'any', 'numberposts' => 1));"
        "if (!$post) { wp_insert_post(array('post_type' => 'post', 'post_status' => 'publish', "
        "'post_name' => 'a-first-practice-post', 'post_title' => 'A First Practice Post', "
        "'post_category' => $category_id ? array($category_id) : array(), "
        "'post_content' => '<p>Use this article to explore headings, categories, "
        "status, and dates.</p>'"
        ")); }"
        "$draft = get_posts(array('name' => 'my-next-practice-story', 'post_type' => 'post', "
        "'post_status' => 'any', 'numberposts' => 1));"
        "if (!$draft) { wp_insert_post(array('post_type' => 'post', 'post_status' => 'draft', "
        "'post_name' => 'my-next-practice-story', 'post_title' => 'My Next Practice Story', "
        "'post_content' => '<p>This draft is private until you choose to publish it.</p>'"
        ")); }"
        f"$handoff_file = '{handoff_mount}/{_PASSWORD_FILE}';"
        "$credentials = is_file($handoff_file) ? json_decode("
        "file_get_contents($handoff_file), true) : null;"
        "if (!is_array($credentials) || empty($credentials['password'])) {"
        "$made = WP_Application_Passwords::create_new_application_password("
        "1, array('name' => 'QUILL Practice Site'));"
        "if (is_array($made) && !empty($made[0])) {"
        "$credentials = array('username' => 'admin', 'password' => $made[0]);"
        "if (file_put_contents($handoff_file, json_encode($credentials), LOCK_EX) === false) {"
        "$credentials = null; } } }"
        "if (is_array($credentials) && !empty($credentials['password'])) {"
        f"file_put_contents('{handoff_mount}/{_SETUP_MARKER}', '1', LOCK_EX); }}"
    )
    return {
        "landingPage": "/wp-admin/",
        "preferredVersions": {
            "php": PRACTICE_PHP_VERSION,
            "wp": PRACTICE_WORDPRESS_VERSION,
        },
        # No "login" step and no --login: Playground's auto-login answers every
        # cookie-less request with a 302 to itself, which QUILL's REST client
        # (application password, no cookies) and the readiness check can never
        # get past -- and it would hand admin cookies to any local process.
        "steps": [
            {"step": "runPHP", "code": php},
        ],
    }


def start_command(tools: PracticeTools, folder: Path, *, port: int = PORT) -> list[str]:
    """The argv that starts the practice site on this computer only."""
    if not tools.ready:
        raise RuntimeError(missing_words(tools))
    folder.mkdir(parents=True, exist_ok=True)
    wordpress = folder / "wordpress"
    if not wordpress.exists():
        if tools.wordpress is not None:
            shutil.copytree(tools.wordpress, wordpress)
        elif tools.wordpress_archive is not None:
            _extract_wordpress_core(tools.wordpress_archive, wordpress)
        else:
            raise RuntimeError(missing_words(tools))
    elif not (wordpress / "wp-load.php").is_file():
        raise RuntimeError(
            "The practice site's WordPress folder is incomplete. Reset the practice site, "
            "then start it again."
        )
    handoff = folder / _HANDOFF_DIR
    handoff.mkdir(parents=True, exist_ok=True)
    mu_plugin = wordpress / _MU_PLUGIN
    mu_plugin.parent.mkdir(parents=True, exist_ok=True)
    mu_plugin.write_text(_MU_PLUGIN_SOURCE, encoding="utf-8", newline="\n")
    preload = folder / _LOOPBACK_PRELOAD
    preload.write_text(_LOOPBACK_PRELOAD_SOURCE, encoding="utf-8", newline="\n")
    argv = [
        str(tools.node),
        "--require",
        str(preload),
        str(tools.cli),
        "server",
        f"--port={port}",
        f"--site-url={site_url(port)}",
        f"--php={PRACTICE_PHP_VERSION}",
        f"--wp={PRACTICE_WORDPRESS_VERSION}",
        "--mount-dir-before-install",
        str(wordpress),
        "/wordpress",
        "--wordpress-install-mode=install-from-existing-files-if-needed",
        "--mount-dir",
        str(handoff),
        "/quill",
        "--verbosity=quiet",
    ]
    if not (handoff / _SETUP_MARKER).is_file():
        plan = handoff / "blueprint.json"
        plan.write_text(json.dumps(blueprint(), indent=1), encoding="utf-8", newline="\n")
        argv.append(f"--blueprint={plan}")
    return argv


def read_password(folder: Path) -> tuple[str, str] | None:
    """(username, application password) the practice site left, or None yet."""
    # The root-level path was used by the first Practice Site prototype. Read
    # it during upgrades so an already-running local site can still connect.
    for path in (folder / _HANDOFF_DIR / _PASSWORD_FILE, folder / _PASSWORD_FILE):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(raw, dict) and raw.get("password"):
            return str(raw.get("username") or "admin"), str(raw["password"])
    return None


def clear_password(folder: Path) -> bool:
    """Remove current and legacy handoff files after Credential Manager stores the secret."""
    try:
        (folder / _HANDOFF_DIR / _PASSWORD_FILE).unlink(missing_ok=True)
        (folder / _PASSWORD_FILE).unlink(missing_ok=True)
    except OSError:
        return False
    return True


def reset(folder: Path) -> None:
    """Empty the practice site's folder, so the next start is a fresh WordPress."""
    if folder.is_dir():
        shutil.rmtree(folder)


# The process half lives in its own module (GATE-11); its names stay importable
# from here, resolved on first use because that module imports this one.
_PROCESS_NAMES = frozenset({
    "last_output",
    "port_problem",
    "start_process",
    "stop_process",
    "wait_for_site",
})


def __getattr__(name: str) -> Any:
    if name in _PROCESS_NAMES:
        from quill.core.wordpress import workbench_practice_process

        return getattr(workbench_practice_process, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
