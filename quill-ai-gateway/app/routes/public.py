"""The public landing page at ``/``.

The one page on this service that is not for an operator or a desktop client.
Somebody reaches it because they typed the address they were asked to connect
a computer to, because they followed a link, or because they want to know what
this thing is doing with their writing before they let it.

So it answers, in that order: what it is, what it does with your text, what it
has cost, and how to get it. The numbers are there because a free service run on
somebody else's money should be able to say how much of it -- and because
"a fraction of a cent per answer" is the whole reason it can be free, which is
more convincing shown than asserted.

What it does **not** show is how much budget is left. See
``app/public_stats.py`` for why: headroom tells anybody who would like the
service switched off for everybody else exactly how hard to push.

No authentication, no cookies, no JavaScript, and no request to the database
that is not cached -- a page anyone can load must not be a way to make the
service work.
"""

from __future__ import annotations

from flask import Blueprint, current_app, render_template

from app.public_stats import gather

bp = Blueprint("public", __name__)


@bp.get("/")
def landing():
    return render_template(
        "public/landing.html",
        stats=gather(current_app),
        connect_url=f"{current_app.config['PUBLIC_BASE_URL'].rstrip('/')}/connect",
    )
