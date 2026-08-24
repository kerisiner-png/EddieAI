def build_claim_audit_schema() -> dict:
    predicate_names = sorted(
        {
            "has_interest",
            "has_preference",
            "has_habit",
            "has_belief",
            "has_goal",
            "has_value",
            "identity_is",
            "watched",
            "used",
            "experienced",
            "has_capability",
            "has_access",
            "relationship_with",
            "subjective_consciousness",
            "subjective_feelings",
            "autonomous_agency",
        }
    )

    return {
        "type": "object",
        "required": [
            "claims",
        ],
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "subject",
                        "predicate",
                        "value",
                        "polarity",
                    ],
                    "properties": {
                        "subject": {
                            "type": [
                                "string",
                                "null",
                            ],
                        },
                        "predicate": {
                            "type": "string",
                            "enum": predicate_names,
                        },
                        "value": {
                            "type": [
                                "string",
                                "null",
                            ],
                        },
                        "polarity": {
                            "type": "string",
                            "enum": [
                                "POSITIVE",
                                "NEGATIVE",
                                "UNKNOWN",
                            ],
                        },
                        "certainty": {
                            "type": "string",
                            "enum": [
                                "HIGH",
                                "MEDIUM",
                                "LOW",
                                "UNKNOWN",
                            ],
                        },
                        "temporal_scope": {
                            "type": "string",
                            "enum": [
                                "PAST",
                                "CURRENT",
                                "FUTURE",
                                "DURATIVE",
                                "UNKNOWN",
                            ],
                        },
                    },
                },
            },
        },
    }


CLAIM_AUDIT_SCHEMA = (
    build_claim_audit_schema()
)
