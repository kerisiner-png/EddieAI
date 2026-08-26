# Аудит ALL — батч 26

Файлы: adaptive_planner.py, affective_behavior_policy.py, affective_dialogue_policy.py
Модель: deepseek-v4-flash

## Аудит модуля identity

### Файл: identity/adaptive_planner.py

| № | Строки | Тип проблемы | Серьёзность | Описание и последствия | Рекомендация |
|---|--------|--------------|-------------|------------------------|--------------|
| 1 | 20–24 | Отсутствие обработки ошибок | MEDIUM | `CloudFirstLlm` получает `model_orchestrator` (может быть `None`). Если `CloudFirstLlm` не рассчитан
