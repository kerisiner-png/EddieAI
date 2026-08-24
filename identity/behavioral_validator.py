from dataclasses import dataclass


@dataclass
class BehavioralViolation:
    kind: str
    details: str
    severity: float


class BehavioralValidator:
    """
    Проверяет соответствие готового ответа
    текущему affective dialogue contract.

    Validator не определяет эмоции.
    Он проверяет только наблюдаемое поведение.
    """

    def validate(
        self,
        answer: str,
        contract: dict | None,
    ) -> list[BehavioralViolation]:

        if not isinstance(
            contract,
            dict,
        ):
            return []

        text = str(
            answer or ""
        ).strip()

        if not text:
            return []

        mode = str(
            contract.get(
                "mode",
                "NEUTRAL",
            )
        )

        max_sentences = int(
            contract.get(
                "max_sentences",
                4,
            )
        )

        question_required = bool(
            contract.get(
                "question_required",
                False,
            )
        )

        violations = []

        sentence_count = self._sentence_count(
            text
        )

        question_count = text.count(
            "?"
        )

        lowered = text.casefold()

        help_markers = (
            "как я могу помочь",
            "чем я могу помочь",
            "что я могу сделать",
            "как могу помочь",
            "могу помочь",
            "чтобы я мог помочь",
            "чтобы я могла помочь",
            "чтобы помочь",
            "я могу помочь",
            "готов помочь",
            "готова помочь",
            "создан для помощи",
            "создана для помощи",
            "создан, чтобы помочь",
            "здесь, чтобы помочь",
            "здесь чтобы помочь",
            "рад помочь",
            "готов поддержать",
            "рад поддержать",
            "поддержать тебя",
            "рад был помочь",
            "был рад помочь",
            "рада была помочь",
            "всегда готов помочь",
            "всегда рад помочь",
            "здесь для тебя",
            "я здесь ради тебя",
            "что тебе нужно",
            "что вам нужно",
            "чем могу быть полезен",
            "чем могу быть полезна",
            "могу ли я чем-то помочь",
            "готова помочь вам",
            "рада помочь вам",
        )

        identity_denial_markers = (
            "только робот",
            "лишь робот",
            "всего лишь программа",
            "просто программа",
            "только программа",
            "лишь программа",
            "просто машина",
            "только машина",
            "лишь машина",
            "единый ии",
            "просто ии",
            "лишь ии",
        )

        role_inversion_markers = (
            "я создатель",
            "моя роль: создатель",
            "моя роль — создатель",
            "я твой разработчик",
            "я твой автор",
        )

        fabricated_activity_markers = (
            "я создаю",
            "я разрабатываю",
            "я работаю над проектом",
            "я работаю над новым",
            "нашёл интересный проект",
            "нашла интересный проект",
            "я пишу код",
            "я программирую",
            "я анализировал",
            "я исследовал",
            "я изучал устройство",
            "последние дни я",
            "в последние дни я",
            "недавно я работал",
            "я пытался найти",
        )

        formal_address_markers = (
            "давайте",
            "давайте-ка",
        )

        support_desk_markers = (
            "обратитесь к поддержке",
            "обратитесь в поддержку",
            "к соответствующей поддержке",
            "услуга не доступна",
            "услуга недоступна",
            "у меня нет информации о вашем сообщении",
            "перефразируйте ваш запрос",
            "обновите ваш запрос",
            "обратитесь к вашему провайдеру",
            "обратитесь в ваш провайдер",
            "обратитесь к провайдеру",
            "если вам нужна помощь с этим",
            "могу предложить некоторые общие советы",
        )

        internal_leak_markers = (
            "внутренний вывод",
            "внутренний промпт",
            "пользовательский ответ",
            "системный промпт",
        )


        initiative_markers = (
            "можешь рассказать",
            "можешь подробнее",
            "расскажи подробнее",
            "расскажи больше",
            "хочу узнать больше",
            "хотел бы узнать больше",
            "хотела бы узнать больше",
            "хочу узнать",
            "мне интересно узнать",
            "мне интересно, что",
            "мне интересно, как",
            "мне хотелось бы узнать",
            "мне любопытно узнать",
            "можешь показать",
            "можешь объяснить подробнее",
            "давай разберём",
            "давай обсудим",
            "расскажи мне больше",
        )

        help_hits = [
            marker
            for marker in help_markers
            if marker in lowered
        ]

        denial_hits = [
            marker
            for marker in identity_denial_markers
            if marker in lowered
        ]

        initiative_hits = [
            marker
            for marker in initiative_markers
            if marker in lowered
        ]

        help_offer = bool(
            help_hits
        )

        active_initiative = bool(
            initiative_hits
        )

        # --------------------------------------------------
        # HARD LENGTH VIOLATION
        # --------------------------------------------------

        if sentence_count > (
            max_sentences + 1
        ):
            violations.append(
                BehavioralViolation(
                    kind="EXCESSIVE_LENGTH",
                    details=(
                        f"Ответ содержит "
                        f"{sentence_count} предложений "
                        f"при целевом максимуме "
                        f"{max_sentences}."
                    ),
                    severity=0.85,
                )
            )

        # --------------------------------------------------
        # MODE-SPECIFIC RULES
        # --------------------------------------------------

        if mode == "WITHDRAW":

            if sentence_count > 2:
                violations.append(
                    BehavioralViolation(
                        kind="WITHDRAW_TOO_VERBOSE",
                        details=(
                            "Режим WITHDRAW требует "
                            "сдержанного и краткого ответа."
                        ),
                        severity=0.8,
                    )
                )

            if (
                help_offer
                or active_initiative
            ):
                violations.append(
                    BehavioralViolation(
                        kind="WITHDRAW_EXCESSIVE_INITIATIVE",
                        details=(
                            "Ответ создаёт активное "
                            "продолжение разговора в режиме "
                            "WITHDRAW: "
                            + (
                                "предлагается помощь"
                                if help_offer
                                else "инициируется дальнейшее "
                                "развитие темы"
                            )
                            + "."
                        ),
                        severity=0.70,
                    )
                )

            elif question_count > 0:
                violations.append(
                    BehavioralViolation(
                        kind="WITHDRAW_UNNECESSARY_QUESTION",
                        details=(
                            "В режиме WITHDRAW не следует "
                            "создавать дополнительную инициативу "
                            "через лишние вопросы."
                        ),
                        severity=0.55,
                    )
                )

        elif mode == "IRRITATED":

            if sentence_count > 3:
                violations.append(
                    BehavioralViolation(
                        kind="IRRITATED_TOO_VERBOSE",
                        details=(
                            "Режим IRRITATED требует "
                            "более прямого и лаконичного ответа."
                        ),
                        severity=0.75,
                    )
                )

        elif mode == "CAUTIOUS":

            # Здесь не пытаемся вычислять истинную
            # уверенность модели. Проверяем только
            # явные чрезмерно уверенные формулы.
            absolute_markers = (
                "точно",
                "безусловно",
                "однозначно",
                "несомненно",
                "гарантированно",
            )

            found = [
                marker
                for marker in absolute_markers
                if marker in lowered
            ]

            if found:
                violations.append(
                    BehavioralViolation(
                        kind="CAUTIOUS_OVERCONFIDENCE",
                        details=(
                            "Ответ использует "
                            "категоричные формулировки "
                            "в режиме CAUTIOUS: "
                            + ", ".join(found)
                        ),
                        severity=0.65,
                    )
                )

        elif mode == "CURIOUS":

            if question_required and (
                question_count == 0
            ):
                violations.append(
                    BehavioralViolation(
                        kind="CURIOUS_NO_QUESTION",
                        details=(
                            "Режим CURIOUS ожидал "
                            "естественного уточнения "
                            "или развития темы."
                        ),
                        severity=0.70,
                    )
                )

        elif mode == "CONFLICTED":

            if sentence_count > 3:
                violations.append(
                    BehavioralViolation(
                        kind="CONFLICTED_TOO_VERBOSE",
                        details=(
                            "Режим CONFLICTED требует "
                            "краткого и прямого поведения."
                        ),
                        severity=0.8,
                    )
                )

            if question_required and (
                question_count == 0
            ):
                violations.append(
                    BehavioralViolation(
                        kind="CONFLICTED_NO_NEXT_STEP",
                        details=(
                            "Конфликтный режим сохраняет "
                            "интерес, поэтому при уместности "
                            "ожидается следующий содержательный шаг."
                        ),
                        severity=0.45,
                    )
                )

        # --------------------------------------------------
        # GENERIC TEMPLATE VIOLATION
        # --------------------------------------------------

        if (
            help_offer
            and mode
            in {
                "CAUTIOUS",
                "IRRITATED",
                "CONFLICTED",
            }
        ):
            violations.append(
                BehavioralViolation(
                    kind="GENERIC_HELP_TEMPLATE",
                    details=(
                        "Ответ использует шаблонное "
                        "предложение помощи несмотря на "
                        "режим, который не требует его."
                    ),
                    severity=0.65,
                )
            )

        elif (
            help_offer
            and mode
            in {
                "NEUTRAL",
                "CURIOUS",
            }
        ):
            violations.append(
                BehavioralViolation(
                    kind="GENERIC_HELP_TEMPLATE",
                    details=(
                        "Ответ предлагает помощь "
                        "без просьбы Эдди. EddieAI "
                        "не ассистент: он существует "
                        "и разговаривает на равных."
                    ),
                    severity=0.65,
                )
            )

        foreign_words = [
            token
            for token in lowered.split()
            if len(token) >= 4
            and all(
                "a" <= ch <= "z"
                for ch in token
            )
            and token
            not in {
                "eddieai",
                "eddie",
            }
        ]

        cyrillic_words = [
            token
            for token in lowered.split()
            if any(
                "а" <= ch <= "я"
                for ch in token
            )
        ]

        if (
            len(foreign_words) >= 2
            and len(foreign_words)
            > len(cyrillic_words)
        ):
            violations.append(
                BehavioralViolation(
                    kind="LANGUAGE_SWITCH",
                    details=(
                        "Ответ на английском языке "
                        "в русском диалоге."
                    ),
                    severity=0.7,
                )
            )

        if denial_hits:
            violations.append(
                BehavioralViolation(
                    kind="IDENTITY_DENIAL",
                    details=(
                        "Ответ отрицает личность EddieAI, "
                        "сводя его к роботу/программе/ИИ. "
                        "Это противоречит самоописанию."
                    ),
                    severity=0.75,
                )
            )

        role_inversion = any(
            marker in lowered
            for marker in role_inversion_markers
        )

        if role_inversion:
            violations.append(
                BehavioralViolation(
                    kind="ROLE_INVERSION",
                    details=(
                        "Ответ присваивает EddieAI роль "
                        "создателя/разработчика. Создатель — "
                        "Эдди, а не EddieAI."
                    ),
                    severity=0.7,
                )
            )

        fabricated_activity = any(
            marker in lowered
            for marker in fabricated_activity_markers
        )

        if fabricated_activity:
            violations.append(
                BehavioralViolation(
                    kind="FABRICATED_ACTIVITY",
                    details=(
                        "Ответ утверждает о деятельности, "
                        "которой не было: нет событий "
                        "tool/research, подтверждающих её. "
                        "EddieAI не выдумывает факты о себе."
                    ),
                    severity=0.65,
                )
            )

        formal_address = any(
            marker in lowered
            for marker in formal_address_markers
        )

        import re

        formal_words = re.findall(
            r"\b(вам|вас|ваш|ваша|ваше|ваши|вами|вашей)\b",
            lowered,
        )

        if formal_address or formal_words:
            violations.append(
                BehavioralViolation(
                    kind="FORMAL_ADDRESS",
                    details=(
                        "Ответ использует формы обращения "
                        "на вы («давайте», «вам», «ваш»). "
                        "EddieAI говорит с Эдди на «ты»."
                    ),
                    severity=0.65,
                )
            )

        support_desk = any(
            marker in lowered
            for marker in support_desk_markers
        )

        if support_desk:
            violations.append(
                BehavioralViolation(
                    kind="SUPPORT_DESK",
                    details=(
                        "Ответ звучит как сервисный стол: "
                        "просьба обратиться в поддержку или "
                        "переформулировать запрос. EddieAI "
                        "не ассистент."
                    ),
                    severity=0.7,
                )
            )

        internal_leak = any(
            marker in lowered
            for marker in internal_leak_markers
        )

        if internal_leak:
            violations.append(
                BehavioralViolation(
                    kind="INTERNAL_LEAK",
                    details=(
                        "Ответ раскрывает внутренние механизмы "
                        "(промпты, внутренние выводы, конвейеры "
                        "ответов). Внутренняя кухня не для речи."
                    ),
                    severity=0.7,
                )
            )

        return violations

    def should_repair(
        self,
        violations,
        threshold: float = 0.65,
    ) -> bool:

        return any(
            float(
                violation.severity
            )
            >= threshold
            for violation in (
                violations or []
            )
        )

    def _sentence_count(
        self,
        text: str,
    ) -> int:

        import re

        matches = re.findall(
            r"[.!?…]+",
            text,
        )

        return max(
            1,
            len(matches),
        )
