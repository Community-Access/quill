"""Jev as the assist, and Choose Your AI behind it (docs/design/command-key.md 7, 14.2, 14.3).

Everything here runs offline against ``FakeJevClient`` and
``FakeCommandPickEngine``. No test reaches TypeSafe; the live suite is
``tests/live/test_jev_live.py``, marked ``live_jev`` and never run in PR CI.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from command_key_fakes import (
    FakeCommandPickEngine,
    FakeJevClient,
    FakeRegistry,
    host_for,
    jev_answer,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from quill.core.command_catalogue import Risk, row, rows_for_app
from quill.core.command_catalogue import jev as jev_mod
from quill.core.command_catalogue.args import read_args
from quill.core.command_catalogue.assist import (
    CommandPickAssist,
    JevAssist,
    command_pick_prompt,
    parse_command_pick,
)
from quill.core.command_catalogue.jev import (
    GatewayJev,
    JevAnswer,
    JevBadAnswer,
    JevDisabled,
    JevFailed,
    JevLimit,
    JevNoCredit,
    OwnKeyJev,
    Throttle,
    parse_answer,
    read_answer,
)
from quill.core.command_catalogue.jev_request import (
    JEV_MODEL,
    MAX_CANDIDATES,
    NONE_OF_THESE,
    PrivateDataInRequest,
    build_request,
    payload_is_private,
)
from quill.core.command_catalogue.policy import CommandKeySession, Outcome
from quill.core.command_catalogue.resolver import Candidate


def _cands(app: str = "radio") -> list[Candidate]:
    return [Candidate(spec) for spec in rows_for_app(app) if spec.offered]


def _request(text: str = "it's way too loud in here", app: str = "radio", **kwargs: Any):
    return build_request(
        text, _cands(app), app=app, surface="Quill Radio", args=read_args(text), **kwargs
    )


# -- the request ------------------------------------------------------------------


def test_the_request_has_the_pinned_model_and_typesafes_shape() -> None:
    request = _request()
    body = request.body
    assert body["model"] == JEV_MODEL
    assert set(body) == {"model", "state", "questions"}
    action = body["questions"]["action"]
    assert action["type"] == "choice" and NONE_OF_THESE in action["criteria"]
    assert "radio.volume_down" in action["criteria"]
    assert body["questions"]["fits"]["type"] == "noul"
    assert "size" in body["questions"]  # Radio has stepped commands
    assert "correction" not in body["questions"]


def test_the_state_carries_only_what_section_7_2_allows() -> None:
    request = _request("skip back 30 seconds", recent=["radio.volume_up"] * 9)
    state = request.body["state"]
    assert set(state) == {"request", "app", "surface", "recent", "last_offer", "local_matches"}
    assert state["local_matches"] == {"number": None, "duration_seconds": 30}
    assert len(state["recent"]) == 5
    assert "correction" in request.body["questions"]


def test_the_request_text_is_capped() -> None:
    assert len(_request("x" * 900).body["state"]["request"]) == 300


def test_at_most_sixty_candidates_go() -> None:
    many = _cands("quill") * 3
    request = build_request("x", many, app="quill", surface="", args=read_args("x"))
    assert len(request.offered) == MAX_CANDIDATES


def test_private_words_never_go_and_a_request_that_would_carry_one_is_refused() -> None:
    body = _request().body
    assert payload_is_private(body, ["WNYC", "Budget.docx"])
    with pytest.raises(PrivateDataInRequest):
        build_request(
            "x",
            _cands(),
            app="radio",
            surface="WNYC Studio",
            args=read_args("x"),
            private_words=["WNYC"],
        )


def test_a_name_the_person_typed_is_their_own_request() -> None:
    request = _request("play WNYC", private_words=["WNYC"])
    assert request.body["state"]["request"] == "play WNYC"


# -- reading the answer -------------------------------------------------------------


def test_parse_keeps_only_offered_options_and_refuses_others() -> None:
    offered = ("radio.volume_down", "radio.volume_up")
    answer = parse_answer(jev_answer({"radio.volume_down": 0.9, "radio.volume_up": 0.1}), offered)
    assert answer.ranked()[0] == ("radio.volume_down", 0.9)
    with pytest.raises(JevBadAnswer):
        parse_answer(jev_answer({"radio.update_catalog": 0.9}), offered)


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"answers": {}},
        {"answers": {"action": {}}},
        {"answers": {"action": {"probabilities": {}}}},
        {"answers": {"action": {"probabilities": {"a": "high"}}, "fits": {"noul": 0.9}}},
        {"answers": {"action": {"probabilities": {"a": 1.5}}, "fits": {"noul": 0.9}}},
        {"answers": {"action": {"probabilities": {"a": 0.5}}, "fits": {}}},
        {"answers": {"action": {"probabilities": {"a": True}}, "fits": {"noul": 0.9}}},
    ],
)
def test_a_malformed_answer_is_a_coded_bad_answer(raw: dict[str, Any]) -> None:
    with pytest.raises(JevBadAnswer) as caught:
        parse_answer(raw, ("a",))
    assert "QUILL-AI-DECIDE-BAD-ANSWER" in str(caught.value)


def _answer(probabilities: dict[str, float], **kwargs: Any) -> JevAnswer:
    return parse_answer(jev_answer(probabilities, **kwargs), tuple(probabilities))


def test_fits_decides_a_refusal() -> None:
    assert read_answer(_answer({"a.b": 0.95, "c.d": 0.05}, fits=0.2)).kind == "refuse"


def test_action_decides_an_act() -> None:
    verdict = read_answer(_answer({"a.b": 0.95, "c.d": 0.05}))
    assert (verdict.kind, verdict.ids) == ("act", ("a.b",))


def test_a_split_asks_between_the_two() -> None:
    verdict = read_answer(_answer({"a.b": 0.5, "c.d": 0.45, "e.f": 0.05}))
    assert verdict.kind == "ask" and set(verdict.ids) == {"a.b", "c.d"}


def test_none_of_these_winning_is_a_refusal() -> None:
    assert read_answer(_answer({NONE_OF_THESE: 0.8, "a.b": 0.2})).kind == "refuse"


def test_is_question_decides_a_readout() -> None:
    verdict = read_answer(
        _answer({"radio.whats_playing_details": 0.6, "radio.stop": 0.4}, is_question=0.9),
        frozenset({"radio.whats_playing_details"}),
    )
    assert verdict.kind == "readout"


def test_size_is_carried_through() -> None:
    assert read_answer(_answer({"a.b": 0.95, "c.d": 0.05}, size="large")).size == "large"


def test_low_confidence_with_a_clear_leader_is_a_refusal() -> None:
    answer = JevAnswer({"a.b": 0.3, "c.d": 0.05, NONE_OF_THESE: 0.1}, confidence=0.2, fits=0.6)
    assert read_answer(answer).kind == "refuse"


# -- the assist in the session --------------------------------------------------------


def _assisted_session(rule: Any = None, *, error: Exception | None = None, fallback: Any = None):
    host = host_for("radio")
    client = FakeJevClient(rule=rule, error=error)
    assist = JevAssist(client, "radio", host.announce, fallback=fallback)
    return CommandKeySession(host, assist=assist), host, client


def test_jev_settles_loose_phrasing_tier_2_could_not() -> None:
    session, host, client = _assisted_session(
        lambda _r: jev_answer({"radio.volume_up": 0.92, "radio.volume_down": 0.08}, size="large")
    )
    decision = session.submit("I can barely make it out over the kettle")
    assert decision.outcome is Outcome.RUN and decision.tier == 3
    assert host.registry.ran == ["radio.volume_up"] * 3
    assert client.requests and client.requests[0]["state"]["request"].startswith("I can barely")


def test_jev_is_not_asked_what_tier_1_settled() -> None:
    session, host, client = _assisted_session(lambda _r: jev_answer({"radio.stop": 1.0}))
    session.submit("louder")
    assert client.requests == [] and host.registry.ran == ["radio.volume_up"]


def test_jev_is_never_asked_to_second_guess_a_deliberate_refusal() -> None:
    session, host, client = _assisted_session(lambda _r: jev_answer({"radio.recordings": 1.0}))
    session.submit("delete all my recordings")
    assert client.requests == [] and host.registry.ran == []


def test_a_jev_answer_for_a_confirm_command_still_asks() -> None:
    session, host, _client = _assisted_session(
        lambda _r: jev_answer({"radio.stop_all_recordings": 0.95, "radio.stop": 0.05})
    )
    host.confirm_answer = False
    session.submit("cease all the capturing")
    assert host.questions and host.registry.ran == []


@pytest.mark.parametrize(
    ("error", "line"),
    [
        (JevLimit("x"), "Jev's daily limit is reached, so I matched it here."),
        (JevNoCredit("x"), "Jev's credit is spent for now, so I matched it here."),
        (JevDisabled("x"), "Jev is turned off, so I matched it here."),
        (JevFailed("x"), "Jev isn't answering, so I matched it here."),
        (JevBadAnswer("x"), "Jev isn't answering, so I matched it here."),
    ],
)
def test_each_failure_falls_back_and_says_so_once(error: Exception, line: str) -> None:
    session, host, _client = _assisted_session(error=error)
    session.submit("flibbertigibbet")
    session.submit("wibble wobble")
    assert host.spoken.count(line) == 1
    assert host.registry.ran == []


def test_a_failure_falls_to_choose_your_ai() -> None:
    engine = FakeCommandPickEngine(reply="radio.jump_to_live")
    session, host, _client = _assisted_session(
        error=JevLimit("x"), fallback=CommandPickAssist(engine)
    )
    host.choose_index = 0
    decision = session.submit("take me to whatever is broadcasting this second")
    assert decision.tier == 4 and engine.prompts
    assert host.registry.ran == ["radio.jump_to_live"]


# -- tier 4 -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reply", "expect"),
    [
        ("radio.stop", "radio.stop"),
        ("I think it is `radio.stop`.", "radio.stop"),
        ('{"id": "radio.stop"}', "radio.stop"),
        ("none", None),
        ("", None),
        ("radio.update_catalog", None),  # NEVER, so not a candidate
        ("radio.stop or radio.play_pause", None),  # two is not one
        ("radio.no_such_command", None),
    ],
)
def test_tier_4_reads_only_one_offered_id(reply: str, expect: str | None) -> None:
    picked = parse_command_pick(reply, _cands())
    assert (picked.spec.id if picked else None) == expect


def test_the_tier_4_prompt_names_ids_and_descriptions_only() -> None:
    prompt = command_pick_prompt("turn it down", _cands())
    assert "radio.volume_down: Make the radio quieter" in prompt
    assert "Request: turn it down" in prompt


def test_tier_4_acts_only_when_it_agrees_with_tier_2_and_is_safe() -> None:
    agree = CommandPickAssist(FakeCommandPickEngine("radio.volume_down"))("turn it down", _cands())
    assert agree is not None and agree.kind == "run"
    disagree = CommandPickAssist(FakeCommandPickEngine("radio.stop"))("turn it down", _cands())
    assert disagree is not None and disagree.kind == "choose"
    confirm = CommandPickAssist(FakeCommandPickEngine("radio.record_toggle"))(
        "record this", _cands()
    )
    assert confirm is not None and confirm.kind == "choose"


def test_tier_4_failure_is_coded_and_offline_answer_stands(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    caplog.set_level(logging.INFO)
    assist = CommandPickAssist(FakeCommandPickEngine(error=RuntimeError("offline")))
    assert assist("turn it down", _cands()) is None
    assert "QUILL-AI-COMMANDPICK-FAILED" in caplog.text
    assert CommandPickAssist(FakeCommandPickEngine("none"))("x", _cands()) is None
    assert CommandPickAssist(FakeCommandPickEngine("x"))("x", []) is None


# -- the routes ------------------------------------------------------------------------


def test_own_key_without_a_key_is_disabled_and_stops_for_the_day() -> None:
    posted: list[str] = []
    route = OwnKeyJev(lambda: "", post=lambda *args, **kw: posted.append("x") or {})
    with pytest.raises(JevDisabled):
        route.decide(_request())
    assert posted == []
    with pytest.raises(JevDisabled):  # remembered, not asked again
        route.decide(_request())


def test_own_key_posts_the_body_to_typesafe_with_the_key() -> None:
    seen: dict[str, Any] = {}

    def post(url: str, body: Any, bearer: str, deadline: float) -> dict[str, Any]:
        seen.update(url=url, body=body, bearer=bearer)
        return jev_answer({"radio.volume_down": 0.9, "radio.volume_up": 0.1})

    answer = OwnKeyJev(lambda: "sk-test", post=post).decide(_request())
    assert seen["url"] == jev_mod.TYPESAFE_URL and seen["bearer"] == "sk-test"
    assert answer.ranked()[0][0] == "radio.volume_down"


def test_the_gateway_route_is_not_deployed_yet() -> None:
    with pytest.raises(JevDisabled):
        GatewayJev().decide(_request())


def test_the_gateway_route_sends_state_and_version_not_questions() -> None:
    seen: dict[str, Any] = {}

    def post(url: str, body: Any, bearer: str, deadline: float) -> dict[str, Any]:
        seen.update(url=url, body=body, bearer=bearer)
        return jev_answer({"radio.stop": 0.9, "radio.play_pause": 0.1})

    GatewayJev("https://gateway.test", lambda: "device-token", post=post).decide(_request())
    assert seen["url"] == "https://gateway.test/v1/decide"
    assert set(seen["body"]) == {"app", "catalogue_version", "question_set", "state"}


def test_a_limit_stops_asking_until_tomorrow() -> None:
    today = [date(2026, 11, 8)]
    calls: list[int] = []

    def post(*_args: Any) -> dict[str, Any]:
        calls.append(1)
        raise JevLimit("x")

    route = OwnKeyJev(lambda: "k", post=post, throttle=Throttle(today=lambda: today[0]))
    for _ in range(3):
        with pytest.raises(JevLimit):
            route.decide(_request())
    assert calls == [1]
    today[0] = date(2026, 11, 9)
    with pytest.raises(JevLimit):
        route.decide(_request())
    assert calls == [1, 1]


def test_a_plain_failure_is_tried_again_next_time() -> None:
    calls: list[int] = []

    def post(*_args: Any) -> dict[str, Any]:
        calls.append(1)
        raise JevFailed("x")

    route = OwnKeyJev(lambda: "k", post=post)
    for _ in range(2):
        with pytest.raises(JevFailed):
            route.decide(_request())
    assert calls == [1, 1]


def test_one_request_in_flight() -> None:
    route = OwnKeyJev(lambda: "k", post=lambda *_a: {})
    route.throttle._lock.acquire()
    try:
        with pytest.raises(JevFailed):
            route.decide(_request())
    finally:
        route.throttle._lock.release()


@pytest.mark.parametrize(
    ("status", "payload", "error"),
    [
        (402, {}, JevNoCredit),
        (403, {"error": "no_credit"}, JevNoCredit),
        (503, {"error": "disabled"}, JevDisabled),
        (429, {"error": "limit_reached"}, JevLimit),
        (500, {}, JevFailed),
    ],
)
def test_server_answers_map_to_codes(status: int, payload: dict[str, Any], error: type) -> None:
    assert isinstance(jev_mod._error_for(status, payload), error)


def test_post_honours_retry_after_only_within_three_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import io
    import urllib.error

    attempts: list[int] = []

    class _Headers(dict):
        def get(self, key: str, default: Any = None) -> Any:
            return super().get(key.lower(), default)

    def fake_urlopen(*_args: Any, **_kwargs: Any) -> Any:
        attempts.append(1)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(
                "u", 429, "busy", _Headers({"retry-after": "0"}), io.BytesIO(b"{}")
            )

        class _Response(io.BytesIO):
            def __enter__(self) -> Any:
                return self

            def __exit__(self, *_exc: Any) -> None:
                return None

        return _Response(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(jev_mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(jev_mod.time, "sleep", lambda _s: None)
    assert jev_mod._post_json("https://x.test", {}, "k", jev_mod.time.monotonic() + 3) == {
        "ok": True
    }
    assert len(attempts) == 2
    with pytest.raises(JevFailed):
        jev_mod._post_json("https://x.test", {}, "k", jev_mod.time.monotonic() - 1)


def test_post_turns_network_trouble_into_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error

    def unreachable(*_args: Any, **_kwargs: Any) -> Any:
        raise urllib.error.URLError("down")

    monkeypatch.setattr(jev_mod.urllib.request, "urlopen", unreachable)
    with pytest.raises(JevFailed):
        jev_mod._post_json("https://x.test", {}, "k", jev_mod.time.monotonic() + 3)


def test_the_key_is_read_from_credential_manager_and_never_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.platform.windows import credential_manager

    asked: list[str] = []

    class _Stored:
        secret = "sk-from-vault"

    monkeypatch.setattr(
        credential_manager, "load_generic_credential", lambda name: asked.append(name) or _Stored()
    )
    assert jev_mod._key_from_credential_manager() == "sk-from-vault"
    assert asked == [jev_mod.DEV_KEY_TARGET] == ["QUILL TypeSafe dev key"]
    monkeypatch.setattr(credential_manager, "load_generic_credential", lambda _name: None)
    assert jev_mod._key_from_credential_manager() == ""


# -- properties: random Jev answers never break the rules (14.3) ------------------------

_IDS = sorted({spec.id for spec in rows_for_app("radio")} | {"quill.no_such", NONE_OF_THESE})


@pytest.mark.timeout(180)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    probabilities=st.dictionaries(st.sampled_from(_IDS), st.floats(0, 1), min_size=1, max_size=6),
    fits=st.floats(0, 1),
    question=st.floats(0, 1),
    answer=st.booleans(),
    text=st.sampled_from(["mmm", "the thing", "do the business", "zzz", "make it so"]),
)
def test_any_jev_answer_keeps_the_safety_rules(
    probabilities: dict[str, float], fits: float, question: float, answer: bool, text: str
) -> None:
    host = host_for("radio", confirm_answer=answer)
    offered = {item.spec.id for item in host.candidates()}
    client = FakeJevClient(
        rule=lambda _r: jev_answer(probabilities, fits=fits, is_question=question)
    )
    session = CommandKeySession(host, assist=JevAssist(client, "radio", host.announce))
    session.submit(text)
    for command_id in host.registry.ran:
        spec = row(command_id, "radio")
        assert command_id in offered and spec is not None and spec.risk is not Risk.NEVER
        if spec.risk is Risk.CONFIRM:
            assert host.questions and answer
    for request in client.requests:
        criteria = request["questions"]["action"]["criteria"]
        assert all(row(cid, "radio") is None or row(cid, "radio").offered for cid in criteria)  # type: ignore[union-attr]


def test_no_never_command_is_ever_sent_to_jev() -> None:
    client = FakeJevClient(rule=lambda _r: jev_answer({NONE_OF_THESE: 1.0}))
    host = host_for("radio")
    CommandKeySession(host, assist=JevAssist(client, "radio", host.announce)).submit("mmm")
    criteria = client.requests[0]["questions"]["action"]["criteria"]
    assert "radio.update_catalog" not in criteria and "radio.chatgpt_account" not in criteria
    assert FakeRegistry  # the fakes module is the shared one
