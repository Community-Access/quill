from flask import Blueprint, render_template, request

from ..artifacts.registry import ARTIFACT_TYPES, get_type
from ..models.database import Artifact, Interaction

web_bp = Blueprint("web", __name__, template_folder="templates")


def _verified(type_id: str | None = None):
    query = Artifact.query.filter_by(status="Verified")
    if type_id and get_type(type_id):
        query = query.filter_by(artifact_type=type_id)
    return query.all()


@web_bp.route("/")
def index():
    """
    Accessible Storefront Home.
    Features: search, artifact-type sections, featured (Gold Standard) artifacts.
    """
    search_query = request.args.get("q", "").strip()
    type_filter = request.args.get("type", "").strip() or None
    artifacts = _verified(type_filter)

    if search_query:
        lowered = search_query.lower()
        artifacts = [
            artifact
            for artifact in artifacts
            if lowered in artifact.name.lower() or lowered in (artifact.description or "").lower()
        ]

    featured = [artifact for artifact in artifacts if artifact.is_gold_standard]
    others = [artifact for artifact in artifacts if not artifact.is_gold_standard]

    return render_template(
        "index.html",
        artifacts=featured + others,
        artifact_types=ARTIFACT_TYPES,
        active_type=get_type(type_filter) if type_filter else None,
        query=search_query,
    )


@web_bp.route("/artifact/<int:artifact_id>")
@web_bp.route("/plugin/<int:artifact_id>")  # legacy bookmarks
def artifact_detail(artifact_id):
    """Deep-dive artifact page with reviews."""
    artifact = Artifact.query.get_or_404(artifact_id)
    reviews = Interaction.query.filter_by(artifact_id=artifact_id, type="Comment").all()
    return render_template(
        "plugin.html",
        artifact=artifact,
        hub_type=get_type(artifact.artifact_type),
        reviews=reviews,
    )


@web_bp.route("/search")
def search():
    """Dedicated search results page for accessibility navigation."""
    q = request.args.get("q", "")
    type_filter = request.args.get("type", "").strip() or None
    query = Artifact.query.filter(
        Artifact.name.contains(q) | Artifact.description.contains(q)
    ).filter_by(status="Verified")
    if type_filter and get_type(type_filter):
        query = query.filter_by(artifact_type=type_filter)
    return render_template(
        "search.html",
        artifacts=query.all(),
        artifact_types=ARTIFACT_TYPES,
        active_type=get_type(type_filter) if type_filter else None,
        query=q,
    )
