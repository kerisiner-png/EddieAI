import json
import random


# Сны — слабая копия яви: эмоция сна применяется с демпфером 0.5
# и весом сна 0.25 (provenance DREAM). Черты личности не трогаем.
DREAM_EMOTION_GAIN = 0.5
DREAM_WEIGHT = 0.25

DREAM_EVENT_CONFIDENCE = 0.25
INTERPRETATION_CONFIDENCE = 0.35

NEUTRAL_EMOTION = "neutral"

_MAX_TEXT = 300
_MAX_FRAMES = 4
_REPLAY_LIMIT = 6
_PLOT_REPEAT_LIMIT = 3


def _cap(text, limit=_MAX_TEXT):
    text = (text or "").strip()
    if not text:
        return ""
    return text[:limit]


def _segment_lines(feed_text, prefix_len=20):
    lines = []
    for line in (feed_text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        clean = line[prefix_len:] if line.startswith("[") else line
        clean = clean.strip()
        if clean:
            lines.append(clean)
    return lines


class DreamProcessor:
    """
    Механизм снов: жатва событий дня -> replay реальных сегментов ->
    ассоциативные кадры -> осмысление облачной моделью -> эмоции сна
    (демпфером) -> события DREAM + интерпретация -> дневник.

    Сон происходит тихо, без действий и диалога. Черты личности не
    изменяются. Все артефакты помечены провенансом DREAM.
    """

    def __init__(
        self,
        memory=None,
        self_state=None,
        affective_state=None,
        diary=None,
        model=None,
        night=None,
        rng=None,
        max_replay_segments=_REPLAY_LIMIT,
        max_frames=_MAX_FRAMES,
        plot_repeat_limit=_PLOT_REPEAT_LIMIT,
        snapshots_enabled=False,
    ):
        self.memory = memory
        self.self_state = self_state
        self.affective_state = affective_state
        self.diary = diary
        self.model = model
        self.night = night
        self.rng = rng or random.Random()
        self.max_replay_segments = max_replay_segments
        self.max_frames = max_frames
        self.plot_repeat_limit = plot_repeat_limit
        self.snapshots_enabled = snapshots_enabled

    # ---------------------------------------------------------
    # Жатва событий дня
    # ---------------------------------------------------------

    def harvest(self, limit=40):
        segments = []

        if self.memory is not None:
            try:
                feed = self.memory.recent_life_feed(
                    limit=limit
                )
                for text in _segment_lines(feed):
                    segments.append({
                        "text": _cap(text),
                        "type": "day",
                    })
            except Exception:
                pass

            try:
                actions = self.memory.recent_action_results(
                    limit=max(2, limit // 4)
                )
                for text in _segment_lines(actions):
                    segments.append({
                        "text": _cap(text),
                        "type": "tool",
                    })
            except Exception:
                pass

        return segments[:limit]

    # ---------------------------------------------------------
    # Каркас сна
    # ---------------------------------------------------------

    def replay(self, segments):
        replay = []
        for seg in segments[: self.max_replay_segments]:
            text = _cap(seg.get("text") if isinstance(seg, dict) else seg)
            if not text:
                continue
            replay.append({
                "text": text,
                "type": str(
                    seg.get("type", "day")
                    if isinstance(seg, dict)
                    else "day"
                ),
            })
        return replay

    def _scene_from_seq(self, seq):
        glue = ["И вот я снова думаю об этом.",
                "Неожиданно рядом возникает знакомое место.",
                "Потом всё смешивается.",
                "Среди этого я узнаю собственные мысли."]
        parts = []
        for i, seg in enumerate(seq):
            parts.append(seg["text"])
            if i < len(seq) - 1 and i < len(glue):
                parts.append(glue[i])
        return " ".join(parts)

    def skew(self, replay):
        frames = []
        repeats = {}
        attempts = 0
        max_attempts = self.max_frames * 4 + 4

        while len(frames) < self.max_frames and attempts < max_attempts:
            attempts += 1

            if not replay:
                break

            seq = self.rng.sample(
                replay,
                min(len(replay), self.rng.randint(2, 3)),
            )

            key = tuple(
                seg["text"][:24]
                for seg in seq
            )

            if repeats.get(key, 0) >= self.plot_repeat_limit:
                continue

            repeats[key] = repeats.get(key, 0) + 1

            frames.append({
                "scene": _cap(self._scene_from_seq(seq)),
            })

        return frames

    def frames(self, replay):
        if not replay:
            return []

        if self.night is not None:
            try:
                night_frames = self.night(replay)
                if isinstance(night_frames, list) and night_frames:
                    return night_frames[: self.max_frames]
            except Exception:
                pass

        return self.skew(replay)

    # ---------------------------------------------------------
    # Осмысление сна (облачная модель; фолбэк без эмоций)
    # ---------------------------------------------------------

    def _default_dream(self, frames):
        scene = frames[0].get("scene") or ""
        return {
            "scene": _cap(scene),
            "emotion": NEUTRAL_EMOTION,
            "intensity": 0.1,
            "theme": "",
        }

    def _parse_dream(self, text, frames):
        if not text:
            return None

        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None

        if not isinstance(data, dict):
            return None

        scene = _cap(str(data.get("scene") or ""))
        if not scene and frames:
            scene = _cap(frames[0].get("scene") or "")

        emotion = str(data.get("emotion") or NEUTRAL_EMOTION)

        try:
            from identity.affective_state import (
                DEFAULT_EMOTIONS,
            )
            if emotion not in DEFAULT_EMOTIONS:
                emotion = NEUTRAL_EMOTION
        except Exception:
            if emotion != NEUTRAL_EMOTION:
                emotion = NEUTRAL_EMOTION

        try:
            intensity = float(data.get("intensity", 0.1))
        except (TypeError, ValueError):
            intensity = 0.1

        intensity = max(0.0, min(1.0, intensity))

        return {
            "scene": scene,
            "emotion": emotion,
            "intensity": intensity,
            "theme": _cap(str(data.get("theme") or ""), 120),
        }

    def dream(self, frames):
        if self.model is None:
            return self._default_dream(frames)

        system = (
            "Ты EddieAI. Ты видишь сон: короткую ассоциативную картину "
            "из образов, рождённых прожитым днём. Верни ТОЛЬКО JSON без "
            "пояснений:\n"
            '{"scene": "короткая сцена сна по-русски до 300 знаков", '
            '"emotion": "одно слово из: joy, sadness, fear, anger, '
            'disgust, surprise, interest, curiosity, frustration, '
            'uncertainty, satisfaction", "intensity": 0.0-1.0, '
            '"theme": "тема сна коротко"}'
        )

        frames_text = "\n".join(
            "- " + _cap(f.get("scene") or "")
            for f in frames
        )

        try:
            text = self.model._cloud_chat(
                system=system,
                user=f"Осколки дня, из которых рождается сон:\n{frames_text}",
                options={
                    "temperature": 0.9,
                    "num_predict": 500,
                },
            )
        except Exception:
            text = None

        parsed = self._parse_dream(text, frames)

        if parsed is None:
            return self._default_dream(frames)

        return parsed

    # ---------------------------------------------------------
    # Эмоции сна (легитимный писатель аффекта)
    # ---------------------------------------------------------

    def affect(self, dream):
        if self.affective_state is None:
            return

        emotion = dream.get("emotion")
        try:
            from identity.affective_state import (
                DEFAULT_EMOTIONS,
            )
            if emotion not in DEFAULT_EMOTIONS:
                emotion = NEUTRAL_EMOTION
        except Exception:
            return

        intensity = float(dream.get("intensity") or 0.1)
        delta = round(
            intensity * DREAM_EMOTION_GAIN * DREAM_WEIGHT,
            4,
        )

        try:
            self.affective_state.apply_reaction(
                changes={emotion: delta},
                trigger="dream",
                reason=(
                    "Переживание сна: "
                    f"{dream.get('scene', '')[:80]}"
                ),
                source="DREAM",
                metadata={
                    "emotion": emotion,
                    "scene": dream.get("scene", "")[:160],
                    "theme": dream.get("theme", ""),
                },
            )
        except Exception:
            pass

    # ---------------------------------------------------------
    # Запись сна
    # ---------------------------------------------------------

    def record(self, dream):
        scene = dream.get("scene")
        if not scene:
            return 0

        count = 0

        emotion = dream.get("emotion") or NEUTRAL_EMOTION
        intensity = dream.get("intensity") or 0.1
        theme = dream.get("theme") or ""

        if self.memory is not None:
            try:
                from memory.events import Event

                self.memory.remember(Event.create(
                    content=f"Мне снилось: {_cap(scene, 400)}",
                    event_type="DREAM",
                    source_type="DREAM",
                    source="self",
                    personal_experience=True,
                    confidence=DREAM_EVENT_CONFIDENCE,
                    interpretation=(
                        "Сон: переживание из образов прожитого дня. "
                        f"Эмоция: {emotion} ({intensity}). "
                        f"Тема: {theme or 'не определена'}."
                    ),
                    verified=False,
                ))
                count += 1

                self.memory.remember(Event.create(
                    content=(
                        f"После сна я замечаю, что "
                        f"{theme or 'некая тема из пережитого'}"
                        " занимает мои мысли."
                    ),
                    event_type="DREAM_INTERPRETATION",
                    source_type="DREAM_INTERPRETATION",
                    source="self",
                    personal_experience=True,
                    confidence=INTERPRETATION_CONFIDENCE,
                    interpretation=(
                        "Интерпретация сна: ассоциативное "
                        "осмысление прожитого дня."
                    ),
                    verified=False,
                ))
                count += 1
            except Exception:
                pass

        if self.diary is not None:
            try:
                self.diary.write(
                    f"Сегодня мне снилось: {_cap(scene, 400)}",
                    trigger="dream",
                )
            except Exception:
                pass

        return count

    # ---------------------------------------------------------
    # Снимки души (опционально, вне лёгкого конвейера)
    # ---------------------------------------------------------

    def snapshot_report(self, before_path=None, after_path=None):
        if not (before_path and after_path):
            return {}

        try:
            from identity import soul_snapshot

            return soul_snapshot.diff(
                before_path,
                after_path,
            )
        except Exception:
            return {}

    def _take_snapshot(self, label):
        try:
            from identity import soul_snapshot

            return soul_snapshot.take_snapshot(label)
        except Exception:
            return None

    # ---------------------------------------------------------
    # Единый метод сна
    # ---------------------------------------------------------

    def process(self, now=None, segments=None):
        snapshots = {}

        if self.snapshots_enabled:
            before = self._take_snapshot("dream_before")
        else:
            before = None

        if segments is None:
            segments = self.harvest(limit=40)

        replay = self.replay(segments)

        if not replay:
            return {
                "status": "empty",
                "scene": "",
                "emotion": NEUTRAL_EMOTION,
                "intensity": 0.1,
                "frames": 0,
                "events": 0,
                "replay": 0,
                "diff": {},
            }

        frames = self.frames(replay)

        if not frames:
            return {
                "status": "empty_no_frames",
                "scene": "",
                "emotion": NEUTRAL_EMOTION,
                "intensity": 0.1,
                "frames": 0,
                "events": 0,
                "replay": len(replay),
                "diff": {},
            }

        dream = self.dream(frames)

        self.affect(dream)

        events = self.record(dream)

        if self.snapshots_enabled:
            after = self._take_snapshot("dream_after")
            snapshots = self.snapshot_report(before, after)

        return {
            "status": "dreamed",
            "scene": dream.get("scene", ""),
            "emotion": dream.get("emotion", NEUTRAL_EMOTION),
            "intensity": dream.get("intensity", 0.1),
            "theme": dream.get("theme", ""),
            "frames": len(frames),
            "events": events,
            "replay": len(replay),
            "diff": snapshots,
        }