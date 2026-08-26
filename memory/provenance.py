VALID_SOURCES = {
    "TEST",
    "USER_STATEMENT",
    "SELF_OBSERVATION",
    "SELF_ACTION",
    "SHARED_EXPERIENCE",
    "EXTERNAL",
    "SYSTEM",
    "ACTION_CHOICE",
    "SELF_EXPERIENCE",
    "SELF_INTERPRETATION",
    "DECISION_PATTERN",
}


SOURCE_WEIGHTS = {
    "TEST": 0.0,
    "USER_STATEMENT": 0.45,
    "SELF_OBSERVATION": 0.8,
    "SELF_ACTION": 1.0,
    "SHARED_EXPERIENCE": 0.7,
    "EXTERNAL": 0.0,
    "SYSTEM": 0.0,
    "ACTION_CHOICE": 1.0,
    "SELF_EXPERIENCE": 1.0,
    "SELF_INTERPRETATION": 1.0,
    "DECISION_PATTERN": 1.0,
}


def validate_source(source: str) -> str:
    if source not in VALID_SOURCES:
        raise ValueError(
            f"Unknown evidence source: {source}"
        )

    return source


def source_weight(source: str) -> float:
    validate_source(source)
    return SOURCE_WEIGHTS[source]
