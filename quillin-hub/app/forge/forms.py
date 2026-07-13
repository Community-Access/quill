"""The Submission Forge.

Drop any shareable QUILL artifact on the Forge and it figures out the rest:
detects the type, runs the exact validation QUILL itself uses, scans any code
for security honesty, reads the artifact's own metadata, and hands back an
accessible report with the next step -- a guided GitHub pull request in the
GitHub-Native model.
"""

import json
import logging
import os
import shutil
import uuid
import zipfile
from urllib.parse import quote

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .. import db, limiter
from ..artifacts.registry import ARTIFACT_TYPES, accepted_suffixes, get_type
from ..models.database import Submission
from .linter import audit_submission

forge_bp = Blueprint("forge", __name__, template_folder="templates")
logger = logging.getLogger(__name__)

_REPO = "Community-Access/quill"
_MAX_UPLOAD_BYTES = 32 * 1024 * 1024
_MAX_UPLOAD_ENTRIES = 2000


def _allowed_upload(filename: str) -> bool:
    lowered = filename.lower()
    return any(lowered.endswith(suffix) for suffix in accepted_suffixes())


def _prepare_upload(file_storage, signature_storage=None) -> tuple[str, str, str | None]:
    """Save the upload (and an optional sidecar) and return (audit_path, saved_path, sidecar_path).

    Quillin ZIPs are extracted so the linter and security scan see real files;
    every other type is audited as the single file it is (.qsp stays zipped --
    the sound-pack loader reads ZIPs natively). If a signature sidecar is
    uploaded (``<artifact>.minisig``), it is saved next to the artifact so
    the linter can verify the signature.
    """
    filename = secure_filename(file_storage.filename or "artifact")
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], uuid.uuid4().hex)
    os.makedirs(upload_dir, exist_ok=True)
    saved_path = os.path.join(upload_dir, filename)
    file_storage.save(saved_path)

    sidecar_path: str | None = None
    if signature_storage is not None and signature_storage.filename:
        sidecar_name = secure_filename(signature_storage.filename)
        sidecar_path = os.path.join(upload_dir, sidecar_name)
        signature_storage.save(sidecar_path)

    if filename.lower().endswith(".zip"):
        extract_dir = os.path.join(upload_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(saved_path) as archive:
            infolist = archive.infolist()
            if len(infolist) > _MAX_UPLOAD_ENTRIES:
                raise ValueError(f"archive has more than {_MAX_UPLOAD_ENTRIES} entries")
            total = sum(info.file_size for info in infolist)
            if total > _MAX_UPLOAD_BYTES:
                raise ValueError("archive expands beyond the 32 MB submission limit")
            archive.extractall(extract_dir)
        return (extract_dir, saved_path, sidecar_path)

    return (saved_path, saved_path, sidecar_path)


def _github_links(metadata: dict, artifact_type_id: str | None) -> dict[str, str]:
    """Prefilled GitHub links for the GitHub-Native submission path."""
    name = str(metadata.get("name") or metadata.get("id") or "my artifact")
    type_label = artifact_type_id or "artifact"
    title = quote(f"[Hub submission] {type_label}: {name}")
    body = quote(
        "## Quillin Hub submission\n\n"
        f"- Type: {type_label}\n"
        f"- Name: {name}\n"
        f"- Version: {metadata.get('version', 'n/a')}\n\n"
        "The Forge report is attached below. I attest to the Quillin Author Covenant.\n"
    )
    return {
        "pull_request": f"https://github.com/{_REPO}/compare",
        "issue": f"https://github.com/{_REPO}/issues/new?title={title}&body={body}",
        "covenant": f"https://github.com/{_REPO}/blob/main/docs/quillins/quillin-code-of-conduct.md",
    }


@forge_bp.route("/")
def index():
    """Entrance to the Submission Forge: what can you share?"""
    return render_template("forge_index.html", artifact_types=ARTIFACT_TYPES)


@forge_bp.route("/submit", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def submit():
    if request.method == "GET":
        return render_template(
            "submit_form.html",
            artifact_types=ARTIFACT_TYPES,
            accept=",".join(accepted_suffixes()),
            preselected=request.args.get("type", ""),
        )

    upload = request.files.get("artifact")
    if upload is None or not upload.filename:
        return render_template(
            "submit_form.html",
            artifact_types=ARTIFACT_TYPES,
            accept=",".join(accepted_suffixes()),
            preselected=request.form.get("artifact_type", ""),
            error="Choose a file to submit.",
        ), 400

    if not _allowed_upload(upload.filename):
        return render_template(
            "submit_form.html",
            artifact_types=ARTIFACT_TYPES,
            accept=",".join(accepted_suffixes()),
            preselected=request.form.get("artifact_type", ""),
            error=(
                "That file type is not a QUILL artifact. Accepted: "
                + ", ".join(accepted_suffixes())
            ),
        ), 400

    requested_type = request.form.get("artifact_type") or None
    if requested_type and get_type(requested_type) is None:
        requested_type = None

    try:
        signature = request.files.get("signature")
        audit_path, _saved_path, sidecar_path = _prepare_upload(upload, signature)
    except (ValueError, zipfile.BadZipFile, OSError) as exc:
        return render_template(
            "submit_form.html",
            artifact_types=ARTIFACT_TYPES,
            accept=",".join(accepted_suffixes()),
            preselected=requested_type or "",
            error=f"Could not read the upload: {exc}",
        ), 400

    upload_dir = os.path.dirname(_saved_path)
    try:
        try:
            results = audit_submission(
                audit_path,
                requested_type,
                sidecar_path=sidecar_path,
                sign_target=_saved_path,
            )
        except Exception:  # noqa: BLE001 - never let a scanner bug crash the Forge
            logger.exception("audit_submission failed for %s", upload.filename)
            return render_template(
                "submit_form.html",
                artifact_types=ARTIFACT_TYPES,
                accept=",".join(accepted_suffixes()),
                preselected=requested_type or "",
                error="The audit could not complete. Please try again or contact a maintainer.",
            ), 500

        submission = Submission(
            artifact_type=results.get("artifact_type"),
            original_filename=secure_filename(upload.filename),
            extracted=results.get("metadata") or {},
            lint_report=json.loads(json.dumps(results["reports"], default=str)),
            status="Passed" if results["status"] == "PASS" else "Failed",
        )
        db.session.add(submission)
        db.session.commit()

        hub_type = get_type(results.get("artifact_type") or "")
        return render_template(
            "forge_report.html",
            results=results,
            hub_type=hub_type,
            submission=submission,
            github=_github_links(results.get("metadata") or {}, results.get("artifact_type")),
        )
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)


@forge_bp.route("/legacy-submit", methods=["POST"])
def legacy_submit():
    """Old bookmark support: the pre-2.0 Forge posted here."""
    return redirect(url_for("forge.submit"))
