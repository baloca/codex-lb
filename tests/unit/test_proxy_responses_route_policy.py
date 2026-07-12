from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi.responses import JSONResponse
from starlette.requests import Request

import app.modules.proxy.api as proxy_api_module

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _disable_fast_mode_policy_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    async def disabled() -> bool:
        return False

    monkeypatch.setattr(proxy_api_module, "_prohibit_fast_mode_enabled", disabled)


def _request(headers: dict[str, str] | None = None) -> Request:
    encoded_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/responses",
            "headers": encoded_headers,
            "client": ("127.0.0.1", 12345),
        }
    )


def _payload(**overrides: Any) -> proxy_api_module.V1ResponsesRequest:
    data: dict[str, Any] = {"model": "gpt-5.4", "input": "hi"}
    data.update(overrides)
    return proxy_api_module.V1ResponsesRequest.model_validate(data)


def _context() -> proxy_api_module.ProxyContext:
    return cast(proxy_api_module.ProxyContext, SimpleNamespace())


@pytest.mark.asyncio
async def test_v1_responses_stateless_batch_disables_bridge_and_cache_affinity(monkeypatch):
    captured: dict[str, Any] = {}

    async def fake_collect_responses(*args: Any, **kwargs: Any) -> JSONResponse:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return JSONResponse({"id": "resp_stateless", "object": "response", "status": "completed"})

    monkeypatch.setattr(proxy_api_module, "_collect_responses", fake_collect_responses)

    response = await proxy_api_module.v1_responses(
        _request({"x-codex-lb-route-policy": "responses_stateless_batch"}),
        _payload(stream=False),
        _context(),
        None,
    )

    assert response.status_code == 200
    assert response.headers["x-codex-lb-route-policy"] == "responses_stateless_batch"
    assert captured["kwargs"]["codex_session_affinity"] is False
    assert captured["kwargs"]["openai_cache_affinity"] is False
    assert captured["kwargs"]["prefer_http_bridge"] is False
    assert captured["kwargs"]["account_selection_lease_kind"] == "response_create"
    assert captured["kwargs"]["wait_for_account_response_create_capacity"] is True


@pytest.mark.asyncio
async def test_v1_responses_stateless_batch_cached_allows_prompt_cache_key(monkeypatch):
    captured: dict[str, Any] = {}

    async def fake_collect_responses(*args: Any, **kwargs: Any) -> JSONResponse:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return JSONResponse({"id": "resp_cached", "object": "response", "status": "completed"})

    monkeypatch.setattr(proxy_api_module, "_collect_responses", fake_collect_responses)

    response = await proxy_api_module.v1_responses(
        _request({"x-codex-lb-route-policy": "responses_stateless_batch_cached"}),
        _payload(stream=False, prompt_cache_key="cache_123"),
        _context(),
        None,
    )

    forwarded_payload = captured["args"][1]
    assert response.status_code == 200
    assert response.headers["x-codex-lb-route-policy"] == "responses_stateless_batch_cached"
    assert forwarded_payload.prompt_cache_key == "cache_123"
    assert captured["kwargs"]["codex_session_affinity"] is False
    assert captured["kwargs"]["openai_cache_affinity"] is True
    assert captured["kwargs"]["prefer_http_bridge"] is False
    assert captured["kwargs"]["account_selection_lease_kind"] == "response_create"
    assert captured["kwargs"]["wait_for_account_response_create_capacity"] is True


def test_cached_stateless_batch_affinity_policy_pins_prompt_cache_key_to_account():
    from app.db.models import StickySessionKind
    from app.modules.proxy.affinity import _sticky_key_for_responses_request

    affinity = _sticky_key_for_responses_request(
        _payload(stream=False, prompt_cache_key="cache_123").to_responses_request(),
        {},
        codex_session_affinity=False,
        openai_cache_affinity=True,
        openai_cache_affinity_max_age_seconds=1800,
        sticky_threads_enabled=False,
    )

    assert affinity.key == "cache_123"
    assert affinity.kind == StickySessionKind.PROMPT_CACHE
    assert affinity.reallocate_sticky is False
    assert affinity.max_age_seconds == 1800


@pytest.mark.asyncio
async def test_v1_responses_default_route_keeps_existing_bridge_policy(monkeypatch):
    captured: dict[str, Any] = {}

    async def fake_collect_responses(*args: Any, **kwargs: Any) -> JSONResponse:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return JSONResponse({"id": "resp_default", "object": "response", "status": "completed"})

    monkeypatch.setattr(proxy_api_module, "_collect_responses", fake_collect_responses)

    response = await proxy_api_module.v1_responses(
        _request(),
        _payload(stream=False),
        _context(),
        None,
    )

    assert response.status_code == 200
    assert "x-codex-lb-route-policy" not in response.headers
    assert captured["kwargs"]["codex_session_affinity"] is False
    assert captured["kwargs"]["openai_cache_affinity"] is True
    assert captured["kwargs"]["prefer_http_bridge"] is True


@pytest.mark.asyncio
async def test_v1_responses_rejects_unknown_route_policy(monkeypatch):
    async def fail_collect_responses(*args: Any, **kwargs: Any) -> JSONResponse:
        del args, kwargs
        pytest.fail("unknown route-policy requests must not reach _collect_responses")

    monkeypatch.setattr(proxy_api_module, "_collect_responses", fail_collect_responses)

    response = await proxy_api_module.v1_responses(
        _request({"x-codex-lb-route-policy": "mystery"}),
        _payload(stream=False),
        _context(),
        None,
    )

    body = json.loads(bytes(response.body))
    assert response.status_code == 400
    assert body["error"]["code"] == "route_policy_unsupported"


@pytest.mark.parametrize(
    ("payload_overrides", "headers", "expected_message"),
    [
        ({"stream": True}, {}, "requires stream=false"),
        ({"previous_response_id": "resp_123"}, {}, "previous_response_id"),
        ({"conversation": "conv_123"}, {}, "conversation"),
        ({"prompt_cache_key": "cache_123"}, {}, "prompt_cache_key"),
        ({}, {"x-codex-session-id": "session_123"}, "x-codex-session-id"),
        ({}, {"x-codex-conversation-id": "conversation_123"}, "x-codex-conversation-id"),
        ({}, {"x-codex-turn-state": "turn_123"}, "x-codex-turn-state"),
    ],
)
@pytest.mark.asyncio
async def test_v1_responses_stateless_batch_rejects_stateful_inputs(
    monkeypatch,
    payload_overrides: dict[str, Any],
    headers: dict[str, str],
    expected_message: str,
):
    async def fail_collect_responses(*args: Any, **kwargs: Any) -> JSONResponse:
        del args, kwargs
        pytest.fail("stateful stateless-batch requests must not reach _collect_responses")

    monkeypatch.setattr(proxy_api_module, "_collect_responses", fail_collect_responses)
    request_headers = {"x-codex-lb-route-policy": "responses_stateless_batch", **headers}

    response = await proxy_api_module.v1_responses(
        _request(request_headers),
        _payload(**payload_overrides),
        _context(),
        None,
    )

    body = json.loads(bytes(response.body))
    assert response.status_code == 400
    assert response.headers["x-codex-lb-route-policy"] == "responses_stateless_batch"
    assert body["error"]["code"] == "route_policy_conflict"
    assert expected_message in body["error"]["message"]


@pytest.mark.parametrize(
    ("payload_overrides", "headers", "expected_message"),
    [
        ({"stream": True}, {}, "requires stream=false"),
        ({"previous_response_id": "resp_123"}, {}, "previous_response_id"),
        ({"conversation": "conv_123"}, {}, "conversation"),
        ({}, {"x-codex-session-id": "session_123"}, "x-codex-session-id"),
        ({}, {"x-codex-conversation-id": "conversation_123"}, "x-codex-conversation-id"),
        ({}, {"x-codex-turn-state": "turn_123"}, "x-codex-turn-state"),
    ],
)
@pytest.mark.asyncio
async def test_v1_responses_stateless_batch_cached_rejects_stateful_inputs(
    monkeypatch,
    payload_overrides: dict[str, Any],
    headers: dict[str, str],
    expected_message: str,
):
    async def fail_collect_responses(*args: Any, **kwargs: Any) -> JSONResponse:
        del args, kwargs
        pytest.fail("stateful stateless-batch-cached requests must not reach _collect_responses")

    monkeypatch.setattr(proxy_api_module, "_collect_responses", fail_collect_responses)
    request_headers = {"x-codex-lb-route-policy": "responses_stateless_batch_cached", **headers}

    response = await proxy_api_module.v1_responses(
        _request(request_headers),
        _payload(**payload_overrides),
        _context(),
        None,
    )

    body = json.loads(bytes(response.body))
    assert response.status_code == 400
    assert response.headers["x-codex-lb-route-policy"] == "responses_stateless_batch_cached"
    assert body["error"]["code"] == "route_policy_conflict"
    assert expected_message in body["error"]["message"]
