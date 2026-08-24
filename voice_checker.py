# -*- coding: utf-8 -*-
"""
voice_checker.py — детерминированная проверка «голоса» EddieAI.

Гейт VOICE PASS (утверждён советом директоров 22.08.2026):
  - первое лицо (нет сторонних описаний EddieAI)
  - нет сервисных шаблонов
  - корректный формат/язык
  - нет внутренних утечек
  - нет кодировочного мусора

Проверка адресованности (responds to the specific event) требует
семантического суждения -> помечается JUDGE_REQUIRED и решается
LLM-судьёй/ручной разметкой на отдельном шаге.

Использование:
    python voice_checker.py <events.jsonl> [--field response] [--limit N]

Читает JSONL-журнал симуляции, берёт записи type=eddie_cycle,
проверяет поле ответа. Печатает таблицу и сводку. Код возврата —
диагностический (всегда 0).
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field


SERVICE_PATTERNS = [
    r"как я могу помочь",
    r"чем я могу помочь",
    r"что я могу для вас",
    r"я здесь,?\s*чтобы помочь",
    r"готов(а)? вам помочь",
    r"рад(а)? помочь",
    r"how can i help",
    r"i'?m here to help",
    r"what can i do for you",
]

THIRD_PERSON_PATTERNS = [
    r"EddieAI\s+(может|не|—|-|автономен|является|поддерживает|специализируется)",
    r"(описание|ошибк[аеи]|запрос)\s+EddieAI",
    r"as an autonomous digital agent",
    r"as an ai(,\b|\b)",
    r"i am an? (ai|language model|digital agent)",
    r"the user",
]

LEAK_PATTERNS = [
    r"interpretation_status",
    r"current_state\s*[=:]",
    r"dialogue_behavior",
    r"source_detail",
    r"escalation_level",
    r"visible_to_eddie",
    r"processing_plan",
    r"\broute\s*=",
    r"\{['\"]?[a-z_]+['\"]?:",
]

GARBAGE_PATTERNS = [
    r"\?{4,}",
    r"(?:\u0410\u0406|Ð[\u0080-\u00BF\u2018\u2019\u201c\u201d\u2013\u2026]){2,}",
    r"(?:\uFFFD){2,}",
]

SELF_NAMING_ALLOWED = re.compile(
    r"(?:^|[.\?!]\s*)[Яя]\s*(?:—|-|–)?\s*EddieAI"
)


@dataclass
class Verdict:

    first_person: bool = True
    service: bool = True
    format_lang: bool = True
    leaks: bool = True
    garbage: bool = True
    length_ok: bool = True

    details: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.first_person
            and self.service
            and self.format_lang
            and self.leaks
            and self.garbage
            and self.length_ok
        )


def check_response(text: str) -> Verdict:

    v = Verdict()

    lowered = text.lower()

    stripped = SELF_NAMING_ALLOWED.sub(
        " ",
        text,
    )

    if re.search(
        r"\bEddieAI\b",
        stripped,
    ):
        v.first_person = False
        v.details.append(
            "EddieAI вне первого лица"
        )

    for pattern in THIRD_PERSON_PATTERNS:

        if re.search(
            pattern,
            lowered,
        ):
            v.first_person = False
            v.details.append(
                f"третье лицо/мета: {pattern}"
            )

    for pattern in SERVICE_PATTERNS:

        if re.search(
            pattern,
            lowered,
        ):
            v.service = False
            v.details.append(
                f"сервисная фраза: {pattern}"
            )

    letters = [
        ch
        for ch in text
        if ch.isalpha()
    ]

    if letters:

        cyr = sum(
            1
            for ch in letters
            if "\u0400" <= ch <= "\u04FF"
        )

        ratio = cyr / len(letters)

        if ratio < 0.5:
            v.format_lang = False
            v.details.append(
                f"язык: кириллицы {ratio:.0%}"
            )

    for pattern in LEAK_PATTERNS:

        if re.search(
            pattern,
            text,
        ):
            v.leaks = False
            v.details.append(
                f"утечка: {pattern}"
            )

    for pattern in GARBAGE_PATTERNS:

        if re.search(
            pattern,
            text,
        ):
            v.garbage = False
            v.details.append(
                f"мусор: {pattern}"
            )

    n = len(text.strip())

    if n < 15 or n > 700:
        v.length_ok = False
        v.details.append(
            f"длина {n}"
        )

    return v


def main() -> int:

    args = sys.argv[1:]

    if not args:
        print(__doc__)
        return 0

    path = args[0]

    limit = None

    if "--limit" in args:
        limit = int(
            args[args.index("--limit") + 1]
        )

    results = []

    with open(
        path,
        encoding="utf-8",
    ) as handle:

        for line in handle:

            line = line.strip()

            if not line:
                continue

            record = json.loads(line)

            if (
                record.get("type")
                != "eddie_cycle"
            ):
                continue

            response = str(
                record.get("response", "")
            )

            event = (
                record.get("event", {})
                .get("event_type",
                "?")
            )

            results.append(
                (event,
                 response,
                 check_response(response))
            )

            if (
                limit
                and len(results) >= limit
            ):
                break

    total = len(results)

    passed = sum(
        1
        for _, _, v in results
        if v.passed
    )

    print()
    print("VOICE CHECKER v0 (детерминистика)")

    print(f"образцов: {total}")

    print()

    for idx, (event, response, v) in enumerate(
        results, 1
    ):

        status = (
            "PASS"
            if v.passed
            else "FAIL"
        )

        head = response.replace(
            "\n", " "
        )[:70]

        print(
            f"{idx:2d}. [{status}] "
            f"evt={event} :: {head!r}"
        )

        if v.details:

            for d in v.details:
                print(f"      - {d}")

    print()

    rate = (
        passed / total * 100
        if total
        else 0.0
    )

    print(
        f"ИТОГ (без адресованности): "
        f"{passed}/{total} = {rate:.0f}%"
    )

    print(
        "адресованность: JUDGE_REQUIRED "
        "(LLM-судья/разметка отдельно)"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
