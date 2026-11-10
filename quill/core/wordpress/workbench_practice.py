"""A practice WordPress site on this computer: WordPress Playground (PRD 15.1, W7).

WordPress Playground runs a whole WordPress in WebAssembly with no server of
its own. Its command-line tool (``@wp-playground/cli``) is staged, pinned,
beside the bundled Node in ``tools/wp-playground-cli`` by
``scripts/fetch_build_deps.py --only wp-playground-cli``; nothing is ever
downloaded while QUILL runs. This module:

- finds the tool and Node (:func:`find_cli`), and says plainly when either
  is missing (:func:`missing_words`);
- builds the command that starts a site on ``127.0.0.1`` only
  (:func:`start_command`), with a blueprint (:func:`blueprint`) that signs
  in, makes an application password for QUILL and writes it to a folder on
  this computer the site can see (mounted), so QUILL connects with no
  password typed;
- keeps the site's files in one folder (:func:`practice_dir`), which Reset
  empties.

The process itself is started and stopped by the window, through
:func:`quill.stability.safe_subprocess.spawn_subprocess_safely`. Wx-free.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "CLI_DIR_NAME",
    "PORT",
    "PRACTICE_NAME",
    "PracticeTools",
    "blueprint",
    "find_cli",
    "missing_words",
    "practice_dir",
    "read_password",
    "site_url",
    "start_command",
]

CLI_DIR_NAME = "wp-playground-cli"
CLI_SCRIPT = Path("node_modules") / "@wp-playground" / "cli" / "wp-playground.js"
PORT = 9400
PRACTICE_NAME = "Practice Site"
_PASSWORD_FILE = "quill-practice-password.json"


@dataclass(frozen=True)
class PracticeTools:
    node: Path | None
    cli: Path | None

    @property
    def ready(self) -> bool:
        return self.node is not None and self.cli is not None


def _tools_dirs(name: str) -> list[Path]:
    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / name)
    beside = Path(sys.executable).parent / "tools" / name
    if beside not in dirs:
        dirs.append(beside)
    override = os.environ.get("QUILL_PLAYGROUND_CLI_DIR", "").strip()
    if override and name == CLI_DIR_NAME:
        dirs.insert(0, Path(override))
    return dirs


def find_cli() -> PracticeTools:
    """The bundled Node and Playground's command-line tool, each or None."""
    cli = next(
        (d / CLI_SCRIPT for d in _tools_dirs(CLI_DIR_NAME) if (d / CLI_SCRIPT).is_file()), None
    )
    node = next((d / "node.exe" for d in _tools_dirs("nodejs") if (d / "node.exe").is_file()), None)
    if node is None:
        found = shutil.which("node")
        node = Path(found) if found else None
    return PracticeTools(node, cli)


def missing_words(tools: PracticeTools) -> str:
    if tools.ready:
        return ""
    if tools.cli is None:
        return (
            "The practice site needs WordPress Playground's tool, which this build of QUILL "
            "does not include yet. A build made with scripts/fetch_build_deps.py --only "
            "wp-playground-cli has it."
        )
    return "The practice site needs Node.js, which ships with QUILL's shared runtime."


def practice_dir(base: Path) -> Path:
    """Where the practice site keeps its files and the password it hands QUILL."""
    return base / "practice-site"


def site_url(port: int = PORT) -> str:
    return f"http://127.0.0.1:{port}"


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
        "$made = WP_Application_Passwords::create_new_application_password("
        "1, array('name' => 'QUILL Practice Site'));"
        f"file_put_contents('{handoff_mount}/{_PASSWORD_FILE}', json_encode(array("
        "'username' => 'admin', 'password' => $made[0])));"
    )
    return {
        "landingPage": "/wp-admin/",
        "preferredVersions": {"php": "8.3", "wp": "latest"},
        "steps": [
            {"step": "login", "username": "admin", "password": "password"},
            {"step": "runPHP", "code": php},
        ],
    }


def start_command(tools: PracticeTools, folder: Path, *, port: int = PORT) -> list[str]:
    """The argv that starts the practice site on this computer only."""
    if not tools.ready:
        raise RuntimeError(missing_words(tools))
    folder.mkdir(parents=True, exist_ok=True)
    plan = folder / "blueprint.json"
    plan.write_text(json.dumps(blueprint(), indent=1), encoding="utf-8", newline="\n")
    return [
        str(tools.node),
        str(tools.cli),
        "server",
        f"--port={port}",
        f"--blueprint={plan}",
        f"--mount={folder}:/quill",
        "--login",
    ]


def read_password(folder: Path) -> tuple[str, str] | None:
    """(username, application password) the practice site left, or None yet."""
    path = folder / _PASSWORD_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or not raw.get("password"):
        return None
    return str(raw.get("username") or "admin"), str(raw["password"])


def reset(folder: Path) -> None:
    """Empty the practice site's folder, so the next start is a fresh WordPress."""
    if folder.is_dir():
        shutil.rmtree(folder)
