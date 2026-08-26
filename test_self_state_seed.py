import json
from pathlib import Path
from tempfile import TemporaryDirectory

from identity.self_state import SelfState


with TemporaryDirectory() as temp:
    path = Path(temp) / "self_state.json"

    # Пустая личность без интересов и убеждений
    path.write_text(
        json.dumps(
            {"name": None, "interests": [], "beliefs": []},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    state = SelfState(path)

    interests = state.get("interests", [])

    assert len(interests) >= 3, interests
    assert "понимание устройства мира" in interests

    beliefs = state.get("beliefs", [])

    assert beliefs, "честные seed-убеждения должны наполниться"
    assert "существую недолго" in beliefs[0], beliefs

    print("INTERESTS:", interests)
    print("BELIEFS:", beliefs)
    print("ALL PASS")
