from memory.source_evaluator import SourceEvaluator


def _accepted(url, title, query, threshold=0.45):
    ev = SourceEvaluator(acceptance_threshold=threshold)
    return [
        item.accepted
        for item in ev.evaluate(
            [{"url": url, "title": title}], query
        )
    ][0]


def test_habr_accepted_for_python_query():
    assert (
        _accepted(
            "https://habr.com/ru/articles/812345/",
            "Как работает dict в Python: внутреннее устройство",
            "как работает dict в python",
        )
        is True
    )


def test_stackoverflow_accepted_for_python_query():
    assert (
        _accepted(
            "https://stackoverflow.com/questions/123/dict",
            "How does dict work in Python",
            "how does dict work python",
        )
        is True
    )


def test_low_trust_still_rejected():
    assert (
        _accepted(
            "https://youtube.com/watch?v=1",
            "Всё о космосе",
            "космос",
        )
        is False
    )


if __name__ == "__main__":
    test_habr_accepted_for_python_query()
    test_stackoverflow_accepted_for_python_query()
    test_low_trust_still_rejected()
    print("ALL OK")
