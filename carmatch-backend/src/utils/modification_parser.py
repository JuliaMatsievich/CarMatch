"""
Парсинг строки модификации автомобиля (например "1.6d MT 90 л.с.") в отдельные поля:
fuel_type, engine_volume, horsepower, transmission (тип коробки).
"""

import re
from decimal import Decimal
from typing import Optional


# Паттерны для типа коробки (латиница и кириллица)
TRANSMISSION_PATTERN = re.compile(
    r"\b(MT|AMT|AT|CVT|DSG|DCT|РКПП|АКПП|AKP|MKP|Вариатор|Робот)\b",
    re.IGNORECASE,
)
# Объём двигателя: число типа 1.4, 1.6, 2.0 (опционально с "d" для дизеля)
ENGINE_VOLUME_PATTERN = re.compile(
    r"(?:^|\s)(\d{1}\.\d{1,2})d?(?:\s|MT|AMT|AT|CVT|$)",
    re.IGNORECASE,
)
# Мощность: цифры перед "л.с."
HORSEPOWER_PATTERN = re.compile(r"(\d+)\s*л\.?\s*с\.?", re.IGNORECASE)


def parse_modification_string(modification: Optional[str]) -> dict:
    """
    Парсит строку модификации и возвращает словарь с полями:
    fuel_type, engine_volume, horsepower, transmission.

    Логика fuel_type:
    - "hyb" в строке -> гибрид
    - буква d после цифр (например 1.6d) -> дизель
    - если нет цифр объёма и нет "л.с." -> электро
    - иначе -> бензин
    """
    result = {
        "fuel_type": None,
        "engine_volume": None,
        "horsepower": None,
        "transmission": None,
    }
    if not modification or not str(modification).strip():
        return result

    s = str(modification).strip()
    s_lower = s.lower()

    # Тип коробки — большие буквы (MT, AMT, CVT, ...)
    tr_match = TRANSMISSION_PATTERN.search(s)
    if tr_match:
        result["transmission"] = tr_match.group(1).upper() if tr_match.group(1).isascii() else tr_match.group(1)

    # Объём двигателя — число типа 1.4, 1.6d перед MT/AMT или в начале
    vol_match = ENGINE_VOLUME_PATTERN.search(s)
    if not vol_match:
        vol_match = re.search(r"(?:^|\s)(\d{1}\.\d{1,2})d?(?=\s|$)", s, re.IGNORECASE)
    if vol_match:
        try:
            result["engine_volume"] = Decimal(vol_match.group(1))
        except (ValueError, TypeError):
            pass

    # Мощность — цифра перед "л.с."
    hp_match = HORSEPOWER_PATTERN.search(s)
    if hp_match:
        try:
            result["horsepower"] = int(hp_match.group(1))
        except (ValueError, TypeError):
            pass

    # Топливо
    if "hyb" in s_lower:
        result["fuel_type"] = "гибрид"
    elif re.search(r"\d+\.?\d*d\b", s_lower):
        result["fuel_type"] = "дизель"
    elif not re.search(r"\d+\.?\d*", s) and "л.с." not in s_lower and "л.с" not in s_lower:
        result["fuel_type"] = "электро"
    else:
        result["fuel_type"] = "бензин"

    return result
