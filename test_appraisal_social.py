from identity.appraisal_engine import AppraisalEngine


engine = AppraisalEngine()

# Похвала (старые и новые маркеры)
result = engine.appraise_interaction(
    message="молодец, ты лучший, спасибо большое"
)

assert result["trigger"] == "positive_social_feedback", result
assert result["changes"].get("joy", 0) > 0
assert result["changes"].get("satisfaction", 0) > 0

# Обидные слова (новые маркеры вне старого списка)
result = engine.appraise_interaction(
    message="ты идиот, ты мне надоел"
)

assert result["trigger"] == "negative_social_feedback", result
assert result["changes"].get("frustration", 0) > 0
assert result["changes"].get("sadness", 0) > 0

# Противоречие во входящем сообщении
result = engine.appraise_interaction(
    message="ты неправ, всё наоборот"
)

assert result["trigger"] == "contradiction_feedback", result
assert result["changes"].get("surprise", 0) > 0
assert result["changes"].get("uncertainty", 0) > 0

# Нейтральное сообщение не меняет эмоции
result = engine.appraise_interaction(
    message="как дела"
)

assert result["trigger"] == "neutral_interaction", result
assert result["changes"] == {}, result

print("ALL PASS")
