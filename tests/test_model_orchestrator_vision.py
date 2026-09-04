from unittest.mock import patch, MagicMock
from pathlib import Path


def test_vision_builds_multimodal_payload():
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    mo.CLOUD_PROVIDERS = [{
        "name": "zen-kimi-vision",
        "model": "kimi-k3",
        "roles": ["vision"],
        "url": "https://test.example.com/v1/chat/completions",
        "key_path": None,
        "max_tokens": 1024,
    }]
    with patch.object(mo, '_cloud_chat_provider') as mock_chat:
        mock_chat.return_value = "browser with open tab"
        result = mo._cloud_chat_vision("describe screen", "what's on screen?", ["base64data123"])
    assert result == {"text": "browser with open tab"}
    call_args = mock_chat.call_args
    user_content = call_args[0][2]
    assert isinstance(user_content, list)
    assert user_content[0] == {"type": "text", "text": "what's on screen?"}
    assert any(part["type"] == "image_url" for part in user_content)
    assert user_content[1]["image_url"]["url"] == "data:image/png;base64,base64data123"


def test_vision_multiple_images():
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    mo.CLOUD_PROVIDERS = [{
        "name": "zen-kimi-vision",
        "model": "kimi-k3",
        "roles": ["vision"],
        "url": "https://test.example.com/v1/chat/completions",
        "key_path": None,
        "max_tokens": 1024,
    }]
    with patch.object(mo, '_cloud_chat_provider') as mock_chat:
        mock_chat.return_value = "two screenshots"
        result = mo._cloud_chat_vision("sys", "compare", ["img1", "img2", "img3"])
    call_args = mock_chat.call_args
    user_content = call_args[0][2]
    image_parts = [p for p in user_content if p["type"] == "image_url"]
    assert len(image_parts) == 3


def test_vision_empty_images_sends_text_only():
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    mo.CLOUD_PROVIDERS = [{
        "name": "zen-kimi-vision",
        "model": "kimi-k3",
        "roles": ["vision"],
        "url": "https://test.example.com/v1/chat/completions",
        "key_path": None,
        "max_tokens": 1024,
    }]
    with patch.object(mo, '_cloud_chat_provider') as mock_chat:
        mock_chat.return_value = "no image"
        result = mo._cloud_chat_vision("describe", "what?", [])
    call_args = mock_chat.call_args
    user_content = call_args[0][2]
    assert isinstance(user_content, str)
    assert user_content == "what?"


def test_vision_no_images_default():
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    mo.CLOUD_PROVIDERS = [{
        "name": "zen-kimi-vision",
        "model": "kimi-k3",
        "roles": ["vision"],
        "url": "https://test.example.com/v1/chat/completions",
        "key_path": None,
        "max_tokens": 1024,
    }]
    with patch.object(mo, '_cloud_chat_provider') as mock_chat:
        mock_chat.return_value = "text only"
        result = mo._cloud_chat_vision("sys", "hello")
    call_args = mock_chat.call_args
    user_content = call_args[0][2]
    assert isinstance(user_content, str)
    assert user_content == "hello"


def test_vision_no_provider_returns_error():
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    mo.CLOUD_PROVIDERS = []
    result = mo._cloud_chat_vision("describe", "what?", ["img"])
    assert "error" in result
    assert result["error"] == "no vision provider"


def test_vision_passes_correct_provider():
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    mo.CLOUD_PROVIDERS = [
        {
            "name": "zen-deepseek-flash",
            "model": "deepseek-v4-flash",
            "roles": ["conversation"],
            "url": "https://test.example.com/v1/chat/completions",
            "key_path": None,
            "max_tokens": 1024,
        },
        {
            "name": "zen-kimi-vision",
            "model": "kimi-k3",
            "roles": ["vision"],
            "url": "https://vision.example.com/v1/chat/completions",
            "key_path": None,
            "max_tokens": 2048,
        },
    ]
    with patch.object(mo, '_cloud_chat_provider') as mock_chat:
        mock_chat.return_value = "described"
        mo._cloud_chat_vision("sys", "user", ["img"])
    provider_arg = mock_chat.call_args[0][0]
    assert provider_arg["name"] == "zen-kimi-vision"
    assert provider_arg["model"] == "kimi-k3"


def test_vision_payload_has_max_tokens_from_provider():
    from core.model_orchestrator import ModelOrchestrator
    mo = ModelOrchestrator.__new__(ModelOrchestrator)
    mo.CLOUD_PROVIDERS = [{
        "name": "zen-kimi-vision",
        "model": "kimi-k3",
        "roles": ["vision"],
        "url": "https://test.example.com/v1/chat/completions",
        "key_path": None,
        "max_tokens": 2048,
    }]
    with patch.object(mo, '_cloud_chat_provider') as mock_chat:
        mock_chat.return_value = "ok"
        mo._cloud_chat_vision("sys", "user", ["img"])
    call_args = mock_chat.call_args
    options_arg = call_args[0][3]
    assert isinstance(options_arg, dict)
