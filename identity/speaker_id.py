import json
import threading
from pathlib import Path

import numpy as np


_extractor_cache_lock = threading.Lock()
_extractor_cache = None


def make_sherpa_embed_fn(model_path, num_threads=2):
    def embed(samples, sample_rate=16000):
        global _extractor_cache
        with _extractor_cache_lock:
            if _extractor_cache is None:
                import sherpa_onnx

                cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                    model=str(model_path),
                    num_threads=num_threads,
                    provider="cpu",
                )
                _extractor_cache = (
                    sherpa_onnx.SpeakerEmbeddingExtractor(cfg)
                )
            extractor = _extractor_cache
        try:
            stream = extractor.create_stream()
            stream.accept_waveform(
                int(sample_rate), samples
            )
            return np.asarray(
                extractor.compute(stream),
                dtype=np.float32,
            )
        except Exception:
            return None

    return embed


def _cosine(a, b):
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class SpeakerIdentifier:
    def __init__(
        self,
        profiles_path=None,
        embed_fn=None,
        threshold=0.5,
    ):
        self._profiles_path = (
            str(profiles_path)
            if profiles_path is not None
            else None
        )
        self._embed_fn = embed_fn
        self._threshold = float(threshold)
        self._lock = threading.Lock()
        self._profiles = {}
        self._load()

    def _load(self):
        if self._profiles_path is None:
            return
        path = Path(self._profiles_path)
        if not path.exists():
            return
        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            return
        if not isinstance(data, dict):
            return
        for name, emb in data.items():
            try:
                self._profiles[name] = np.asarray(
                    emb, dtype=np.float32
                )
            except Exception:
                continue

    def _save(self):
        if self._profiles_path is None:
            return
        path = Path(self._profiles_path)
        data = {
            name: emb.tolist()
            for name, emb in self._profiles.items()
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            return

    def enroll(self, name, samples):
        if self._embed_fn is None:
            return False
        emb = self._embed_fn(samples, 16000)
        if emb is None:
            return False
        with self._lock:
            self._profiles[str(name)] = (
                np.asarray(emb, dtype=np.float32)
            )
            self._save()
        return True

    def identify(self, samples):
        if self._embed_fn is None:
            return None
        emb = self._embed_fn(samples, 16000)
        if emb is None:
            return None
        with self._lock:
            best = None
            best_score = 0.0
            for name, prof in self._profiles.items():
                score = _cosine(emb, prof)
                if score > best_score:
                    best_score = score
                    best = name
            if (
                best is not None
                and best_score >= self._threshold
            ):
                return best
        return None

    def clear(self):
        with self._lock:
            self._profiles.clear()
            self._save()