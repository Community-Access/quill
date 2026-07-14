"""Unit tests for the wx-free cloud<->local AI fallback decisions (Phase 4)."""

from __future__ import annotations

import socket
from urllib.error import HTTPError, URLError

import pytest

from quill.core.ai.fallback import (
    FallbackPlan,
    classify_exception,
    is_local_provider,
    plan_fallback,
)


@pytest.mark.parametrize(
    ("pid", "expected"),
    [("ollama", True), ("llama_cpp", True), ("OpenAI", False), ("claude", False), ("", False)],
)
def test_is_local_provider(pid: str, expected: bool) -> None:
    assert is_local_provider(pid) is expected


# --- exception classification ---------------------------------------------


def test_classify_timeout() -> None:
    assert classify_exception(TimeoutError()) == "timeout"


def test_classify_rate_limit_and_server_error() -> None:
    assert classify_exception(HTTPError("u", 429, "too many", {}, None)) == "rate_limit"  # type: ignore[arg-type]
    assert classify_exception(HTTPError("u", 503, "down", {}, None)) == "server_error"  # type: ignore[arg-type]


def test_classify_client_error_is_other() -> None:
    assert classify_exception(HTTPError("u", 400, "bad", {}, None)) == "other"  # type: ignore[arg-type]


def test_classify_urlerror_and_connection_are_offline() -> None:
    assert classify_exception(URLError("no route")) == "offline"
    assert classify_exception(ConnectionError()) == "offline"
    assert classify_exception(socket.gaierror()) == "offline"


def test_classify_unknown_is_other() -> None:
    assert classify_exception(ValueError("nope")) == "other"


# --- fallback planning -----------------------------------------------------


def test_non_connectivity_failure_never_falls_back() -> None:
    plan = plan_fallback(
        primary_provider="openai",
        failure_kind="other",
        local_available=True,
        cloud_available=True,
    )
    assert plan.offer is False


def test_cloud_failure_offers_local_without_consent() -> None:
    plan = plan_fallback(
        primary_provider="openai",
        failure_kind="offline",
        local_available=True,
        cloud_available=False,
    )
    assert plan.offer is True
    assert plan.to_provider == "local"
    assert plan.requires_consent is False
    assert "stays on this computer" in plan.announcement


def test_cloud_failure_with_no_local_makes_no_offer() -> None:
    plan = plan_fallback(
        primary_provider="claude",
        failure_kind="timeout",
        local_available=False,
        cloud_available=False,
    )
    assert plan.offer is False


def test_local_failure_offers_cloud_but_requires_consent() -> None:
    plan = plan_fallback(
        primary_provider="ollama",
        failure_kind="server_error",
        local_available=True,
        cloud_available=True,
        cloud_provider="OpenAI",
    )
    assert plan.offer is True
    assert plan.to_provider == "OpenAI"
    assert plan.requires_consent is True  # data would leave the device
    assert "sends your text" in plan.announcement
    assert "OpenAI" in plan.announcement


def test_local_failure_with_no_cloud_makes_no_offer() -> None:
    plan = plan_fallback(
        primary_provider="ollama",
        failure_kind="offline",
        local_available=True,
        cloud_available=False,
    )
    assert plan.offer is False


def test_plan_none_helper() -> None:
    assert FallbackPlan.none().offer is False
