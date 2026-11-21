"""Tests 151 to 154 of the live WordPress run: QAF's spam checks, the BAF move, and PMPro at size.

Loaded by ``docs/qa/wordpress-live-run.py`` (``_load_workbench_checks``), which
passes itself to :func:`register`:

- 151, QUILL Accessible Forms' spam checks against real submissions from the
  form's own page: a person's answers kept, the honeypot held with its reason,
  a form sent too fast and one with too many links asked a question, Not Spam
  and Spam through the Workbench, and a spam setting changed and put back
  (``workbench_qaf_spam``, ``workbench_qaf_spam_edit``, ``workbench_forms``);
- 152, what came across when BITS Accessible Forms became QAF: BAF's forms
  and entries under ``qaf/v1``, the old ``baf/v1`` still answering reads, a
  page written with BAF's block and shortcode still showing the form, and the
  Workbench's Forms node listing them;
- 153, PMPro's discount codes past one page: 30 codes made through New
  Discount Code; PMPro 3.9.2 lists codes only through its quick search, at
  most 20 with no paging, so the node lists 20 and says the rest are in wp-admin;
- 154, Members of This Level on a site of more than 200 people, timed.

153 and 154 make what ``pmpro/v1`` and ``wp/v2`` cannot take away again (PMPro
has no route that deletes a code, and 250 throwaway people are quicker made
and removed by the site itself), so they need the site's shell: set
``QUILL_LIVE_SITE_SHELL`` to the command that runs wp-cli there, for example
``ssh lp.csedesigns.com app/wordpress-test/wpcli.sh``. Without it they are
"not run". Everything made is named "QUILL live test" (codes ``QLTPAGE``,
people ``quill-live-test-``) and deleted afterwards. The people have no
password anyone knows and no way to sign in that anyone holds.

QAF counts five sends an hour from one address to one form, so 151 makes its
own form and sends four.
"""

from __future__ import annotations

import os
import posixpath
import re
import shlex
import subprocess
import time
from typing import Any

#: The harness module, set by :func:`register`.
H: Any = None

AREA = "Workbench, plugins and WordPress.org (10B.3)"
SHELL_ENV = "QUILL_LIVE_SITE_SHELL"
CODE_PREFIX = "QLTPAGE"
PEOPLE_PREFIX = "quill-live-test-"
CODES = 30
PEOPLE = 250
MEMBERS = 60


def register(harness: Any) -> None:
    """Put tests 151 to 154 on the harness's list."""
    global H
    H = harness
    for ref, name, fn, who, writes in _TESTS:
        harness.check(AREA, ref, name, who=getattr(harness, who), writes=writes)(fn)


def _site_ctx(ctx: Any) -> Any:
    from quill.core.wordpress.site import load_account, load_site_info
    from quill.core.wordpress.workbench_load import SiteContext

    api = ctx.api(H.ADMIN)
    key = f"wb_info_{H.ADMIN}"
    if key not in ctx.state:
        ctx.state[key] = load_site_info(api)
    if H.ADMIN not in ctx.accounts:
        ctx.accounts[H.ADMIN] = load_account(api)
    return SiteContext(
        H.SITE_NAME, api, url=H.SITE_URL, account=ctx.accounts[H.ADMIN], info=ctx.state[key]
    )


def _need_qaf(ctx: Any) -> str:
    namespace = H.forms_namespace(ctx.api(H.ADMIN))
    if namespace != "qaf/v1":
        raise H.NotRun(f"skipped: the site's forms plugin is {namespace or 'missing'}, not QAF")
    return namespace


# =========================================================================== #
# 151: spam


_SPAM_FORM = """\
form "{title}"
  text #name "Your name"
    @required
  email #email "Your email"
    @required
  textarea #message "Your message"
"""


def _page_fields(link: str) -> dict[str, str]:
    """The hidden fields the form's page gives a visitor: token, start time, signature."""
    _status, _headers, body = H.fetch(link)
    html = body.decode("utf-8", "replace")
    found = {}
    for name in ("_qaf_token", "_qaf_form_loaded", "_qaf_form_sig"):
        match = re.search(rf'name="{name}" value="([^"]*)"', html)
        H.expect(match, f"the page has no {name}")
        found[name] = match.group(1)
    return found


def _spam(ctx: Any) -> str:
    from quill.core.forms import bfl_document as bd
    from quill.core.wordpress import workbench_qaf_spam as qs
    from quill.core.wordpress import workbench_qaf_spam_edit as qe
    from quill.core.wordpress.workbench_forms import load_forms, set_entry_spam

    namespace = _need_qaf(ctx)
    fs = H.forms_site()
    api = ctx.api(H.ADMIN)
    site = _site_ctx(ctx)
    state = qs.read_spam_state(site, namespace)
    H.expect(state, "qaf/v1/spam did not answer")
    text = qs.spam_state_text(state)
    H.expect("Honeypot: on and running" in text, f"the Spam page says: {H.cell(text, 200)}")
    source = _SPAM_FORM.format(title=ctx.title("spam checks"))
    model = bd.read_form(source)
    form = fs.create_form(api, fs.publish_body(model, source, status="active"))
    ctx.later(f"delete form {form.id}", lambda: api.delete(f"{namespace}/forms/{form.id}"))
    block, _what = fs.placement(form.id, "html", "qaf")
    page = api.post(
        "wp/v2/pages", {"title": ctx.title("spam page"), "status": "publish", "content": block}
    )
    ctx.later(
        f"delete page {page['id']}", lambda: api.delete(f"wp/v2/pages/{page['id']}", force=True)
    )

    def send(n: int, message: str, extra: dict[str, str]) -> dict[str, Any]:
        answers = {
            "name": f"{H.TAG} {n}",
            "email": f"quill-live-{n}@example.invalid",
            "message": message,
        }
        return ctx.anon.post(
            f"{namespace}/submit/{form.id}", {"fields": answers, **answers, **extra}
        )

    person = _page_fields(page["link"])
    time.sleep(4)  # longer than the site's shortest time to fill
    kept = send(1, "A question from a person.", person)
    H.expect(kept.get("success") and kept.get("entry_id"), f"a person's answers: {kept}")
    bot = send(2, "Hello", {**_page_fields(page["link"]), "qaf_website": "http://spam.example"})
    H.expect(bot.get("success"), f"the honeypot told the sender: {bot}")  # held, never refused
    fast = send(3, "Hello", _page_fields(page["link"]))
    asked_fast = (fast.get("challenge") or {}).get("question")
    if fast.get("entry_id"):  # say what QAF made of it
        fast["spam"] = api.get(f"{namespace}/entries/{fast['entry_id']}").get("spam")
    H.expect(not fast.get("success") and asked_fast, f"sent at once: {fast}")
    links = " ".join(f"https://{c}.example/" for c in "abcd")
    linky = send(4, f"See {links}", {})
    asked_links = (linky.get("challenge") or {}).get("question")
    H.expect(not linky.get("success") and asked_links, f"four links: {linky}")

    entries = {e.id: e for e in fs.list_responses(api, form.id)}
    mine = entries.get(int(kept["entry_id"]))
    H.expect(mine is not None and mine.status == "active", "the person's entry is not kept")
    # Responses lists what was received; the held one is under Held as Spam, below.
    H.expect(len(entries) == 1, f"{len(entries)} responses: a question asked must save nothing")
    held = [r for r in load_forms(site, "spam") if r.key == str(bot["entry_id"])]
    H.expect(held, "the honeypot's entry is not under Held as Spam")
    reason = qs.held_reason(held[0].raw)
    H.expect("qaf_website" in reason and "honeypot" in reason, f"reason: {reason}")
    H.expect(reason in held[0].detail, "the row does not say why it was held")
    H.expect(not set_entry_spam(site, held, False), "Not Spam failed")
    released = api.get(f"{namespace}/entries/{bot['entry_id']}")
    H.expect(released.get("status") == "active", f"Not Spam left it {released.get('status')}")
    again = [r for r in load_forms(site, "entries") if r.key == str(bot["entry_id"])]
    H.expect(not set_entry_spam(site, again, True), "Spam failed")
    H.expect(api.get(f"{namespace}/entries/{bot['entry_id']}").get("status") == "spam", "not held")

    limits = state.get("limits") or {}
    was = int(limits.get("max_links", 3))
    revision = str(state.get("revision", ""))
    said, after = qe.save_spam_settings(api, namespace, revision, {"max_links": was + 1})
    H.expect("read them back" in said, said)
    ctx.later(
        "put back the link limit",
        lambda: qe.save_spam_settings(
            api, namespace, str(after.get("revision", "")), {"max_links": was}
        ),
    )
    try:  # the copy read before the change is stale now
        qe.save_spam_settings(api, namespace, revision, {"max_links": was})
        stale = False
    except qe.SpamConflict:
        stale = True
    H.expect(stale, "a stale settings change was sent")
    return (
        f"form {form.id}: a person's answers kept (entry {kept['entry_id']}); the honeypot held "
        f"({H.cell(reason, 70)}); sent at once, asked {asked_fast!r}; four links, asked "
        f"{asked_links!r}; Not Spam and Spam; link limit {was} to {was + 1}, a stale change "
        "refused, put back"
    )


# =========================================================================== #
# 152: from BAF to QAF


def _baf_moved(ctx: Any) -> str:
    from quill.core.forms import qaf_site
    from quill.core.wordpress.workbench_forms import load_forms

    namespace = _need_qaf(ctx)
    api = ctx.api(H.ADMIN)
    names = set(ctx.index.namespaces)
    H.expect("baf/v1" in names, "baf/v1 is gone: QAF keeps it for reading for one release")
    forms = list(api.iter_collection(f"{namespace}/forms"))
    # QAF numbered on from BAF: the forms BAF made are the ones older than QAF's arrival.
    old = [f for f in forms if str(f.get("created_at", "")) < "2026-11-20"]
    if not old:
        raise H.NotRun("no form from before QAF arrived is left on the site")
    form = qaf_site.form_from_payload(old[-1])
    entries = []
    for status in ("active", "spam", "trash"):  # QAF takes one status at a time
        params = {"form_id": form.id, "status": status}
        entries += list(api.iter_collection(f"{namespace}/entries", params))
    by_status: dict[str, int] = {}
    for raw in entries:
        by_status[str(raw.get("status"))] = by_status.get(str(raw.get("status")), 0) + 1
    H.expect(entries, f"BAF's form {form.id} has no entries under QAF")
    legacy = api.get(f"baf/v1/forms/{form.id}")
    H.expect(str(legacy.get("id")) == str(form.id), "baf/v1 does not read the same form")
    content = (
        f'<!-- wp:baf/form {{"formId":{form.id}}} /-->\n'
        f'<!-- wp:shortcode -->[baf_form id="{form.id}"]<!-- /wp:shortcode -->'
    )
    page = api.post(
        "wp/v2/pages", {"title": ctx.title("BAF page"), "status": "publish", "content": content}
    )
    ctx.later(
        f"delete page {page['id']}", lambda: api.delete(f"wp/v2/pages/{page['id']}", force=True)
    )
    _status, _h, body = H.fetch(page["link"])
    shown = body.decode("utf-8", "replace").count("<form")
    H.expect(shown >= 2, f"BAF's block and shortcode show {shown} forms")
    H.expect(any(link == page["link"] for _t, link, _s in qaf_site.pages_showing(api, form.id)),
             "QUILL does not find the page written with BAF's names")  # fmt: skip
    rows = [r for r in load_forms(_site_ctx(ctx), "all") if r.key == str(form.id)]
    H.expect(rows and rows[0].subkind == "qaf", "the Forms node does not list BAF's form")
    counts = ", ".join(f"{n} {s}" for s, n in sorted(by_status.items()))
    made_on = str(old[-1].get("created_at"))[:10]
    return (
        f"BAF's form {form.id} ({H.cell(form.title, 50)}, made {made_on}) "
        f"is QAF's: {counts} entries; baf/v1 reads it; BAF's block and shortcode on a page show "
        f"it ({shown} forms) and QUILL finds that page; the Forms node lists it"
    )


# =========================================================================== #
# 153, 154: PMPro at size, with the site's shell


def _shell() -> list[str]:
    command = os.environ.get(SHELL_ENV, "").strip()
    if not command:
        raise H.NotRun(f"needs the site's shell ({SHELL_ENV}) to delete what it makes")
    return shlex.split(command)


def _php(code: str) -> str:
    """Run *code* on the site with wp-cli's eval-file; its output.

    The code goes over as a file, not as words on a command line: Git's ssh on
    Windows strips the quotes the far shell would need around PHP. The test
    site's ``wpcli.sh`` mounts its folder read-only at ``/host``, so the file is
    put there over ssh and removed afterwards.
    """
    shell = _shell()
    if len(shell) < 3 or os.path.basename(shell[0]).lower().removesuffix(".exe") != "ssh":
        raise H.NotRun(f"{SHELL_ENV} must be 'ssh <host> <path to wpcli.sh>'")
    ssh, script = shell[:-1], shell[-1]
    folder = posixpath.dirname(script)
    name = f"quill-live-{os.getpid()}.php"
    remote = posixpath.join(folder, name)

    def run(args: list[str], given: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args, input=given, capture_output=True, text=True, timeout=900, check=False
        )

    sent = run([*ssh, f"cat > {remote}"], "<?php " + code)
    if sent.returncode != 0:
        raise H.CheckFailed(f"ssh: {H.cell(sent.stderr, 200)}")
    try:
        done = run([*ssh, f"{script} eval-file /host/{name}"])
    finally:
        run([*ssh, f"rm -f {remote}"])
    if done.returncode != 0:
        raise H.CheckFailed(f"wp-cli: {H.cell(done.stderr or done.stdout, 200)}")
    return done.stdout.strip()


_DROP_CODES = f"""
global $wpdb;
$ids = $wpdb->get_col("SELECT id FROM {{$wpdb->pmpro_discount_codes}}
  WHERE code LIKE '{CODE_PREFIX}%'");
foreach ($ids as $id) {{
  $wpdb->delete($wpdb->pmpro_discount_codes_levels, array('code_id' => $id));
  $wpdb->delete($wpdb->pmpro_discount_codes, array('id' => $id));
}}
echo count($ids);
"""


def _codes(ctx: Any) -> str:
    """New Discount Code past PMPro's 20, and what the Discount Codes node then says.

    PMPro 3.9.2 lists codes only through its quick search, 20 at most and with
    no paging (there is no discount-codes ability), so the node lists 20 and
    a row saying the rest are in wp-admin; Look Up still reads any code.
    """
    from quill.core.wordpress import workbench_pmpro_rest as pr

    _shell()
    if ctx.index is None or pr.PMPRO_NAMESPACE not in set(ctx.index.namespaces):
        raise H.NotRun("skipped: Paid Memberships Pro not installed")
    api = ctx.api(H.ADMIN)
    site = _site_ctx(ctx)
    levels = api.get("pmpro/v1/membership_levels")
    level = int(next(iter(levels.values() if isinstance(levels, dict) else levels))["id"])
    ctx.later("delete the QLTPAGE codes", lambda: _php(_DROP_CODES))
    preview = pr.discount_preview(
        pr.DiscountSpec(f"{CODE_PREFIX}001", (level,), uses=1), H.SITE_NAME, {}
    )
    for n in range(1, CODES + 1):
        pr.create_discount_code(api, pr.DiscountSpec(f"{CODE_PREFIX}{n:03d}", (level,), uses=1))
    last = pr.read_discount_code(api, f"{CODE_PREFIX}{CODES:03d}")
    H.expect(str(last.get("uses")) == "1", f"Look Up: {last}")
    started = time.monotonic()
    rows = pr.load_discount_codes(site)
    took = time.monotonic() - started
    codes = [r.cell("code") for r in rows if r.kind == "pmpro"]
    H.expect(len(set(codes)) == len(codes), "a code was listed twice")
    note = [r for r in rows if r.kind == "discount_note"]
    if len(codes) >= 20:
        H.expect(note and "more discount codes" in note[0].detail, f"rows: {len(rows)}, no note")
    gone = int(_php(_DROP_CODES) or 0)
    H.expect(gone == CODES, f"{gone} codes deleted")
    said = H.cell(note[0].detail, 120) if note else "no note"
    return (
        f"{CODES} codes made through New Discount Code ({H.cell(preview[0], 50)}); the node "
        f"lists {len(codes)} in {took:.1f} s, each once, then: {said}; Look Up read "
        f"{last.get('code')}; deleted on the site"
    )


_SEED_PEOPLE = f"""
$level = (int) $args_level;
$made = 0;
for ($n = 1; $n <= {PEOPLE}; $n++) {{
  $login = sprintf('{PEOPLE_PREFIX}%03d', $n);
  if (username_exists($login)) continue;
  $id = wp_insert_user(array('user_login' => $login, 'user_email' => $login . '@example.invalid',
    'user_pass' => wp_generate_password(32), 'display_name' => 'QUILL live test ' . $n,
    'role' => 'subscriber'));
  if (is_wp_error($id)) continue;
  if ($n <= {MEMBERS}) pmpro_changeMembershipLevel($level, $id);
  $made++;
}}
echo $made;
"""

_DROP_PEOPLE = f"""
require_once ABSPATH . 'wp-admin/includes/user.php';
$gone = 0;
foreach (get_users(array('search' => '{PEOPLE_PREFIX}*', 'search_columns' => array('user_login'),
  'fields' => 'ID')) as $id) {{
  if (function_exists('pmpro_changeMembershipLevel')) pmpro_changeMembershipLevel(0, $id);
  wp_delete_user($id);
  $gone++;
}}
echo $gone;
"""


def _members_at_size(ctx: Any) -> str:
    from quill.core.wordpress import workbench_pmpro_members as pm
    from quill.core.wordpress import workbench_pmpro_rest as pr

    _shell()
    if ctx.index is None or pr.PMPRO_NAMESPACE not in set(ctx.index.namespaces):
        raise H.NotRun("skipped: Paid Memberships Pro not installed")
    api = ctx.api(H.ADMIN)
    levels = api.get("pmpro/v1/membership_levels")
    levels = list(levels.values()) if isinstance(levels, dict) else list(levels or [])
    level = levels[0]
    before = pm.find_members(api, int(level["id"]), str(level["name"]), H.SITE_NAME)
    ctx.later("delete the throwaway people", lambda: _php(_DROP_PEOPLE))
    made = int(_php(f"$args_level = {int(level['id'])};" + _SEED_PEOPLE) or 0)
    H.expect(made == PEOPLE, f"{made} of {PEOPLE} people made")
    people = pm.count_people(api)
    asked = pm.ask_words(str(level["name"]), H.SITE_NAME, people)
    H.expect(people is not None and people >= pm.SLOW_FROM, f"{people} people")
    H.expect("slow" in asked.lower() or "minute" in asked.lower(), f"the question: {asked}")
    started = time.monotonic()
    found = pm.find_members(api, int(level["id"]), str(level["name"]), H.SITE_NAME, people=people)
    took = time.monotonic() - started
    H.expect(found.checked == people, f"asked about {found.checked} of {people}")
    H.expect(len(found.members) == len(before.members) + MEMBERS,
             f"{len(found.members)} members, {len(before.members)} before")  # fmt: skip
    import threading

    stop = threading.Event()
    seen: list[int] = []

    def progress(checked: int, _members: int) -> None:
        seen.append(checked)
        if checked >= 40:
            stop.set()

    part = pm.find_members(
        api, int(level["id"]), str(level["name"]), H.SITE_NAME, people=people, stop=stop,
        progress=progress,
    )  # fmt: skip
    H.expect(part.stopped and part.checked < people, f"Stop: {part.sentence()}")
    gone = int(_php(_DROP_PEOPLE) or 0)
    H.expect(gone == PEOPLE, f"{gone} people deleted")
    return (
        f"{people} people; asked first: {H.cell(asked, 90)} Read in {took:.0f} s "
        f"({took / max(1, people) * 1000:.0f} ms a person): {H.cell(found.sentence(), 80)} "
        f"Stopped at {part.checked}: {H.cell(part.sentence(), 70)} The {PEOPLE} people deleted."
    )


_TESTS: tuple[tuple[str, str, Any, str, bool], ...] = (
    ("151", "QAF spam: real submissions held, asked, released", _spam, "ADMIN", True),
    ("152", "QAF: BAF's forms, entries and pages came across", _baf_moved, "ADMIN", True),
    ("153", "Paid Memberships Pro: discount codes past one page", _codes, "ADMIN", True),
    (
        "154",
        "Paid Memberships Pro: Members of This Level at 260 people",
        _members_at_size,
        "ADMIN",
        True,
    ),
)
