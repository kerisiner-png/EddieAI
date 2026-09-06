from core.model_orchestrator import ModelOrchestrator


def test_ollama_cloud_first_for_conversation():
    matching = [
        p
        for p in ModelOrchestrator.CLOUD_PROVIDERS
        if "conversation" in (p.get("roles") or [])
    ]
    assert matching[0]["name"] == (
        "ollama-gpt-oss"
    )
    assert matching[1]["name"] == (
        "ollama-gemma"
    )


def test_ollama_cloud_cover_main_roles():
    ollama_roles = []

    for p in ModelOrchestrator.CLOUD_PROVIDERS:
        if p["name"].startswith("ollama-"):
            ollama_roles.extend(p["roles"])

    for role in (
        "conversation",
        "fallback",
        "plan",
        "reflection",
        "affective",
    ):
        assert role in ollama_roles, role


def test_ollama_gpt_oss_reasoning_low():
    p = next(
        p
        for p in ModelOrchestrator.CLOUD_PROVIDERS
        if p["name"] == "ollama-gpt-oss"
    )
    assert p["extra_payload"] == {
        "reasoning_effort": "low"
    }


if __name__ == "__main__":
    test_ollama_cloud_first_for_conversation()
    test_ollama_cloud_cover_main_roles()
    test_ollama_gpt_oss_reasoning_low()
    print("ALL OK")
