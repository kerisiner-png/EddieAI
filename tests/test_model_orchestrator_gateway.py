from unittest.mock import patch, MagicMock


def _make_orchestrator(providers):
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    mo.CLOUD_PROVIDERS = providers
    mo.CLOUD_TIMEOUT_SEC = 90
    mo.CLOUD_NET_COOLDOWN_SEC = 90
    mo.CLOUD_BILLING_COOLDOWN_SEC = 1800
    mo._cloud_blocked = {}
    mo._cloud_last_error = {}
    mo._cloud_used = ""
    return mo


def _fake_response(message):
    body = '{"choices":[{"message":' + str(message).replace("'", '"') + '}]}'
    resp = MagicMock()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    resp.read.return_value = body.encode("utf-8")
    return resp


def test_glm_provider_disables_thinking():
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    glm = next(
        p for p in mo.CLOUD_PROVIDERS if p["name"] == "glm"
    )
    assert glm["extra_payload"] == {
        "thinking": {"type": "disabled"}
    }


def test_cloud_chat_provider_calls_glm_with_thinking_disabled(tmp_path):
    from core.model_orchestrator import ModelOrchestrator
    key = tmp_path / "glm.key"
    key.write_text("test-key", encoding="utf-8")
    mo = _make_orchestrator([{
        "name": "glm",
        "model": "glm-4.5-flash",
        "url": "https://api.z.ai/api/paas/v4/chat/completions",
        "key_path": key,
        "extra_payload": {"thinking": {"type": "disabled"}},
    }])
    resp = _fake_response({
        "content": "Привет, Эдди!",
        "reasoning_content": "",
        "role": "assistant",
    })
    provider = mo.CLOUD_PROVIDERS[0]
    with patch("core.model_orchestrator.urllib.request.urlopen",
               return_value=resp) as mock_open:
        result = mo._cloud_chat_provider(
            provider, "sys", "user", {"temperature": 0.8}, 0
        )
    assert result == "Привет, Эдди!"
    payload = mock_open.call_args[0][0].data.decode("utf-8")
    assert '"thinking": {"type": "disabled"}' in payload


def test_cloud_chat_provider_does_not_use_reasoning_content(tmp_path):
    from core.model_orchestrator import ModelOrchestrator
    key = tmp_path / "glm.key"
    key.write_text("test-key", encoding="utf-8")
    mo = _make_orchestrator([{
        "name": "glm",
        "model": "glm-4.5-flash",
        "url": "https://api.z.ai/api/paas/v4/chat/completions",
        "key_path": key,
        "extra_payload": {"thinking": {"type": "disabled"}},
    }])
    resp = _fake_response({
        "content": "",
        "reasoning_content": "В этом сценарии мне нужно ответить...",
        "role": "assistant",
    })
    provider = mo.CLOUD_PROVIDERS[0]
    with patch("core.model_orchestrator.urllib.request.urlopen",
               return_value=resp):
        result = mo._cloud_chat_provider(
            provider, "sys", "user", {"temperature": 0.8}, 0
        )
    assert result is None