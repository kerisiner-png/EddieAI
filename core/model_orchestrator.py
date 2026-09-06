from dataclasses import dataclass
from typing import Any

import ctypes
import json
import time
import urllib.error
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

    Приоритет очереди (решение Эдди 06.09):
        1. ollama-cloud: gpt-oss:120b-cloud, gemma4:31b-cloud
           (локальный демон ollama оффлоадит в облако,
           auth — ollama signin; fast ~0.5-1.5 с)
        2. zen (ключи истекли — быстрый 401, фолбэк)
        3. glm z.ai (медленный при рейт-лимите)
    """

    SECRETS_DIR = Path.home() / ".eddieai_secrets"
    MISTRAL_MODEL = "mistral-small-latest"

    # Решение Эдди 06.09: локальные модели — ПОСЛЕДНИЙ РУБЕЖ
    # (только когда все облака недоступны) и выгрузка сразу
    # после ответа (keep_alive=0, модель не висит в RAM).
    LOCAL_MODELS_ENABLED = True

    CLOUD_PROVIDERS = [
        {
            "name": "ollama-gpt-oss",
            "key_path": (
                SECRETS_DIR / "ollama.key"
            ),
            "url": (
                "http://127.0.0.1:11434/v1"
                "/chat/completions"
            ),
            "model": "gpt-oss:120b-cloud",
            "max_tokens": 1024,
            "roles": [
                "conversation",
                "fallback",
                "plan",
                "reflection",
                "affective",
            ],
            "extra_payload": {
                "reasoning_effort": "low"
            },
        },
        {
            "name": "ollama-gemma",
            "key_path": (
                SECRETS_DIR / "ollama.key"
            ),
            "url": (
                "http://127.0.0.1:11434/v1"
                "/chat/completions"
            ),
            "model": "gemma4:31b-cloud",
            "max_tokens": 1024,
            "roles": [
                "conversation",
                "fallback",
                "plan",
                "reflection",
                "affective",
                "vision",
            ],
        },
        {
            "name": "zen-deepseek-flash",
            "key_path": (
                SECRETS_DIR / "zen.key"
            ),
            "url": (
                "https://opencode.ai/zen/v1"
                "/chat/completions"
            ),
            "model": "deepseek-v4-flash",
            "max_tokens": 1024,
            "roles": [
                "conversation",
                "fallback",
                "plan",
                "reflection",
            ],
        },
        {
            "name": "zen-deepseek-pro",
            "key_path": (
                SECRETS_DIR / "zen.key"
            ),
            "url": (
                "https://opencode.ai/zen/v1"
                "/chat/completions"
            ),
            "model": "deepseek-v4-pro",
            "max_tokens": 1024,
            "roles": [
                "deep",
            ],
        },
        {
            "name": "zen-qwen-affective",
            "key_path": (
                SECRETS_DIR / "zen.key"
            ),
            "url": (
                "https://opencode.ai/zen/v1"
                "/chat/completions"
            ),
            "model": "qwen3.6-plus",
            "max_tokens": 1024,
            "roles": ["affective"],
        },
        {
            "name": "zen-kimi-vision",
            "key_path": (
                SECRETS_DIR / "zen.key"
            ),
            "url": (
                "https://opencode.ai/zen/v1"
                "/chat/completions"
            ),
            "model": "kimi-k3",
            "max_tokens": 1024,
            "roles": ["vision"],
        },
        {
            "name": "glm",
            "key_path": (
                SECRETS_DIR / "glm.key"
            ),
            "url": (
                "https://api.z.ai/api/paas/v4"
                "/chat/completions"
            ),
            "model": "glm-4.7-flash",
            "extra_payload": {
                "thinking": {"type": "disabled"}
            },
        },
        {
            "name": "deepseek",
            "key_path": (
                SECRETS_DIR / "deepseek.key"
            ),
            "url": (
                "https://api.deepseek.com/v1"
                "/chat/completions"
            ),
            "model": "deepseek-chat",
        },
        {
            "name": "mistral",
            "key_path": (
                SECRETS_DIR / "mistral.key"
            ),
            "url": (
                "https://api.mistral.ai/v1/chat/completions"
            ),
            "model": "mistral-small-latest",
        },
        {
            "name": "groq",
            "key_path": (
                SECRETS_DIR / "groq.key"
            ),
            "url": (
                "https://api.groq.com/openai/v1/chat/completions"
            ),
            "model": "llama-3.3-70b-versatile",
        },
        {
            "name": "openrouter",
            "key_path": (
                SECRETS_DIR / "openrouter.key"
            ),
            "url": (
                "https://openrouter.ai/api/v1/chat/completions"
            ),
            "model": (
                "meta-llama/llama-3.3-70b-instruct:free"
            ),
        },
        {
            "name": "gemini",
            "key_path": (
                SECRETS_DIR / "gemini.key"
            ),
            "url": (
                "https://generativelanguage.googleapis.com"
                "/v1beta/openai/chat/completions"
            ),
            "model": "gemini-2.0-flash",
        },
    ]

    CLOUD_NET_COOLDOWN_SEC = 90
    CLOUD_BILLING_COOLDOWN_SEC = 1800
    CLOUD_TIMEOUT_SEC = 90

    def _cloud_chat(
        self,
        *,
        system,
        user,
        options,
        task=None,
    ):
        now = time.time()

        matching = [
            provider
            for provider in self.CLOUD_PROVIDERS
            if not provider.get("roles")
            or (
                task is not None
                and task in provider["roles"]
            )
        ]

        if not matching:
            matching = self.CLOUD_PROVIDERS

        print(
            f"[cloud] попытка: {len(matching)} "
            f"провайдеров (task={task})"
        )

        for provider in matching:
            key_path = provider["key_path"]

            if not key_path.exists():
                print(
                    f"[cloud] {provider['name']} "
                    "пропущен: нет ключа"
                )
                continue

            name = provider["name"]

            if now < self._cloud_blocked.get(
                name, 0.0
            ):
                remain = int(
                    self._cloud_blocked[name]
                    - now
                )
                print(
                    f"[cloud] {name} пропущен: "
                    f"cooldown ещё {remain}с"
                )
                continue

            content = self._cloud_chat_provider(
                provider,
                system,
                user,
                options,
                now,
            )

            if content is not None:
                return content

        return None

    def _cloud_chat_provider(
        self,
        provider,
        system,
        user,
        options,
        now,
    ):
        name = provider["name"]

        try:
            api_key = provider["key_path"].read_text(
                encoding="utf-8"
            ).strip()
            payload = {
                "model": provider["model"],
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
                    options.get("num_predict", 300),
                    provider.get("max_tokens", 512),
                ),
            }
            response_format = options.get(
                "response_format"
            )
            if response_format is not None:
                payload["response_format"] = (
                    response_format
                )
            payload.update(
                provider.get("extra_payload", {})
            )
            req = urllib.request.Request(
                provider["url"],
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; "
                        "Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/131.0 Safari/537.36"
                    ),
                },
            )
            if api_key and api_key != "no-auth":
                req.add_header(
                    "Authorization", f"Bearer {api_key}"
                )
            with urllib.request.urlopen(
                req,
                timeout=self.CLOUD_TIMEOUT_SEC,
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            content = msg.get("content", "")
            content = content.strip() if content else None
            if content is not None:
                self._cloud_used = name
                self._cloud_last_error[name] = ""
            else:
                print(
                    f"[cloud] {name}: пустой ответ "
                    "(thinking съел лимит токенов?)"
                )
            return content
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode(
                    "utf-8", errors="replace"
                )[:200]
            except Exception:
                pass
            error = f"HTTP {exc.code}: {detail}"
            cooldown = (
                self.CLOUD_BILLING_COOLDOWN_SEC
                if exc.code in (401, 402, 403)
                else self.CLOUD_NET_COOLDOWN_SEC
            )
            self._cloud_blocked[name] = now + cooldown
            self._cloud_last_error[name] = error
            print(f"[cloud] {name} недоступен: {error}")
            return None
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._cloud_blocked[name] = (
                now + self.CLOUD_NET_COOLDOWN_SEC
            )
            self._cloud_last_error[name] = error
            print(f"[cloud] {name} недоступен: {error}")
            return None

    def _cloud_chat_vision(
        self,
        system,
        user,
        images=None,
        task="vision",
    ):
        if images is None:
            images = []
        matching = [
            p
            for p in self.CLOUD_PROVIDERS
            if task in (p.get("roles") or [])
        ]
        if not matching:
            return {
                "text": "",
                "error": "no vision provider",
            }
        provider = matching[0]
        if images:
            user_content = [
                {"type": "text", "text": user}
            ]
            for img_b64 in images:
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                "data:image/png;"
                                f"base64,{img_b64}"
                            )
                        },
                    }
                )
        else:
            user_content = user
        options = {
            "num_predict": provider.get(
                "max_tokens", 1024
            )
        }
        content = self._cloud_chat_provider(
            provider,
            system,
            user_content,
            options,
            time.time(),
        )
        if content is None:
            return {
                "text": "",
                "error": (
                    f"cloud failure: "
                    f"{self._cloud_last_error.get(provider['name'], '')}"
                ),
            }
        return {"text": content}

    def cloud_chat_stream(
        self,
        *,
        system,
        user,
        options=None,
        on_delta=None,
        task=None,
    ):
        """
        Стриминговый облачный вызов (SSE). on_delta(piece)
        вызывается по мере поступления текста.
        Возвращает полный текст или None.
        """
        options = options or {}
        now = time.time()

        matching = [
            provider
            for provider in self.CLOUD_PROVIDERS
            if not provider.get("roles")
            or (
                task is not None
                and task in provider["roles"]
            )
        ]

        if not matching:
            matching = self.CLOUD_PROVIDERS

        for provider in matching:
            key_path = provider["key_path"]

            if not key_path.exists():
                continue

            name = provider["name"]

            if now < self._cloud_blocked.get(
                name, 0.0
            ):
                continue

            try:
                api_key = (
                    key_path.read_text(
                        encoding="utf-8"
                    ).strip()
                )
                payload = {
                    "model": provider["model"],
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                system
                                + "\nНикогда не используй эмодзи."
                            ),
                        },
                        {
                            "role": "user",
                            "content": user,
                        },
                    ],
                    "temperature": options.get(
                        "temperature", 0.7
                    ),
                    "max_tokens": min(
                        options.get(
                            "num_predict", 300
                        ),
                        provider.get(
                            "max_tokens", 512
                        ),
                    ),
                    "stream": True,
                }
                response_format = options.get(
                    "response_format"
                )
                if response_format is not None:
                    payload["response_format"] = (
                        response_format
                    )
                payload.update(
                    provider.get(
                        "extra_payload", {}
                    )
                )
                req = urllib.request.Request(
                    provider["url"],
                    data=json.dumps(
                        payload
                    ).encode("utf-8"),
                    headers={
                        "Content-Type": (
                            "application/json"
                        ),
                        "User-Agent": (
                            "Mozilla/5.0 "
                            "(Windows NT 10.0; "
                            "Win64; x64) "
                            "AppleWebKit/537.36 "
                            "(KHTML, like Gecko) "
                            "Chrome/131.0 "
                            "Safari/537.36"
                        ),
                    },
                )
                if (
                    api_key
                    and api_key != "no-auth"
                ):
                    req.add_header(
                        "Authorization",
                        f"Bearer {api_key}",
                    )
                pieces = []
                with urllib.request.urlopen(
                    req,
                    timeout=(
                        self.CLOUD_TIMEOUT_SEC
                    ),
                ) as resp:
                    for raw in resp:
                        line = raw.decode(
                            "utf-8",
                            errors="replace",
                        ).strip()
                        if not line.startswith(
                            "data:"
                        ):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(
                                data
                            )
                        except json.JSONDecodeError:
                            continue
                        choices = (
                            obj.get("choices")
                            or []
                        )
                        if not choices:
                            continue
                        delta = (
                            choices[0].get(
                                "delta", {}
                            )
                            or {}
                        )
                        piece = delta.get(
                            "content", ""
                        ) or ""
                        if not piece:
                            continue
                        pieces.append(piece)
                        if on_delta is not None:
                            try:
                                on_delta(piece)
                            except Exception:
                                pass
                content = "".join(
                    pieces
                ).strip()
                if content:
                    self._cloud_used = name
                    self._cloud_last_error[
                        name
                    ] = ""
                    self._cloud_blocked.pop(
                        name, None
                    )
                    return content
                self._cloud_last_error[
                    name
                ] = "empty"
                return None
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode(
                        "utf-8",
                        errors="replace",
                    )[:200]
                except Exception:
                    pass
                error = (
                    f"HTTP {exc.code}: "
                    f"{detail}"
                )
                cooldown = (
                    self.CLOUD_BILLING_COOLDOWN_SEC
                    if exc.code
                    in (401, 402, 403)
                    else self.CLOUD_NET_COOLDOWN_SEC
                )
                self._cloud_blocked[
                    name
                ] = now + cooldown
                self._cloud_last_error[
                    name
                ] = error
                print(
                    f"[cloud] {name} "
                    f"недоступен: {error}"
                )
                return None
            except Exception as exc:
                error = (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
                self._cloud_blocked[name] = (
                    now
                    + self.CLOUD_NET_COOLDOWN_SEC
                )
                self._cloud_last_error[
                    name
                ] = error
                print(
                    f"[cloud] {name} "
                    f"недоступен: {error}"
                )
                return None

        return None

    def __init__(
        self,
        fallback_on_error: bool = True,
    ):
        self.fallback_on_error = fallback_on_error
        self._cloud_blocked = {}
        self._cloud_last_error = {}
        self._cloud_used = ""

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

    MODEL_RAM_GB = {
        "qwen3.5:4b": 3.6,
        "phi4-mini:latest": 2.6,
    }

    @staticmethod
    def available_ram_gb():
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(stat)
        )
        return stat.ullAvailPhys / (1024 ** 3)

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

        # Ensure stdout/stderr are UTF‑8 to avoid UnicodeEncodeError when printing Cyrillic
        try:
            import sys
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

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
                    keep_alive=0,
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
                task=task,
            )
            if cloud_content is not None:
                return {
                    "status": "OK",
                    "content": cloud_content,
                    "model": (
                        self._cloud_used
                        or self.MISTRAL_MODEL
                    ),
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
            cloud_content = self._cloud_chat(
                system=system,
                user=user,
                options=options or {},
                task="deep",
            )

            if cloud_content is not None:
                return {
                    "status": "OK",
                    "content": cloud_content,
                    "model": (
                        self._cloud_used
                        or self.MISTRAL_MODEL
                    ),
                }

            decision = self.select_model(
                profile
            )

        model = next(
            item
            for item in self.models
            if item.name == decision.model
        )

        # -----------------------------------------------------
        # RESOURCE POLICY
        # -----------------------------------------------------

        free_gb = self.available_ram_gb()
        required_gb = self.MODEL_RAM_GB.get(model.name)
        if required_gb is not None and free_gb < required_gb:
            lighter = "phi4-mini:latest"
            lighter_need = self.MODEL_RAM_GB.get(lighter)
            if (
                model.name != lighter
                and lighter_need is not None
                and free_gb >= lighter_need
            ):
                print(
                    f"[orchestrator] мало RAM ({free_gb:.1f} GB) "
                    f"для {model.name}: даунгрейд на {lighter}"
                )
                decision = ModelDecision(
                    model=lighter,
                    provider="ollama-local",
                    score=0.1,
                    reason="Downgrade: insufficient free RAM.",
                )
                model = next(
                    item
                    for item in self.models
                    if item.name == lighter
                )
                required_gb = lighter_need
            else:
                message = (
                    f"[orchestrator] отказ: свободно "
                    f"{free_gb:.1f} GB, модели {model.name} "
                    f"нужно ~{required_gb} GB. Освободите память."
                )
                print(message)
                return {
                    "status": "ERROR",
                    "content": "",
                    "model": model.name,
                    "provider": model.provider,
                    "error": "insufficient_ram",
                    "error_detail": message,
                }

        is_fast = (
            metadata is not None
            and metadata.get("fast", False)
        )

        if model.name == "phi4-mini:latest":
            default_num_predict = (
                128 if is_fast else 256
            )
            keep_alive = 0

        elif model.name == "qwen3.5:4b":
            default_num_predict = 256
            keep_alive = 0

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
                "keep_alive": 0,
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








