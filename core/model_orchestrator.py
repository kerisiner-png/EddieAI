from dataclasses import dataclass
from typing import Any

import json
import time
import urllib.request
from pathlib import Path

from ollama import Client, chat, list as ollama_list


@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: str
    reasoning: float
    context: float
    speed: float
    num_ctx: int
    num_predict: int
    temperature: float


@dataclass(frozen=True)
class TaskProfile:
    complexity: float
    reasoning: float
    context_need: float
    speed_need: float
    risk: float


@dataclass(frozen=True)
class ModelDecision:
    model: str
    provider: str
    score: float
    reason: str


class ModelOrchestrator:
    """
    Сам выбирает наиболее подходящую доступную модель
    для конкретной когнитивной задачи.

    Сейчас доступны только локальные модели:
        qwen3.5:4b
        phi4-mini
    """

    MISTRAL_KEY_PATH = (
        Path.home() / ".eddieai_secrets" / "mistral.key"
    )
    MISTRAL_MODEL = "mistral-small-latest"

    def _cloud_chat(self, *, system, user, options):
        if not self.MISTRAL_KEY_PATH.exists():
            return None
        try:
            api_key = self.MISTRAL_KEY_PATH.read_text(
                encoding="utf-8"
            ).strip()
            payload = {
                "model": self.MISTRAL_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            system
                            + "\nНикогда не используй эмодзи."
                        ),
                    },
                    {"role": "user", "content": user},
                ],
                "temperature": options.get("temperature", 0.7),
                "max_tokens": min(
                    options.get("num_predict", 300), 512
                ),
            }
            req = urllib.request.Request(
                "https://api.mistral.ai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return content.strip() if content else None
        except Exception:
            return None

    def __init__(
        self,
        fallback_on_error: bool = True,
    ):
        self.fallback_on_error = fallback_on_error

        self.llm_client = Client(
            timeout=600.0,
        )

        self.models = [
            ModelProfile(
                name="qwen3.5:4b",
                provider="ollama-local",
                reasoning=0.60,
                context=0.65,
                speed=0.95,
                num_ctx=4096,
                num_predict=512,
                temperature=0.4,
            ),
            ModelProfile(
                name="phi4-mini:latest",
                provider="ollama-local",
                reasoning=0.55,
                context=0.55,
                speed=0.85,
                num_ctx=2048,
                num_predict=384,
                temperature=0.4,
            ),
        ]

    # =========================================================
    # AVAILABLE MODELS
    # =========================================================

    def available_models(self) -> list[str]:
        try:
            response = ollama_list()

            return [
                item.model
                for item in response.models
            ]

        except Exception:
            return []

    # =========================================================
    # TASK PROFILING
    # =========================================================

    def profile_task(
        self,
        task: str,
        context: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> TaskProfile:

        metadata = metadata or {}

        text = (
            f"{task}\n"
            f"{context}"
        ).lower()

        complexity = 0.30
        reasoning = 0.30
        context_need = 0.30
        speed_need = 0.50
        risk = 0.20

        reasoning_words = (
            "почему",
            "проанализируй",
            "сравни",
            "выведи",
            "объясни",
            "спланируй",
            "придумай",
            "рассмотри",
            "противореч",
            "причин",
            "стратег",
            "архитектур",
            "рефлек",
            "belief",
            "reflection",
            "reason",
            "analyze",
            "analysis",
            "plan",
            "design",
        )

        if any(
            word in text
            for word in reasoning_words
        ):
            reasoning += 0.35
            complexity += 0.25

        complex_words = (
            "несколько",
            "многоэтап",
            "глубоко",
            "подробно",
            "систем",
            "архитектур",
            "долгосроч",
            "саморазвит",
            "самомодел",
            "world model",
            "self model",
            "multi-step",
        )

        if any(
            word in text
            for word in complex_words
        ):
            complexity += 0.30
            reasoning += 0.20
            context_need += 0.15

        if len(context) > 2000:
            context_need += 0.30

        if len(context) > 6000:
            context_need += 0.20

        risk_words = (
            "изменить собственный код",
            "изменить архитектуру",
            "самоизмен",
            "удалить",
            "заменить",
            "rollback",
            "identity",
            "личность",
            "belief",
            "цель",
            "goal",
            "self",
        )

        if any(
            word in text
            for word in risk_words
        ):
            risk += 0.50
            reasoning += 0.25
            complexity += 0.20

        if metadata.get("high_reasoning"):
            reasoning += 0.40

        if metadata.get("high_risk"):
            risk += 0.40

        if metadata.get("fast"):
            speed_need += 0.40

        if metadata.get("long_context"):
            context_need += 0.40

        return TaskProfile(
            complexity=min(complexity, 1.0),
            reasoning=min(reasoning, 1.0),
            context_need=min(context_need, 1.0),
            speed_need=min(speed_need, 1.0),
            risk=min(risk, 1.0),
        )

    # =========================================================
    # MODEL SELECTION
    # =========================================================

    def select_model(
        self,
        profile: TaskProfile,
    ) -> ModelDecision:

        phi = next(
            (
                model
                for model in self.models
                if model.name == "phi4-mini:latest"
            ),
            None,
        )

        qwen = next(
            (
                model
                for model in self.models
                if model.name == "qwen3.5:4b"
            ),
            None,
        )

        if phi is None and qwen is None:
            raise RuntimeError(
                "У EddieAI нет доступных локальных моделей."
            )

        # -----------------------------------------------------
        # HEAVY TASK DETECTION
        # -----------------------------------------------------
        if profile.speed_need >= 0.80 and profile.complexity < 0.70:
            if phi is not None:
                return ModelDecision(
                    model=phi.name,
                    provider=phi.provider,
                    score=1.0,
                    reason="Fast conversational path.",
                )


        qwen_required = (
            profile.reasoning >= 0.70
            or profile.complexity >= 0.70
            or profile.context_need >= 0.75
            or profile.risk >= 0.65
        )

        # -----------------------------------------------------
        # HEAVY TASK
        # -----------------------------------------------------

        if qwen_required and qwen is not None:
            return ModelDecision(
                model=qwen.name,
                provider=qwen.provider,
                score=1.0,
                reason=(
                    "Тяжёлая задача: "
                    f"reasoning={profile.reasoning:.2f}, "
                    f"complexity={profile.complexity:.2f}, "
                    f"context={profile.context_need:.2f}, "
                    f"risk={profile.risk:.2f}. "
                    "Выбран qwen3.5:4b."
                ),
            )

        # -----------------------------------------------------
        # FAST TASK
        # -----------------------------------------------------

        if phi is not None:
            return ModelDecision(
                model=phi.name,
                provider=phi.provider,
                score=1.0,
                reason=(
                    "Быстрая задача: "
                    f"reasoning={profile.reasoning:.2f}, "
                    f"complexity={profile.complexity:.2f}, "
                    f"context={profile.context_need:.2f}, "
                    f"risk={profile.risk:.2f}. "
                    "Выбран phi4-mini."
                ),
            )

        # -----------------------------------------------------
        # PHI UNAVAILABLE
        # -----------------------------------------------------

        return ModelDecision(
            model=qwen.name,
            provider=qwen.provider,
            score=0.5,
            reason=(
                "phi4-mini недоступна. "
                "Используется qwen3.5:4b."
            ),
        )
    # =========================================================
    # MODEL WARM-UP
    # =========================================================

    def warm_up_models(
        self,
        *,
        models: list[str] | None = None,
        enabled: bool = True,
    ) -> dict[str, float | str]:

        from time import perf_counter

        if not enabled:
            print(
                "Модели не прогреваются: "
                "загрузятся при первом запросе."
            )
            return {}

        targets = (
            models
            if models is not None
            else [
                "phi4-mini:latest",
                "qwen3.5:4b",
            ]
        )

        results: dict[str, float | str] = {}

        print()
        print("=" * 70)
        print("EDDIEAI MODEL WARM-UP")
        print("=" * 70)

        for model_name in targets:
            started = perf_counter()

            try:
                self.llm_client.chat(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Initialize EddieAI runtime.",
                        },
                        {
                            "role": "user",
                            "content": "ping",
                        },
                    ],
                    options={
                        "num_ctx": (
                            2048
                            if model_name == "phi4-mini:latest"
                            else 4096
                        ),
                        "num_predict": 1,
                        "temperature": 0.0,
                    },
                    keep_alive="3m",
                    think=False,
                )

                elapsed = (
                    perf_counter()
                    - started
                )

                results[model_name] = elapsed

                print(
                    f"{model_name}: READY "
                    f"({elapsed:.2f} sec)"
                )

            except Exception as exc:
                elapsed = (
                    perf_counter()
                    - started
                )

                results[model_name] = (
                    f"ERROR: {exc}"
                )

                print(
                    f"{model_name}: ERROR "
                    f"after {elapsed:.2f} sec"
                )
                print(
                    str(exc)
                )

        print("=" * 70)

        return results

    # =========================================================
    # EXECUTION
    # =========================================================

    def execute(
        self,
        *,
        task: str,
        system: str,
        user: str,
        context: str = "",
        metadata: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        response_format: Any | None = None,
    ) -> dict[str, Any]:

        profile = self.profile_task(
            task=task,
            context=context,
            metadata=metadata,
        )

        # Fast conversational requests prefer the cloud mouth,
        # local qwen stays as automatic fallback.
        if metadata and metadata.get("fast", False):
            cloud_content = self._cloud_chat(
                system=system,
                user=user,
                options=options or {},
            )
            if cloud_content is not None:
                return {
                    "status": "OK",
                    "content": cloud_content,
                    "model": self.MISTRAL_MODEL,
                }

            qwen = next(
                (
                    item
                    for item in self.models
                    if item.name == "qwen3.5:4b"
                ),
                None,
            )

            if qwen is not None:
                decision = ModelDecision(
                    model=qwen.name,
                    provider=qwen.provider,
                    score=1.0,
                    reason="Explicit fast conversation path.",
                )
            else:
                decision = self.select_model(profile)
        else:
            decision = self.select_model(profile)

        model = next(
            item
            for item in self.models
            if item.name == decision.model
        )

        # -----------------------------------------------------
        # RESOURCE POLICY
        # -----------------------------------------------------

        is_fast = (
            metadata is not None
            and metadata.get("fast", False)
        )

        if model.name == "phi4-mini:latest":
            default_num_predict = (
                128 if is_fast else 256
            )
            keep_alive = "3m"

        elif model.name == "qwen3.5:4b":
            default_num_predict = 256
            keep_alive = "3m"

        else:
            default_num_predict = 256
            keep_alive = 0

        merged_options = {
            "num_ctx": (
                2048
                if is_fast
                else model.num_ctx
            ),
            "num_predict": default_num_predict,
            "temperature": model.temperature,
        }

        if options:
            merged_options.update(options)

        messages = [
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": user,
            },
        ]

        try:
            chat_kwargs = {
                "model": model.name,
                "messages": messages,
                "options": merged_options,
                "keep_alive": keep_alive,
                "think": False,
            }

            if response_format is not None:
                chat_kwargs["format"] = (
                    response_format
                )

            response = self.llm_client.chat(
                **chat_kwargs
            )

            content = (
                response["message"]["content"]
                .strip()
            )

            return {
                "status": "OK",
                "content": content,
                "model": model.name,
                "provider": model.provider,
                "selection": {
                    "score": decision.score,
                    "reason": decision.reason,
                },
                "task_profile": {
                    "complexity": profile.complexity,
                    "reasoning": profile.reasoning,
                    "context_need": profile.context_need,
                    "speed_need": profile.speed_need,
                    "risk": profile.risk,
                },
                "fallback": False,
            }

        except Exception as exc:

            if not self.fallback_on_error:
                raise

            fallback = next(
                (
                    item
                    for item in self.models
                    if item.name == "phi4-mini:latest"
                    and item.name != model.name
                ),
                None,
            )

            if fallback is None:
                raise

            fallback_kwargs = {
                "model": fallback.name,
                "messages": messages,
                "options": {
                    "num_ctx": fallback.num_ctx,
                    "num_predict": 128,
                    "temperature": fallback.temperature,
                },
                "keep_alive": "3m",
            }

            if response_format is not None:
                fallback_kwargs["format"] = (
                    response_format
                )

            response = self.llm_client.chat(
                **fallback_kwargs
            )

            content = (
                response["message"]["content"]
                .strip()
            )

            return {
                "status": "OK",
                "content": content,
                "model": fallback.name,
                "provider": fallback.provider,
                "selection": {
                    "score": decision.score,
                    "reason": decision.reason,
                },
                "task_profile": {
                    "complexity": profile.complexity,
                    "reasoning": profile.reasoning,
                    "context_need": profile.context_need,
                    "speed_need": profile.speed_need,
                    "risk": profile.risk,
                },
                "fallback": True,
                "fallback_reason": str(exc),
            }








