from pathlib import Path
from identity.self_model import SelfModel


class FakeSelfState:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


class TestSelfModelOwnership:
    def setup_method(self):
        self.ss = FakeSelfState()
        self.model = SelfModel(self.ss)
        self.model.build([], agent=None)

    def test_ownership_in_model(self):
        snapshot = self.model.snapshot()
        assert "ownership" in snapshot

    def test_ownership_keys(self):
        snapshot = self.model.snapshot()
        ownership = snapshot["ownership"]
        assert "mine" in ownership
        assert "eddies" in ownership
        assert "installed" in ownership
        assert "system" in ownership
        assert "installing" in ownership

    def test_ownership_render(self):
        text = self.model.render()
        assert "МОИ ГРАНИЦЫ" in text
        assert "EddieAI" in text or "мо" in text.lower()
        assert "Эдди" in text or "Eddie" in text

    def test_ownership_values_content(self):
        snapshot = self.model.snapshot()
        ownership = snapshot["ownership"]
        assert "EddieAI" in ownership["mine"]
        assert "спроса" in ownership["eddies"]
        assert "пользоваться" in ownership["installed"]
        assert "не меняю" in ownership["system"]
        assert "спрашиваю" in ownership["installing"]
