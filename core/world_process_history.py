from collections import Counter, deque


class WorldProcessHistory:
    """
    Хранит скользящее окно снимков процессов во времени
    и считает частоту появления каждого процесса.

    Позволяет получить картину «что часто происходит на ПК»
    вместо единичного снимка.
    """

    def __init__(self, window=10):
        self.window = max(1, int(window))
        self.snapshots = deque(maxlen=self.window)

    def record(self, snapshot):
        if snapshot.get("status") != "OK":
            return
        procs = snapshot.get("top_processes") or []
        names = set()
        for proc in procs:
            name = proc.get("name")
            if name:
                names.add(name)
        if names:
            self.snapshots.append(names)

    def frequency(self):
        counter = Counter()
        for snap in self.snapshots:
            for name in snap:
                counter[name] += 1
        return dict(counter)

    def frequent_processes(self, top=5):
        freq = self.frequency()
        ranked = sorted(
            freq.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked[:max(1, int(top))]

    def summary_text(self, top=5):
        ranked = self.frequent_processes(top)
        if not ranked:
            return ""
        names = ", ".join(
            name
            for name, _count in ranked
        )
        return f"за последние снимки чаще всего: {names}"
