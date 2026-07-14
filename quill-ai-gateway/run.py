"""Local development entry point.

Production deployment does **not** use this file's ``app.run()`` — use a
real WSGI server (Gunicorn is what ``quillin-hub`` already runs on this
host; see README.md's deployment section for the exact command). This
file exists for `flask run` / local debugging only, and for local dev
convenience loads a ``.env`` file via ``python-dotenv`` — a mechanism
deliberately **not** present in ``app/config.py`` itself, so a forgotten
``.env`` file can never accidentally get read in a production process
that doesn't expect it.
"""

from __future__ import annotations

import os

if os.environ.get("FLASK_ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()  # loads .env from the current directory, if present

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
