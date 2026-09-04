from pathlib import Path

from core.world_description import (
    PROJECT_ROOT,
    FOLDER_MEANING,
)


def build_folders_model(root):
    folders = []
    root_path = Path(root)
    for folder, meaning in FOLDER_MEANING.items():
        folders.append({
            "name": folder,
            "meaning": meaning,
            "exists": (root_path / folder).is_dir(),
        })
    return folders


def _pc_model(snapshot):
    if not snapshot or snapshot.get("status") != "OK":
        return {}
    ram = snapshot.get("ram") or {}
    disk = snapshot.get("disk") or {}
    top = (
        snapshot.get("top_processes")
        or []
    )
    procs = [
        {
            "name": proc.get("name"),
            "memory_mb": proc.get("memory_mb"),
        }
        for proc in top
        if proc.get("name")
    ]
    model = {}
    if ram.get("avail_mb") is not None:
        model["ram_avail_mb"] = ram["avail_mb"]
    if ram.get("load") is not None:
        model["ram_load"] = ram["load"]
    if snapshot.get("cpu") is not None:
        model["cpu"] = snapshot["cpu"]
    if disk.get("status") == "OK":
        if disk.get("free_gb") is not None:
            model["disk_free_gb"] = disk["free_gb"]
        if disk.get("total_gb") is not None:
            model["disk_total_gb"] = disk["total_gb"]
    if procs:
        model["top_processes"] = procs
    return model


def build_world_model(
    probe_snapshot=None,
    root=None,
):
    root = root if root is not None else str(PROJECT_ROOT)
    return {
        "root": root,
        "folders": build_folders_model(root),
        "pc": _pc_model(probe_snapshot),
    }


def world_model_text(model):
    if not model:
        return ""
    lines = []
    folders = model.get("folders") or []
    existing = [
        folder
        for folder in folders
        if folder.get("exists")
    ]
    if existing:
        names = ", ".join(
            folder["name"]
            for folder in existing
        )
        lines.append(f"каталоги: {names}")
    pc = model.get("pc") or {}
    if pc.get("ram_avail_mb") is not None:
        lines.append(
            f"свободная RAM ~{pc['ram_avail_mb']} МБ"
        )
    if pc.get("cpu") is not None:
        lines.append(f"CPU ~{pc['cpu']}%")
    if pc.get("disk_free_gb") is not None:
        lines.append(
            f"диск C: свободно ~{pc['disk_free_gb']} ГБ"
        )
    top = pc.get("top_processes") or []
    if top:
        names = ", ".join(
            proc["name"]
            for proc in top
        )
        lines.append(f"активные процессы: {names}")
    return "; ".join(lines)


def ensure_world_model(
    self_state,
    probe_snapshot=None,
    root=None,
):
    existing = self_state.get("world_model")
    if (
        existing
        and not probe_snapshot
    ):
        return existing
    model = build_world_model(
        probe_snapshot=probe_snapshot,
        root=root,
    )
    self_state.set("world_model", model)
    return model
