import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.model_orchestrator import ModelOrchestrator


def _by_name(name):
    for provider in ModelOrchestrator.CLOUD_PROVIDERS:
        if provider.get("name") == name:
            return provider
    return None


def test_reflection_role_exists():
    reflection = [
        provider
        for provider in ModelOrchestrator.CLOUD_PROVIDERS
        if "reflection" in (
            provider.get("roles") or []
        )
    ]
    assert reflection, "роль reflection должна быть назначена провайдеру"


def test_reflection_routes_to_flash():
    reflection = [
        provider
        for provider in ModelOrchestrator.CLOUD_PROVIDERS
        if "reflection" in (
            provider.get("roles") or []
        )
    ]
    for provider in reflection:
        assert provider["model"] == "deepseek-v4-flash"
        assert provider["name"] == "zen-deepseek-flash"


def test_pro_has_no_reflection_role():
    pro = _by_name("zen-deepseek-pro")
    assert pro is not None
    assert "reflection" not in (
        pro.get("roles") or []
    )
    assert "deep" in (pro.get("roles") or [])


def test_flash_keeps_conversation_roles():
    flash = _by_name("zen-deepseek-flash")
    assert flash is not None
    roles = flash.get("roles") or []
    for role in ("conversation", "fallback", "plan"):
        assert role in roles


def test_no_duplicate_role_owners():
    owners = {}
    for provider in ModelOrchestrator.CLOUD_PROVIDERS:
        for role in (provider.get("roles") or []):
            owners.setdefault(role, set()).add(
                provider["name"]
            )
    assert len(owners.get("reflection", set())) == 1


if __name__ == "__main__":
    test_reflection_role_exists()
    test_reflection_routes_to_flash()
    test_pro_has_no_reflection_role()
    test_flash_keeps_conversation_roles()
    test_no_duplicate_role_owners()
    print("ALL OK")