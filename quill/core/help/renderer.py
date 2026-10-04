"""Topic registry and renderer for the QUILL context-sensitive help system.

Topics are stored in ``topics.json`` alongside this file. Each topic has:

- ``id`` (str): name-keyed lookup key, e.g. ``"main.search_text"`` or
  ``"prefs.theme"``; matches ``ctrl.GetName()`` in the UI.
- ``title`` (str): short human label shown as the dialog heading.
- ``body`` (str): one-to-four sentence plain-text explanation.
- ``keystrokes`` (list[str], optional): keyboard shortcuts relevant to this
  control.
- ``see_also`` (list[str], optional): list of other topic IDs to link to.
- ``user_guide_section`` (str, optional): section anchor in the user guide,
  e.g. ``"search"``; enables the "Open in User Guide" link in the help dialog.
- ``tokens`` (dict[str, str], optional): ``{token: value}`` substitution map
  for the body and title, resolved at render time.

The renderer supports two output modes: ``"live"`` (for the in-app dialog)
and ``"doc"`` (for generated Markdown reference docs).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_TOPICS_PATH = Path(__file__).with_name("topics.json")
_log = logging.getLogger(__name__)


@dataclass(slots=True)
class HelpTopic:
    id: str
    title: str
    body: str
    keystrokes: list[str] = field(default_factory=list)
    see_also: list[str] = field(default_factory=list)
    user_guide_section: str = ""
    tokens: dict[str, str] = field(default_factory=dict)

    def render(self, mode: str = "live") -> str:
        """Render the topic for *mode* (``"live"`` or ``"doc"``)."""
        body = self.body
        title = self.title
        for token, value in self.tokens.items():
            placeholder = f"{{{token}}}"
            body = body.replace(placeholder, value)
            title = title.replace(placeholder, value)
        if mode == "doc":
            return _render_doc(self, title, body)
        return _render_live(self, title, body)


def _render_live(topic: HelpTopic, title: str, body: str) -> str:
    lines = [title, "", body]
    if topic.keystrokes:
        lines += ["", "Keyboard shortcuts:"]
        lines += [f"  {k}" for k in topic.keystrokes]
    if topic.see_also:
        lines += ["", f"See also: {', '.join(topic.see_also)}"]
    return "\n".join(lines)


def _render_doc(topic: HelpTopic, title: str, body: str) -> str:
    lines = [f"### {title}", "", body]
    if topic.keystrokes:
        lines += ["", "**Keyboard shortcuts:**"]
        lines += [f"- {k}" for k in topic.keystrokes]
    if topic.user_guide_section:
        lines += ["", f"[Full details in the user guide](#{topic.user_guide_section})"]
    return "\n".join(lines)


class HelpRenderer:
    """Loads and serves help topics by control name."""

    def __init__(self, topics: dict[str, HelpTopic]) -> None:
        self._topics = topics

    @classmethod
    def from_file(cls, path: Path | None = None) -> HelpRenderer:
        return cls(load_topics(path))

    def get(self, ctrl_name: str) -> HelpTopic | None:
        """Return the topic for *ctrl_name*, or ``None`` if not covered."""
        return self._topics.get(ctrl_name)

    def get_or_missing(self, ctrl_name: str) -> HelpTopic:
        """Return the topic for *ctrl_name*, or a generic placeholder."""
        topic = self._topics.get(ctrl_name)
        if topic is not None:
            return topic
        return HelpTopic(
            id=ctrl_name,
            title="No help available",
            body=(
                "No specific help is available for this control. "
                "Press Ctrl+Shift+F1 from your document to open the User Guide."
            ),
        )

    def all_ids(self) -> list[str]:
        return list(self._topics.keys())

    def generate_markdown(self) -> str:
        """Return a full Markdown control-reference document."""
        lines: list[str] = [
            "# QUILL Control Reference",
            "",
            "This document is auto-generated from `quill/core/help/topics.json`.",
            "Do not edit by hand.",
            "",
        ]
        for topic in sorted(self._topics.values(), key=lambda t: t.id):
            lines.append(topic.render(mode="doc"))
            lines.append("")
        return "\n".join(lines)


def load_topics(path: Path | None = None) -> dict[str, HelpTopic]:
    """Load and return topics from *path* (defaults to the bundled JSON)."""
    p = path or _TOPICS_PATH
    if not p.is_file():
        _log.warning("help: topics file not found at %s", p)
        return {}
    try:
        raw: Any = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        _log.error("help: failed to load topics: %s", exc)
        return {}
    if not isinstance(raw, list):
        _log.error("help: topics.json must be a JSON array")
        return {}
    topics: dict[str, HelpTopic] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        topic_id = str(entry.get("id", ""))
        if not topic_id:
            continue
        topics[topic_id] = HelpTopic(
            id=topic_id,
            title=str(entry.get("title", topic_id)),
            body=str(entry.get("body", "")),
            keystrokes=list(entry.get("keystrokes", [])),
            see_also=list(entry.get("see_also", [])),
            user_guide_section=str(entry.get("user_guide_section", "")),
            tokens=dict(entry.get("tokens", {})),
        )
    _log.debug("help: loaded %d topics", len(topics))
    return topics
