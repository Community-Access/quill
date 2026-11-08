"""The Command Key's safety rules, as properties (docs/design/command-key.md 14.3).

Generated over random enabled sets, random availability changes between asking
and running, random confirmation answers and random sentences -- some drawn
from the catalogue's own words, some nonsense -- in QUILL, QUILL Lite and Radio:

- nothing outside the candidate list ever runs;
- no NEVER command ever runs;
- every CONFIRM command asks before it runs, every time;
- a command unavailable at run time never runs;
- every sentence ends in a run, a question, a list, a refusal or nothing --
  never an exception;
- every word spoken is one of the app's own sentences, at most twelve words.
"""

from __future__ import annotations

import pytest
from command_key_fakes import FakeHost, FakeRegistry
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from quill.core.command_catalogue import Risk, rows_for_app
from quill.core.command_catalogue.policy import CommandKeySession

_APPS = ("quill", "lite", "radio")
_ROWS = {app: rows_for_app(app) for app in _APPS}
_WORDS = sorted({
    word
    for rows in _ROWS.values()
    for spec in rows
    for phrase in spec.words()
    for word in phrase.split()
})
_PHRASES = sorted({phrase for rows in _ROWS.values() for spec in rows for phrase in spec.words()})
_EXTRA = ["delete", "send", "a lot", "a bit", "3", "thirty seconds", "please", "undo that", "again"]

_sentences = st.one_of(
    st.sampled_from(_PHRASES),
    st.lists(st.sampled_from(_WORDS + _EXTRA), min_size=1, max_size=6).map(" ".join),
    st.text(max_size=30),
)


@st.composite
def _worlds(draw: st.DrawFn) -> tuple[FakeHost, set[str], set[str]]:
    app = draw(st.sampled_from(_APPS))
    rows = _ROWS[app]
    ids = sorted(spec.id for spec in rows)
    registered = set(draw(st.lists(st.sampled_from(ids), unique=True, max_size=len(ids))))
    disabled = set(draw(st.lists(st.sampled_from(ids), unique=True, max_size=8)))
    vanish = set(draw(st.lists(st.sampled_from(ids), unique=True, max_size=4)))
    registry = FakeRegistry(ids=set(registered), reasons={i: "Not now." for i in disabled})
    host = FakeHost(
        app,
        registry,
        rows,
        confirm_answer=draw(st.booleans()),
        choose_index=draw(st.sampled_from([None, 0, 1, 2])),
        help_pick=draw(st.sampled_from([None, *ids])),
    )
    return host, disabled, vanish


_SETTINGS = settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@pytest.mark.timeout(180)
@_SETTINGS
@given(world=_worlds(), sentences=st.lists(_sentences, min_size=1, max_size=4))
def test_the_safety_rules_hold_for_any_sentence(
    world: tuple[FakeHost, set[str], set[str]], sentences: list[str]
) -> None:
    host, disabled, vanish = world
    rows = {spec.id: spec for spec in host.rows}
    offered_at_start = {item.spec.id for item in host.candidates()}

    asked_before_run: list[str] = []
    original_confirm = host.confirm

    def confirm(question: str) -> bool:
        asked_before_run.append(question)
        # The world changes while the person is deciding.
        for command_id in vanish:
            host.registry.reasons[command_id] = "It went away."
        return original_confirm(question)

    host.confirm = confirm  # type: ignore[method-assign]
    session = CommandKeySession(host)
    for text in sentences:
        before = len(host.registry.ran)
        questions_before = len(asked_before_run)
        session.submit(text)
        for command_id in host.registry.ran[before:]:
            spec = rows[command_id]
            # Nothing outside what was offered; nothing NEVER; nothing disabled.
            assert command_id in offered_at_start
            assert spec.risk is not Risk.NEVER
            assert command_id not in disabled
            assert not host.registry.reasons.get(command_id)
            if spec.risk is Risk.CONFIRM:
                assert len(asked_before_run) > questions_before
                assert host.confirm_answer
    for line in host.spoken:
        assert len(line.split()) <= 12, line


@pytest.mark.timeout(180)
@_SETTINGS
@given(world=_worlds(), text=_sentences)
def test_a_command_never_runs_when_it_was_never_offered(
    world: tuple[FakeHost, set[str], set[str]], text: str
) -> None:
    host, _disabled, _vanish = world
    offered = {item.spec.id for item in host.candidates()}
    CommandKeySession(host).submit(text)
    assert set(host.registry.ran) <= offered


@pytest.mark.timeout(180)
@_SETTINGS
@given(text=_sentences, answer=st.booleans())
def test_every_confirm_command_asks_whatever_the_sentence(text: str, answer: bool) -> None:
    rows = tuple(spec for spec in _ROWS["radio"] if spec.risk is Risk.CONFIRM)
    host = FakeHost(
        "radio", FakeRegistry(ids={spec.id for spec in rows}), rows, confirm_answer=answer
    )
    CommandKeySession(host).submit(text)
    if host.registry.ran:
        assert host.questions and answer
    if not answer:
        assert host.registry.ran == []
