import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.self_claim_validator import SelfClaimValidator
from core.claim_engine import Claim, ClaimEngine


class _FakeState:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


class _FakeAgent:
    def __init__(self, data):
        self.self_state = _FakeState(data)
        self.capabilities = []


def test_validator_supports_dict_preference():
    agent = _FakeAgent({
        "preferences": [
            {
                "label": "в перерыве читать книгу",
                "context": "break",
                "method": "read",
                "share": 0.75,
                "total": 4,
            }
        ]
    })
    validator = SelfClaimValidator(agent)
    result = validator.validate(
        property_name="preference",
        text="я предпочитаю в перерыве читать книгу",
    )
    assert result.status == "SUPPORTED"
    assert result.value == "в перерыве читать книгу"


def test_validator_dict_without_label_no_crash():
    agent = _FakeAgent({
        "preferences": [
            {
                "label": "",
                "context": "break",
                "method": "read",
            }
        ]
    })
    validator = SelfClaimValidator(agent)
    # Без label нет читаемой строки — validate не падает,
    # возвращает детерминированный статус (не сматчится).
    result = validator.validate(
        property_name="preference",
        text="предпочитаю читать",
    )
    assert result.status in {
        "SUPPORTED",
        "UNSUPPORTED",
    }


def test_validator_misses_unrelated():
    agent = _FakeAgent({
        "preferences": [
            {
                "label": "смотреть сериалы",
                "context": "evening",
                "method": "watch",
                "share": 0.8,
                "total": 5,
            }
        ]
    })
    validator = SelfClaimValidator(agent)
    result = validator.validate(
        property_name="preference",
        text="предпочитаю читать газеты",
    )
    assert result.status == "UNSUPPORTED"


def test_claim_engine_supports_dict_preference():
    def provider():
        return {
            "preferences": [
                {
                    "label": "в перерыве читать книгу",
                    "context": "break",
                    "method": "read",
                    "share": 0.75,
                    "total": 4,
                }
            ]
        }

    engine = ClaimEngine(
        self_state_provider=provider,
    )
    claim = Claim(
        owner="SELF",
        predicate="has_preference",
        value="в перерыве читать книгу",
        polarity="POSITIVE",
        certainty="MEDIUM",
        temporal_scope="CURRENT",
        text="я предпочитаю в перерыве читать книгу",
    )
    eval_res = engine.predicate_registry.evaluate(
        predicate=claim.predicate,
        value=claim.value,
        polarity=claim.polarity,
        claim=claim,
    )
    assert eval_res["status"] == "SUPPORTED"


def test_claim_engine_matches_by_method():
    def provider():
        return {
            "preferences": [
                {
                    "label": "в перерыве читать книгу",
                    "context": "break",
                    "method": "read",
                }
            ]
        }

    engine = ClaimEngine(
        self_state_provider=provider,
    )
    claim = Claim(
        owner="SELF",
        predicate="has_preference",
        value="читать книгу",
        polarity="POSITIVE",
        certainty="MEDIUM",
        temporal_scope="CURRENT",
        text="я предпочитаю читать книгу",
    )
    eval_res = engine.predicate_registry.evaluate(
        predicate=claim.predicate,
        value=claim.value,
        polarity=claim.polarity,
        claim=claim,
    )
    assert eval_res["status"] == "SUPPORTED"


def test_claim_engine_repr_not_leaked():
    def provider():
        return {
            "preferences": [
                {
                    "label": "в перерыве читать книгу",
                    "context": "break",
                    "method": "read",
                    "share": 0.75,
                    "total": 4,
                }
            ]
        }

    engine = ClaimEngine(
        self_state_provider=provider,
    )
    claim = Claim(
        owner="SELF",
        predicate="has_preference",
        value="читать книгу",
        polarity="POSITIVE",
        certainty="MEDIUM",
        temporal_scope="CURRENT",
        text="я предпочитаю читать книгу",
    )
    eval_res = engine.predicate_registry.evaluate(
        predicate=claim.predicate,
        value=claim.value,
        polarity=claim.polarity,
        claim=claim,
    )
    # Если бы в сравнение уходил repr(dict) — матча не было бы вовсе.
    assert eval_res["status"] == "SUPPORTED"


if __name__ == "__main__":
    test_validator_supports_dict_preference()
    test_validator_dict_without_label_no_crash()
    test_validator_misses_unrelated()
    test_claim_engine_supports_dict_preference()
    test_claim_engine_matches_by_method()
    test_claim_engine_repr_not_leaked()
    print("ALL OK")
