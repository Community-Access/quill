from datetime import datetime

# This is usually initialized in __init__.py using db.init_app(app)
# but we import the db instance to define models.
from .. import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default="User")  # Admin, Author, User
    reputation_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Artifact(db.Model):
    """One published QUILL artifact of any supported type.

    ``artifact_type`` matches an id in ``app.artifacts.registry`` (quillin,
    agent, verbosity-pack, sound-pack, keyboard-pack, skill-pack,
    pronunciation-dictionary).
    """

    __tablename__ = "artifacts"
    id = db.Column(db.Integer, primary_key=True)
    manifest_id = db.Column(db.String(128), unique=True, nullable=False)
    artifact_type = db.Column(db.String(32), nullable=False, default="quillin", index=True)
    version = db.Column(db.String(32), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    download_url = db.Column(db.String(512))
    status = db.Column(db.String(20), default="Pending")  # Pending, Verified, Rejected
    is_gold_standard = db.Column(db.Boolean, default=False)
    signer_key_id = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Back-compat alias: early Hub code (and its callers) knew only about plugins.
Plugin = Artifact


class Submission(db.Model):
    __tablename__ = "submissions"
    id = db.Column(db.Integer, primary_key=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"), nullable=True)
    submitter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    artifact_type = db.Column(db.String(32))
    original_filename = db.Column(db.String(256))
    # Metadata the Forge extracted from the upload (name, version, description).
    extracted = db.Column(db.JSON)
    lint_report = db.Column(db.JSON)
    status = db.Column(db.String(20), default="Received")  # Received, Passed, Failed
    review_notes = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class Interaction(db.Model):
    __tablename__ = "interactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    type = db.Column(db.String(20))  # Upvote, Downvote, Comment
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
