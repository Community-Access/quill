"""BITS Accessible Forms on a WordPress site: its REST routes (wordpress.md 17a.7, 17a.8).

wx-free. Every request goes through the shared WordPress client
(:class:`quill.core.wordpress.api.WordPressApi`, whose one door is
``send_to_site``), signed with the site's saved application password, so
Forms adds no new host and no new way in: only BAF's own namespace, ``baf/v1``,
on a site the person already connected. A site whose REST index does not list
that namespace is never asked anything else (:func:`supports_baf`).

The routes (BAF ``includes/api/class-baf-rest-api.php``):

- ``GET /baf/v1/forms`` and ``GET /baf/v1/forms/{id}``: the forms, with each
  one's ``entry_count`` -- a count, never anybody's answers;
- ``POST /baf/v1/forms`` and ``POST /baf/v1/forms/{id}``: create and update;
- ``GET /baf/v1/entries?form_id=``: the responses, read only when the person
  opens Responses;
- ``DELETE /baf/v1/entries/{id}``: one response to BAF's Trash (no ``force``).

A form is sent as BAF stores it (``docs/form-model.md``, "How BAF stores the
model"): the model in ``config.form_model``, its BFL in ``bfl_source``, and
the model again as ``model``, the parameter :meth:`BAF_Form::set_model` takes.
On an update the rest of the site's ``config`` is kept, so the builder's own
fields are never wiped by a publish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from quill.core.forms import model as M
from quill.core.wordpress.api import WordPressApiError

NAMESPACE = "baf/v1"
#: Where a form is edited in BAF's own screens.
BUILDER_PAGE = "wp-admin/admin.php"


@dataclass(frozen=True)
class SiteForm:
    """A form on the site, as its list shows it."""

    id: int
    title: str
    status: str = "draft"
    entry_count: int = 0
    updated_at: str = ""
    slug: str = ""
    config: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)
    bfl_source: str = field(default="", compare=False, repr=False)

    @property
    def live(self) -> bool:
        return self.status == "active"

    def spoken(self) -> str:
        noun = "response" if self.entry_count == 1 else "responses"
        state = "" if self.live else f", {self.status}"
        return f"{self.title or 'Untitled form'}, {self.entry_count} {noun}{state}"

    def model(self) -> M.Model | None:
        """The model BAF stores for this form, when it has one."""
        found = self.config.get("form_model") if isinstance(self.config, dict) else None
        return found if isinstance(found, dict) else None

    def question_labels(self) -> dict[str, str]:
        """Field id -> its question, from the model, or the builder's fields."""
        model = self.model()
        if model is not None:
            return {k: v for k, v in M.labels(model).items() if v}
        out: dict[str, str] = {}
        for entry in self.config.get("fields") or [] if isinstance(self.config, dict) else []:
            if isinstance(entry, dict) and entry.get("id"):
                out[str(entry["id"])] = str(entry.get("label") or entry["id"])
        return out


def form_from_payload(raw: Any) -> SiteForm:
    data = raw if isinstance(raw, dict) else {}
    config = data.get("config")
    config = dict(config) if isinstance(config, dict) else {}
    # BAF's GET forms/{id} also returns the model on its own, beside config.
    if isinstance(data.get("model"), dict) and not isinstance(config.get("form_model"), dict):
        config["form_model"] = data["model"]
    return SiteForm(
        id=_int(data.get("id")),
        title=str(data.get("title") or ""),
        status=str(data.get("status") or "draft"),
        entry_count=_int(data.get("entry_count")),
        updated_at=str(data.get("updated_at") or ""),
        slug=str(data.get("slug") or ""),
        config=config,
        bfl_source=str(data.get("bfl_source") or ""),
    )


def supports_baf(api: Any) -> bool:
    """Whether the site's REST index lists BAF's namespace."""
    from quill.core.wordpress.site_features import read_index

    return read_index(api).supports(NAMESPACE)


def list_forms(api: Any) -> list[SiteForm]:
    """Every form on the site, newest first."""
    return [form_from_payload(raw) for raw in api.iter_collection(f"{NAMESPACE}/forms")]


def get_form(api: Any, form_id: int) -> SiteForm:
    return form_from_payload(api.get(f"{NAMESPACE}/forms/{int(form_id)}"))


def publish_body(
    model: M.Model, bfl: str, *, status: str, existing: SiteForm | None = None
) -> dict[str, Any]:
    """What Publish Form sends: the model, its BFL, and the site's own config kept."""
    config: dict[str, Any] = dict(existing.config) if existing is not None else {}
    config["form_model"] = model
    config["model_version"] = int(model.get("version") or M.MODEL_VERSION)
    return {
        "title": str(model.get("title") or "Untitled form"),
        "description": str(model.get("description") or ""),
        "status": status,
        "bfl_source": bfl,
        "config": config,
        "model": model,
    }


def create_form(api: Any, body: dict[str, Any]) -> SiteForm:
    return form_from_payload(api.post(f"{NAMESPACE}/forms", body))


def update_form(api: Any, form_id: int, body: dict[str, Any]) -> SiteForm:
    return form_from_payload(api.post(f"{NAMESPACE}/forms/{int(form_id)}", body))


# --------------------------------------------------------------------------- #
# responses (BAF calls them entries)


@dataclass(frozen=True)
class Response:
    id: int
    form_id: int
    created_at: str = ""
    answers: dict[str, Any] = field(default_factory=dict)
    is_read: bool = False
    is_starred: bool = False
    status: str = "active"


def response_from_payload(raw: Any) -> Response:
    data = raw if isinstance(raw, dict) else {}
    answers = data.get("fields")
    return Response(
        id=_int(data.get("id")),
        form_id=_int(data.get("form_id")),
        created_at=str(data.get("created_at") or ""),
        answers=answers if isinstance(answers, dict) else {},
        is_read=bool(_int(data.get("is_read"))),
        is_starred=bool(_int(data.get("is_starred"))),
        status=str(data.get("status") or "active"),
    )


def list_responses(api: Any, form_id: int) -> list[Response]:
    """Every response to one form, newest first. Personal data: only on request."""
    params = {"form_id": int(form_id), "orderby": "created_at", "order": "DESC"}
    return [response_from_payload(r) for r in api.iter_collection(f"{NAMESPACE}/entries", params)]


def delete_responses(api: Any, ids: list[int]) -> int:
    """Move each response to BAF's Trash; returns how many went."""
    gone = 0
    for response_id in ids:
        api.delete(f"{NAMESPACE}/entries/{int(response_id)}")
        gone += 1
    return gone


# --------------------------------------------------------------------------- #
# putting a form on a page


def block_markup(form_id: int) -> str:
    """BAF's form block, as block markup."""
    return f'<!-- wp:baf/form {{"formId":{int(form_id)}}} /-->'


def shortcode(form_id: int) -> str:
    """BAF's shortcode, for a page written in Markdown."""
    return f'[baf_form id="{int(form_id)}"]'


def placement(form_id: int, text_format: str) -> tuple[str, str]:
    """``(text to insert, what it is)`` for a page in *text_format*."""
    if text_format == "html":
        return "\n" + block_markup(form_id) + "\n", "a block"
    return "\n" + shortcode(form_id) + "\n", "a shortcode"


_SHOWS = r'(?:wp:baf/form\s*\{{[^}}]*"formId"\s*:\s*{id}\b|\[baf_form[^\]]*\bid\s*=\s*"?{id}\b)'


def shows_form(content: str, form_id: int) -> bool:
    """Whether a page's raw content places form *form_id*."""
    return re.search(_SHOWS.format(id=int(form_id)), content or "") is not None


def pages_showing(api: Any, form_id: int) -> list[tuple[str, str, str]]:
    """``(title, link, status)`` of each page or post that places the form."""
    found: list[tuple[str, str, str]] = []
    for kind in ("pages", "posts"):
        params = {
            "search": "baf",
            "context": "edit",
            "status": "publish,draft,private,future,pending",
            "_fields": "id,link,title,content,status",
        }
        try:
            rows = list(api.iter_collection(f"wp/v2/{kind}", params, max_pages=5))
        except WordPressApiError:
            continue  # an account that cannot list drafts still finds nothing here
        for raw in rows:
            content = raw.get("content")
            text = content.get("raw", "") if isinstance(content, dict) else str(content or "")
            if shows_form(str(text), form_id):
                title = raw.get("title")
                name = title.get("raw", "") if isinstance(title, dict) else str(title or "")
                found.append((str(name), str(raw.get("link") or ""), str(raw.get("status") or "")))
    found.sort(key=lambda row: row[2] != "publish")
    return found


def builder_url(site_url: str, form_id: int) -> str:
    """BAF's own editing screen for the form, in the site's dashboard."""
    query = urlencode({"page": "baf-form-builder", "form_id": int(form_id)})
    return f"{site_url.rstrip('/')}/{BUILDER_PAGE}?{query}"


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


__all__ = [
    "NAMESPACE",
    "Response",
    "SiteForm",
    "block_markup",
    "builder_url",
    "create_form",
    "delete_responses",
    "form_from_payload",
    "get_form",
    "list_forms",
    "list_responses",
    "pages_showing",
    "placement",
    "publish_body",
    "response_from_payload",
    "shortcode",
    "shows_form",
    "supports_baf",
    "update_form",
]
