from core.agent import Agent


tests = [
    "У тебя есть интерес к астрофизике?",
    "У тебя есть любимые сериалы?",
]

a = Agent()
a.structured_claim_pipeline = True

for user_message in tests:

    print()
    print("=" * 80)
    print("USER:", user_message)

    route = (
        "SELF_QUERY"
        if any(
            marker in user_message.casefold()
            for marker in (
                "у тебя",
                "ты ",
                "тво",
                "ты?",
            )
        )
        else "USER_QUERY"
    )

    system_prompt = a.build_system_prompt(
        route=route,
        language="ru",
    )

    packet = a._generate_response_packet(
        system_prompt=system_prompt,
        user_prompt=user_message,
        task="conversation",
        context="",
        fast=True,
    )

    print("STRUCTURED:", packet.get("structured"))
    print("FALLBACK:", packet.get("fallback"))
    print("FALLBACK_REASON:")
    print(packet.get("fallback_reason"))

    print()
    print("ANSWER:")
    print(packet.get("answer"))

    print()
    print("CLAIMS:")
    for claim in packet.get(
        "claims",
        [],
    ):
        print(claim)

a.close()
