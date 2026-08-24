from identity.user_statement_detector import (
    UserStatementDetector,
)


detector = UserStatementDetector()

tests = [
    "Мне очень нравится космос.",
    "Я люблю баскетбол.",
    "Я часто читаю про NASA.",
    "Мне интересны космические миссии.",
    "Я предпочитаю средний бросок.",
    "Я обычно играю вечером.",
    "NASA запустила новую миссию.",
    "Космос сегодня выглядит интересно.",
    "Мы вчера говорили про баскетбол.",
]

for text in tests:
    print()
    print("TEXT:", text)
    print("RESULT:", detector.detect(text))
