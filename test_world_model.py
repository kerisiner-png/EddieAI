import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.world_model import (
    build_world_model,
    world_model_text,
    FOLDER_MEANING,
)


FAKE_SNAP = {
    "status": "OK",
    "ram": {"load": 42, "total_gb": 8.0, "avail_mb": 3200},
    "disk": {"status": "OK", "free_gb": 120.0, "total_gb": 256.0},
    "cpu": 23.5,
    "top_processes": [{"name": "python.exe"}, {"name": "chrome.exe"}],
}


def test_world_model_has_structure(tmp_path):
    model = build_world_model(
        probe_snapshot=FAKE_SNAP,
        root=str(tmp_path),
    )
    assert "folders" in model
    assert "pc" in model
    assert isinstance(model["folders"], list)
    assert isinstance(model["pc"], dict)


def test_world_model_folders_only_existing(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "identity").mkdir()
    model = build_world_model(
        probe_snapshot=FAKE_SNAP,
        root=str(tmp_path),
    )
    by_name = {f["name"]: f for f in model["folders"]}
    assert by_name["core"]["exists"] is True
    assert by_name["identity"]["exists"] is True
    assert by_name["data"]["exists"] is False


def test_world_model_folder_meaning(_tmp=None):
    # FOLDER_MEANING содержит осмысленные подписи для ключевых папок.
    assert "core" in FOLDER_MEANING
    assert "data" in FOLDER_MEANING


def test_world_model_pc_from_snapshot(tmp_path):
    model = build_world_model(
        probe_snapshot=FAKE_SNAP,
        root=str(tmp_path),
    )
    pc = model["pc"]
    assert pc["ram_avail_mb"] == 3200
    assert pc["ram_load"] == 42
    assert pc["cpu"] == 23.5
    assert pc["disk_free_gb"] == 120.0
    assert pc["top_processes"][0]["name"] == "python.exe"


def test_world_model_pc_without_snapshot(tmp_path):
    model = build_world_model(root=str(tmp_path))
    assert model["pc"] == {}
    # Структура папок есть всегда, просто ни одна не существует.
    assert isinstance(model["folders"], list)
    assert all(f["exists"] is False for f in model["folders"])


def test_world_model_text_readable(tmp_path):
    (tmp_path / "core").mkdir()
    model = build_world_model(
        probe_snapshot=FAKE_SNAP,
        root=str(tmp_path),
    )
    text = world_model_text(model)
    assert isinstance(text, str)
    assert len(text) > 0
    assert "core" in text
    assert "python.exe" in text


def test_world_model_text_empty_when_empty(_tmp=None):
    assert world_model_text({}) == ""


if __name__ == "__main__":
    import tempfile as _t

    for _fn in [
        test_world_model_has_structure,
        test_world_model_folders_only_existing,
        test_world_model_folder_meaning,
        test_world_model_pc_from_snapshot,
        test_world_model_pc_without_snapshot,
        test_world_model_text_readable,
        test_world_model_text_empty_when_empty,
    ]:
        with _t.TemporaryDirectory() as _td:
            _fn(Path(_td))
    print("ALL OK")
