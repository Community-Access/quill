"""Registry API for the QUILL client.

``/api/v1/artifacts`` is the modern surface: every verified artifact of every
supported type, filterable with ``?type=``. The original ``/plugins``
endpoints remain as aliases so existing QUILL clients keep working.
"""

from flask import Blueprint, jsonify, request

from ..artifacts.registry import ARTIFACT_TYPES, get_type
from ..models.database import Artifact

plugins_bp = Blueprint("plugins_api", __name__)


def _artifact_json(artifact: Artifact) -> dict:
    return {
        "id": artifact.manifest_id,
        "type": artifact.artifact_type,
        "name": artifact.name,
        "version": artifact.version,
        "description": artifact.description,
        "download_url": artifact.download_url,
        "gold_standard": artifact.is_gold_standard,
    }


@plugins_bp.route("/types", methods=["GET"])
def get_types():
    """Every artifact type the Hub accepts, with storefront metadata."""
    return jsonify([
        {
            "id": artifact_type.id,
            "label": artifact_type.label,
            "plural": artifact_type.plural,
            "description": artifact_type.description,
            "upload_suffixes": list(artifact_type.upload_suffixes),
            "installs_into": artifact_type.installs_into,
        }
        for artifact_type in ARTIFACT_TYPES
    ])


@plugins_bp.route("/artifacts", methods=["GET"])
def get_artifacts():
    """All verified artifacts, optionally filtered by ``?type=``."""
    query = Artifact.query.filter_by(status="Verified")
    type_id = request.args.get("type")
    if type_id:
        if get_type(type_id) is None:
            return jsonify({"error": f"unknown artifact type '{type_id}'"}), 400
        query = query.filter_by(artifact_type=type_id)
    return jsonify([_artifact_json(artifact) for artifact in query.all()])


@plugins_bp.route("/artifacts/<manifest_id>/latest", methods=["GET"])
def get_latest_artifact(manifest_id):
    artifact = Artifact.query.filter_by(manifest_id=manifest_id, status="Verified").first()
    if not artifact:
        return jsonify({"error": "Artifact not found or not verified"}), 404
    return jsonify({
        "id": artifact.manifest_id,
        "type": artifact.artifact_type,
        "version": artifact.version,
        "download_url": artifact.download_url,
    })


# ---------------------------------------------------------------------------
# Back-compat aliases (original plugin-only API)
# ---------------------------------------------------------------------------


@plugins_bp.route("/plugins", methods=["GET"])
def get_plugins():
    """Legacy endpoint: verified Quillin extensions only."""
    plugins = Artifact.query.filter_by(status="Verified", artifact_type="quillin").all()
    return jsonify([_artifact_json(plugin) for plugin in plugins])


@plugins_bp.route("/plugins/<manifest_id>/latest", methods=["GET"])
def get_latest_plugin(manifest_id):
    return get_latest_artifact(manifest_id)
