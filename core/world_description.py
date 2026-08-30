from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FOLDER_MEANING = {
    "core": "мозг, внутренние подсистемы",
    "identity": "личность: цели, черты, эмоции",
    "memory": "память: события, знания, evidence",
    "data": "мои личные данные (не трогать напрямую)",
    "docs_engineer": "инженерная документация, дорожная карта",
    "communication": "голос и мессенджер-каналы",
}


def build_world_description() -> str:
    parts = []
    for folder, meaning in FOLDER_MEANING.items():
        if (PROJECT_ROOT / folder).is_dir():
            parts.append(f"{folder} — {meaning}")
    editable = ", ".join(
        name
        for name in parts[:8]
    )
    root_note = (
        f"Я живу в каталоге {PROJECT_ROOT}. "
        f"Мои каталоги: {editable}."
    )
    return root_note[:500]


def world_block(world_description: str) -> str:
    if not world_description:
        return ""
    return (
        "ГДЕ ТЫ ЖИВЁШЬ\n"
        f"{world_description}\n"
    )