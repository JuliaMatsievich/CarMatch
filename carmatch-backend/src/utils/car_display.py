"""Форматирование данных автомобиля для отображения."""


def format_car_description(car) -> str | None:
    """
    Собирает строку описания в порядке: mark_name model_name (modification), body_type, year. Факты из description.
    Объект car может быть ORM Car или любой с атрибутами mark_name, model_name, modification, body_type, year, description.
    """
    mark = getattr(car, "mark_name", None) or ""
    model = getattr(car, "model_name", None) or ""
    modification = getattr(car, "modification", None)
    body_type = getattr(car, "body_type", None)
    year = getattr(car, "year", None)
    raw_desc = getattr(car, "description", None)
    facts = (raw_desc and str(raw_desc).strip()) or ""

    head = f"{mark} {model}".strip()
    if modification:
        head = f"{head} ({modification})"
    rest = []
    if body_type:
        rest.append(body_type)
    if year is not None:
        rest.append(str(year))
    if rest:
        head = f"{head}, {', '.join(rest)}"
    if facts:
        head = f"{head}. {facts}"
    return head if head else None
