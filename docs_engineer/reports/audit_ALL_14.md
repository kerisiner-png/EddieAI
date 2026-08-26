# Аудит ALL — батч 14

Файлы: lexical_claim_adapter.py, model_orchestrator.py, night_consolidation.py
Модель: deepseek-v4-flash

Мы провели аудит трёх файлов: core/lexical_claim_adapter.py, core/model_orchestrator.py, core/night_consolidation.py. Ниже подробный разбор.

## Файл: core/lexical_claim_adapter.py (32 строки)

### Найденные проблемы:

1. **Строка 1**: `from core.claim_engine import Claim` — импорт абсолютный. Если модуль используется как часть пакета, это нормально, но если файл запускается напрямую, может быть проблема. Однако это стандартная практика, серьёзность LOW.

2. **Строки 5-19**: Метод `to_claim` — статический, но использует `lexical_claim` без проверки типа. Если `lexical_claim` не имеет атрибутов `predicate`, `value` и т.д., будет ошибка AttributeError. Но это ожидаемо, так как предполагается, что передаётся объект с этими атрибутами. Проблема не критична.

3. **Строки 21-31**: Метод `to_claims` — классовый, использует `cls.to_claim`. Всё корректно.

4. **Стиль**: Везде используется отступы в 4 пробела, но в некоторых местах есть лишние пустые строки (например, после `return Claim(`). Это не ошибка, но нарушает единообразие. Серьёзность LOW.

5. **Потенциальная проблема**: `to_claim` не проверяет, что `lexical_claim` не None. Если передать None, будет AttributeError. Но это скорее всего не предполагается.

6. **Замечание**: В `to_claims` используется list comprehension, но можно было бы использовать map. Не ошибка.

7. **Отсутствие аннотаций типов**: В `to_claim` параметр `lexical_claim` не аннотирован. Это снижает читаемость, но не является ошибкой.

8. **Кодировка**: Файл, судя по всему, в UTF-8 без BOM (не видно BOM). Это хорошо.

9. **Мёртвый код**: Нет.

10. **Связи**: Зависит от `core.claim_engine.Claim`. Если этот класс не существует или имеет другую сигнатуру, будет ошибка. Но это вне данного файла.

### Сводка по файлу:
Файл простой, функциональный, но имеет мелкие стилистические недочёты. Критических проблем нет.

## Файл: core/model_orchestrator.py (1054 строки)

### Найденные проблемы:

1. **Строка 1**: `from dataclasses import dataclass` — импорт корректный.

2. **Строка 2**: `from typing import Any` — корректно.

3. **Строка 4**: `import ctypes` — используется для получения RAM. Это Windows-специфично. Если проект запускается на Linux/macOS, `ctypes.windll` вызовет ошибку. Это серьёзная проблема кроссплатформенности. Серьёзность HIGH.

4. **Строка 5**: `import json` — ок.

5. **Строка 6**: `import time` — ок.

6. **Строка 7**: `import urllib.error` и `urllib.request` — ок.

7. **Строка 8**: `from pathlib import Path` — ок.

8. **Строка 9**: `from ollama import Client, chat, list as ollama_list` — импорт `chat` не используется (мёртвый импорт). Серьёзность LOW.

9. **Строки 12-24**: Датaclass'ы `ModelProfile`, `TaskProfile`, `ModelDecision` — корректны.

10. **Строка 27**: Класс `ModelOrchestrator` — docstring говорит, что доступны только локальные модели, но в коде есть облачные провайдеры. Несоответствие документации. Серьёзность LOW.

11. **Строка 29**: `SECRETS_DIR = Path.home() / ".eddieai_secrets"` — путь к секретам. Хорошо, что не в коде.

12. **Строка 30**: `MISTRAL_MODEL = "mistral-small-latest"` — используется как fallback.

13. **Строки 32-105**: Список `CLOUD_PROVIDERS` — содержит конфигурации облачных провайдеров. Проблемы:
    - В `zen-deepseek-flash` и других `zen-*` указан одинаковый `key_path` (`.eddieai_secrets/zen.key`). Это нормально, если один ключ для всех zen.
    - В `glm` и других нет поля `roles`, что означает, что они подходят для любых задач (если не указаны roles, то провайдер считается универсальным). Это может быть нежелательно, но не ошибка.
    - В `openrouter` модель `meta-llama/llama-3.3-70b-instruct:free` — бесплатная, но может быть медленной.
    - В `gemini` URL указан как `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` — это OpenAI-совместимый эндпоинт, но для Gemini обычно используется другой формат. Возможно, это работает, но требует проверки.
    - В `groq` модель `llama-3.3-70b-versatile` — может быть не самой быстрой.
    - В `mistral` модель `mistral-small-latest` — ок.
    - В `deepseek` модель `deepseek-chat` — ок.
    - В `zen-deepseek-pro` и `zen-qwen-affective` и `zen-kimi-vision` — модели выглядят вымышленными (deepseek-v4-pro, qwen3.6-plus, kimi-k3). Возможно, это реальные, но не уверен. Если они не существуют, будут ошибки.
    - В `zen-deepseek-flash` модель `deepseek-v4-flash` — тоже подозрительно.
    - В `glm` модель `glm-4.5-flash` — возможно, существует.
    - В `openrouter` модель `meta-llama/llama-3.3-70b-instruct:free` — существует.
    - В `gemini` модель `gemini-2.0-flash` — существует.
    - В `groq` модель `llama-3.3-70b-versatile` — существует.
    - В `mistral` модель `mistral-small-latest` — существует.
    - В `deepseek` модель `deepseek-chat` — существует.

    Проблема: у провайдеров `glm`, `deepseek`, `mistral`, `groq`, `openrouter`, `gemini` нет поля `roles`, поэтому они будут использоваться для любых задач, включая `deep` и `reflection`. Это может привести к непредсказуемому поведению, если эти модели не подходят для сложных задач. Но это скорее конфигурационная проблема, не баг.

14. **Строка 107**: `CLOUD_NET_COOLDOWN_SEC = 90` — ок.

15. **Строка 108**: `CLOUD_BILLING_COOLDOWN_SEC = 1800` — ок.

16. **Строка 109**: `CLOUD_TIMEOUT_SEC = 90` — ок.

17. **Метод `_cloud_chat` (строки 111-170)**:
    - Строка 113: `now = time.time()` — ок.
    - Строки 115-122: Фильтрация провайдеров по ролям. Если `task` не указан, то берутся все провайдеры без `roles`. Это может быть нежелательно, но допустимо.
    - Строка 124: `if not matching: matching = self.CLOUD_PROVIDERS` — если ни один провайдер не подходит (например, все имеют roles и task не совпадает), то берутся все. Это может привести к использованию неподходящего провайдера. Лучше было бы вернуть None.
    - Строка 128: `print(f"[cloud] попытка: {len(matching)} провайдеров (task={task})")` — ок.
    - Строки 130-145: Цикл по провайдерам. Проверка наличия ключа, cooldown.
    - Строка 147: `content = self._cloud_chat_provider(...)` — вызов.
    - Строка 150: `if content is not None: return content` — возвращает первый успешный ответ.
    - Строка 154: `return None` — если все провайдеры недоступны.

    Проблема: если все провайдеры недоступны, возвращается None, и вызывающий код переходит к локальным моделям. Это нормально.

18. **Метод `_cloud_chat_provider` (строки 156-250)**:
    - Строка 160: `api_key = provider["key_path"].read_text(encoding="utf-8").strip()` — чтение ключа. Если файл не существует, будет исключение FileNotFoundError, которое перехватывается в `except Exception` (строка 240) и возвращается None. Это нормально.
    - Строка 162: `payload` — формирование запроса.
    - Строка 170: `response_format` — если есть, добавляется.
    - Строка 172: `payload.update(provider.get("extra_payload", {}))` — дополнительный payload.
    - Строка 174: `req = urllib.request.Request(...)` — создание запроса.
    - Строка 181: `if api_key and api_key != "no-auth": req.add_header("Authorization", f"Bearer {api_key}")` — добавление заголовка.
    - Строка 184: `with urllib.request.urlopen(req, timeout=self.CLOUD_TIMEOUT_SEC) as resp:` — выполнение запроса.
    - Строка 185: `data = json.loads(resp.read().decode("utf-8"))` — парсинг ответа.
    - Строка 186: `msg = data["choices"][0]["message"]` — получение сообщения.
    - Строка 187: `content = msg.get("content", "")` — получение контента.
    - Строка 189: `if not content: content = msg.get("reasoning_content", "")` — если content пуст, берём reasoning_content.
    - Строка 190: `content = content.strip() if content else None` — обрезка.
    - Строка 191: `if content is not None: self._cloud_used = name; self._cloud_last_error[name] = ""` — запись успеха.
    - Строка 195: `else: print(...)` — если пустой ответ.
    - Строка 197: `return content` — возврат.
    - Строки 199-238: Обработка ошибок HTTPError и общих исключений. Устанавливается cooldown и записывается ошибка.

    Проблемы:
    - Строка 186: `data["choices"][0]["message"]` — если ответ не содержит `choices` или `message`, будет KeyError, который перехватится в `except Exception` (строка 240) и вернёт None. Это нормально, но лучше было бы проверить.
    - Строка 189: `msg.get("reasoning_content", "")` — это специфично для некоторых моделей (например, DeepSeek). Если модель не поддерживает, будет пусто.
    - Строка 191: `self._cloud_used = name` — запись имени провайдера, который использовался. Это глобальное состояние, но оно не потокобезопасно. Если несколько потоков вызывают `_cloud_chat`, возможна гонка. Но в текущем коде, вероятно, всё однопоточное.
    - Строка 199: `except urllib.error.HTTPError as exc:` — обработка HTTP ошибок. Код 401, 402, 403 — billing cooldown, остальные — net cooldown. Это разумно.
    - Строка 240: `except Exception as exc:` — перехват всех остальных исключений. Это может скрыть ошибки программирования, но для надёжности приемлемо.

19. **Метод `__init__` (строки 252-290)**:
    - Строка 253: `self.fallback_on_error = fallback_on_error` — ок.
    - Строка 254: `self._cloud_blocked = {}` — словарь для cooldown
