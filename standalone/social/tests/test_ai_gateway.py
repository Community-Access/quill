"""Tests for the AI provider gateway (PRD 21.2)."""

from quill_social.services.ai.gateway import (
    AIGateway,
    Disclosure,
    GatewayResult,
    MockProvider,
    ProviderMode,
)


class RecordingProvider:
    """Captures exactly what text it was asked to complete."""

    name = "recording"
    model = "recording-v1"

    def __init__(self) -> None:
        self.seen: list[str] = []

    def complete(self, system, user, tools=None):
        self.seen.append(user)
        return f"[done] {user}"


def test_disabled_refuses_without_raising():
    gw = AIGateway(mode=ProviderMode.disabled)
    res = gw.run("summarize", "sys", "hello")
    assert res.refused
    assert not res.ok
    assert "disabled" in res.reason.lower()
    assert res.text == ""
    # A disclosure is still produced so the UI can explain the state.
    assert res.disclosure is not None


def test_mock_runs_and_echoes():
    gw = AIGateway(mode=ProviderMode.mock)
    res = gw.run("summarize", "sys", "hello world")
    assert res.ok
    assert res.text == "hello world"
    assert res.disclosure.provider == "mock"
    assert res.disclosure.model == "mock-echo-v1"


def test_disclosure_reports_provider_data_and_redactions():
    gw = AIGateway(mode=ProviderMode.mock)
    res = gw.run("writing", "sys", "my api_key=SUPERSECRETVALUE ok")
    disc = res.disclosure
    assert disc.provider == "mock"
    assert disc.estimated_cost is None
    assert "credential_assignment" in disc.redactions_applied
    assert "characters" in disc.data_being_sent
    # The redacted preview must not leak the secret value.
    assert "SUPERSECRETVALUE" not in disc.data_being_sent


def test_secret_redacted_before_provider_sees_it():
    prov = RecordingProvider()
    gw = AIGateway(mode=ProviderMode.api_key, provider=prov)
    gw.run("writing", "sys", "token: ABCDEF123456 please")
    assert prov.seen  # provider was called
    assert "ABCDEF123456" not in prov.seen[0]
    assert "[REDACTED]" in prov.seen[0]


def test_per_feature_provider_selection():
    special = RecordingProvider()
    gw = AIGateway(
        mode=ProviderMode.mock,
        feature_providers={"writing.shorten": special},
    )
    assert gw.provider_for("writing.shorten") is special
    # A different feature falls back to the mode default (a fresh MockProvider).
    other = gw.provider_for("understand.summarize")
    assert isinstance(other, MockProvider)


def test_per_feature_mode_can_disable_one_feature():
    gw = AIGateway(
        mode=ProviderMode.mock,
        feature_modes={"understand.translate": ProviderMode.disabled},
    )
    assert gw.run("writing", "s", "hi").ok
    assert gw.run("understand.translate", "s", "hi").refused


def test_available_reports_dependency_presence():
    gw = AIGateway()
    assert gw.available(ProviderMode.mock) is True
    assert gw.available(ProviderMode.disabled) is True
    # No injected provider => brokered/org modes are an unmet boundary.
    assert gw.available(ProviderMode.quill_brokered) is False
    assert gw.available(ProviderMode.org_managed) is False


def test_unconfigured_live_mode_is_honest_boundary():
    gw = AIGateway(mode=ProviderMode.quill_brokered)
    res = gw.run("writing", "sys", "hi")
    assert res.refused
    assert "boundary" in res.reason.lower()


def test_disclosure_and_result_roundtrip():
    disc = Disclosure(provider="mock", model="m", redactions_applied=["jwt"])
    assert Disclosure.from_dict(disc.to_dict()) == disc
    res = GatewayResult(feature="f", text="t", disclosure=disc)
    back = GatewayResult.from_dict(res.to_dict())
    assert back.feature == "f"
    assert back.text == "t"
    assert back.disclosure == disc
