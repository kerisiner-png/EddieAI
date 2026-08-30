from memory.provenance import (
    VALID_SOURCES,
    SOURCE_WEIGHTS,
    validate_source,
    source_weight,
)

# 1. Провенанс сна добавлен в валидные источники
assert "DREAM" in VALID_SOURCES
assert "DREAM_INTERPRETATION" in VALID_SOURCES

# 2. Веса сна: ниже яви (0.25 / 0.35 против 1.0)
assert SOURCE_WEIGHTS["DREAM"] == 0.25
assert SOURCE_WEIGHTS["DREAM_INTERPRETATION"] == 0.35

# 3. Существующие источники не тронуты
assert SOURCE_WEIGHTS["SELF_EXPERIENCE"] == 1.0
assert SOURCE_WEIGHTS["SELF_OBSERVATION"] == 0.8
assert SOURCE_WEIGHTS["SELF_ACTION"] == 1.0

# 4. validate_source принимает новые и отклоняет неизвестные
assert validate_source("DREAM") == "DREAM"
assert validate_source("DREAM_INTERPRETATION") == "DREAM_INTERPRETATION"

try:
    validate_source("NOT_A_SOURCE")
    raise SystemExit("validate_source не отклонил неизвестный источник")
except ValueError:
    pass

# 5. source_weight выдаёт вес сна
assert source_weight("DREAM") == 0.25
assert source_weight("DREAM_INTERPRETATION") == 0.35

print("ALL PASS")