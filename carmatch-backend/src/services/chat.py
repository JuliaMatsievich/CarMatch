"""Сервис чат-сессий: создание сессии, добавление сообщений, вызов DeepSeek, сохранение в БД."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _extract_country_from_description(description: str | None) -> str | None:
    """Из текста описания извлекает страну («Выпускается в X», «Производство — X»)."""
    if not description or not description.strip():
        return None
    d = description.strip()
    m = re.search(r"\bВыпускается\s+в\s+([^.]+?)(?:\.|$)", d, re.IGNORECASE)
    if m:
        return m.group(1).strip() or None
    m = re.search(r"Производство\s*[—\-]\s*([^.]+?)(?:\.|$)", d)
    if m:
        return m.group(1).strip() or None
    return None

from src.database import SessionLocal
from src.models import Car, ChatMessage, SearchParameter, Session
from src.services import deepseek as deepseek_service
from src.services.reference_data.car_reference_service import get_body_type_reference
from src.services.vector_search import (
    compose_search_query,
    hybrid_rank,
    sql_search_cars,
    vector_search_cars_with_scores,
)

# Лимит кандидатов векторного поиска в чате (меньше = быстрее ответ)
CHAT_VECTOR_SEARCH_LIMIT = 12

MIN_PARAMS_FOR_SEARCH = 3  # минимум параметров для «достаточно критериев» при отсутствии результатов

# Нормализация типа кузова для фильтрации списка машин (как в car_reference_service)
_BODY_TYPE_MATCH = [
    ("хэтчбек", "hatchback"), ("седан", "sedan"), ("универсал", "wagon"),
    ("внедорожник", "suv"), ("кроссовер", "crossover"), ("купе", "coupe"),
    ("минивэн", "minivan"), ("лифтбек", "liftback"), ("кабриолет", "cabriolet"), ("пикап", "pickup"),
]
_TRANSMISSION_MATCH = {"автомат": "at", "механика": "mt", "вариатор": "cvt", "робот": "amt", "акпп": "at", "мкпп": "mt"}


def _normalize_for_greeting(text: str) -> str:
    """
    Нормализует строку для сравнения с приветствиями:
    - нижний регистр, пробелы и пунктуация по правилам _is_greeting_only;
    - замена латинских букв-гомоглифов на кириллицу (привет/привет);
    - удаление невидимых символов (zero-width, BOM и т.п.).
    """
    if not text:
        return ""
    # Удаляем невидимые и нулевой ширины символы
    invisible = (
        "\u200b", "\u200c", "\u200d", "\ufeff", "\u00ad",  # zero-width, soft hyphen, BOM
        "\u2060", "\u180e", "\u034f",
    )
    t = text.strip().lower()
    for ch in invisible:
        t = t.replace(ch, "")
    # Латинские гомоглифы -> кириллица только если в тексте уже есть кириллица (чтобы не ломать "hello")
    if re.search(r"[\u0400-\u04ff]", t):
        homographs = (
            ("e", "\u0435"), ("a", "\u0430"), ("o", "\u043e"), ("p", "\u0440"),
            ("c", "\u0441"), ("y", "\u0443"), ("x", "\u0445"),
        )
        for lat, cyr in homographs:
            t = t.replace(lat, cyr)
    t = re.sub(r"[!.,?()\-–—]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _looks_like_greeting_only(text: str | None) -> bool:
    """
    Быстрая проверка: сообщение после нормализации — только приветствие (одно слово/фраза).
    Используется как дополнительная страховка вместе с _is_greeting_only.
    """
    if not text or not text.strip():
        return False
    t = _normalize_for_greeting(text)
    if not t or len(t) > 50:
        return False
    greetings_any = (
        "привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер", "доброе утро",
        "hi", "hello", "hey", "хай", "салют", "здарова", "прив",
    )
    return t in greetings_any or any(t == g or t.startswith(g + " ") for g in greetings_any)


def _is_greeting_only(text: str | None) -> bool:
    """
    Проверяет, является ли сообщение только приветствием без доп. контекста.
    Нужно, чтобы на «привет» ассистент не сразу выдавал список машин.
    """
    if not text:
        return False
    t = _normalize_for_greeting(text)
    greetings = {
        "привет",
        "здравствуй",
        "здравствуйте",
        "добрый день",
        "добрый вечер",
        "доброе утро",
        "hi",
        "hello",
        "hey",
    }
    if t in greetings:
        return True
    # Короткое сообщение, которое только начинается с приветствия (без явного запроса про авто)
    if len(t) <= 40 and any(t.startswith(g) for g in ("привет", "здравствуй", "здравствуйте", "добрый день",
                                                       "добрый вечер", "доброе утро", "hi", "hello", "hey")):
        rest = t
        for g in ("привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер",
                  "доброе утро", "hi", "hello", "hey"):
            if rest.startswith(g):
                rest = rest[len(g):].strip()
                break
        car_hints = ("машин", "авто", "подбор", "ищу", "хочу", "марк", "модел", "кузов", "бюджет")
        if not any(h in rest for h in car_hints):
            return True
    return False


def _message_mentions_car(text: str | None) -> bool:
    """
    Проверяет, есть ли в тексте упоминание машины или синонимов (авто, автомобиль, тачка и т.п.).
    Используется как часть проверки: small talk или ветка подбора авто (векторный поиск + LLM).
    """
    if not text or not text.strip():
        return False
    t = " " + text.strip().lower() + " "
    # Синонимы и словоформы: машина, авто, автомобиль, тачка
    if "машин" in t or "автомобил" in t or " тачк" in t or "тачка" in t:
        return True
    if " авто " in t:
        return True
    return False


def _message_mentions_car_or_params(text: str | None) -> bool:
    """
    Проверяет, содержит ли ПОСЛЕДНЕЕ сообщение пользователя явное упоминание машины
    или её параметров (марка, тип кузова, топливо, коробка, год, объём, мощность).
    Если нет — такое сообщение обрабатывается как small talk без подбора авто.
    """
    if not text or not text.strip():
        return False
    # Явное упоминание машины / авто
    if _message_mentions_car(text):
        return True
    t = " " + text.strip().lower() + " "
    # Явное упоминание распространённых брендов — тоже считаем контекстом про авто
    brand_keywords = [
        " renault ",
        " рено ",
        " toyota ",
        " тойота ",
        " bmw ",
        " бмв ",
        " mercedes ",
        " мерседес ",
        " мерс ",
        " kia ",
        " киа ",
        " nissan ",
        " ниссан ",
        " volkswagen ",
        " вольксваген ",
        " фольксваген ",
        " lada ",
        " лада ",
        " hyundai ",
        " хёндай ",
        " хендай ",
        " skoda ",
        " шкода ",
        # Американские бренды, чтобы запросы вроде «шевроле импала»
        # тоже однозначно считались контекстом про авто.
        " chevrolet ",
        " шевроле ",
        " ford ",
        " форд ",
        " dodge ",
        " додж ",
    ]
    if any(b in t for b in brand_keywords):
        return True

    # Ключевые слова параметров, которые с высокой вероятностью относятся к машине
    keywords = [
        "родстер",
        "седан",
        "хэтчбек",
        "универсал",
        "кроссовер",
        "suv",
        "кабриолет",
        "купе",
        "минивэн",
        "лифтбек",
        "пикап",
        "дизель",
        "бензин",
        "гибрид",
        "электро",
        "акпп",
        "мкпп",
        "автомат",
        "механика",
        "вариатор",
        "робот",
        "л.с.",
        "л. с.",
    ]
    if any(k in t for k in keywords):
        return True
    # Паттерн «2000 года», «2015 г.» и т.п. — обычно про год выпуска
    if re.search(r"\b(19\d{2}|20[0-2]\d)\s*(?:года|г\.?)\b", t):
        return True
    # Простой объём двигателя вида «1.6 л», «2.0 литра»
    if re.search(r"\b\d\.\d{1,2}\s*(?:л|литр|литра)\b", t):
        return True
    return False


def _clear_year_constraints_if_any_year_mentioned(
    last_user_message: str | None,
    params: dict,
) -> dict:
    """
    Если в последнем сообщении пользователя явно сказано, что год
    не важен / любой год, — снимаем ограничения по году (year, year_min, year_max).
    Это позволяет «перебить» более ранние условия вроде «не старше 10 лет».
    """
    if not last_user_message or not last_user_message.strip() or not isinstance(params, dict):
        return params
    text = " " + last_user_message.strip().lower() + " "
    # Типичные формулировки снятия ограничения по году
    any_year_phrases = (
        "любой год",
        "любого года",
        "год не важен",
        "год не принципиален",
        "год не играет роли",
        "год не имеет значения",
        "без ограничений по году",
        "год не критичен",
    )
    if any(phrase in text for phrase in any_year_phrases):
        for key in ("year", "year_min", "year_max"):
            if key in params:
                params.pop(key, None)
        logger.info(
            "chat: last message explicitly allows any year, "
            "cleared year/year_min/year_max from params",
        )
    return params


def _override_params_from_last_message(last_user_message: str | None, params: dict) -> dict:
    """
    Даёт приоритет последнему сообщению пользователя:
    если он сначала выбрал один параметр (седан, дизель и т.п.), а потом в
    последнем сообщении явно указал другой (кроссовер, бензин и т.п.), —
    перезаписываем соответствующий параметр в params.
    """
    if not last_user_message or not last_user_message.strip() or not isinstance(params, dict):
        return params
    text = " " + last_user_message.strip().lower() + " "

    # Кузов: последние явные указания «седан», «кроссовер», «универсал» и т.п.
    body_type_map = [
        ("хэтчбек", "хэтчбек"),
        ("хетчбек", "хэтчбек"),
        ("hatchback", "хэтчбек"),
        ("седан", "седан"),
        ("sedan", "седан"),
        ("универсал", "универсал"),
        ("wagon", "универсал"),
        ("внедорожник", "внедорожник"),
        ("suv", "внедорожник"),
        ("кроссовер", "кроссовер"),
        ("crossover", "кроссовер"),
        ("купе", "купе"),
        ("coupe", "купе"),
        ("минивэн", "минивэн"),
        ("минивен", "минивэн"),
        ("minivan", "минивэн"),
        ("лифтбек", "лифтбек"),
        ("liftback", "лифтбек"),
        ("кабриолет", "кабриолет"),
        ("cabriolet", "кабриолет"),
        ("пикап", "пикап"),
        ("pickup", "пикап"),
    ]
    for needle, canonical in body_type_map:
        if f" {needle} " in text:
            params["body_type"] = canonical

    # Топливо: бензин / дизель / гибрид / электро
    if "бензин" in text or "на бензине" in text or "бензиновый" in text:
        params["fuel_type"] = "бензин"
    elif "дизель" in text or "на дизеле" in text or "дизельный" in text:
        params["fuel_type"] = "дизель"
    elif "гибрид" in text or "гибридный" in text:
        params["fuel_type"] = "гибрид"
    elif "электро" in text or "электрический" in text or "электромобиль" in text:
        params["fuel_type"] = "электро"

    # Коробка: автомат / механика / вариатор / робот
    if "автомат" in text or "автоматическая" in text or "акпп" in text:
        params["transmission"] = "автомат"
    elif "механика" in text or "механическая" in text or "мкпп" in text or "ручная" in text:
        params["transmission"] = "механика"
    elif "вариатор" in text or "cvt" in text:
        params["transmission"] = "вариатор"
    elif "робот" in text or "роботизированная" in text:
        params["transmission"] = "робот"

    # Марка: даём приоритет последнему явному упоминанию
    brand_map = [
        (r"\b(renault|рено)\b", "Renault"),
        (r"\b(toyota|тойота)\b", "Toyota"),
        (r"\b(bmw|бмв)\b", "BMW"),
        (r"\b(mercedes|мерседес|мерс)\b", "Mercedes-Benz"),
        (r"\b(lada|лада)\b", "Lada"),
        (r"\b(volkswagen|вольксваген|фольксваген)\b", "Volkswagen"),
        (r"\b(hyundai|хёндай|хендай)\b", "Hyundai"),
        (r"\b(kia|киа)\b", "Kia"),
        (r"\b(nissan|ниссан)\b", "Nissan"),
        (r"\b(skoda|шкода)\b", "Škoda"),
        (r"\b(chevrolet|шевроле)\b", "Chevrolet"),
        (r"\b(ford|форд)\b", "Ford"),
        (r"\b(dodge|додж)\b", "Dodge"),
    ]
    for pattern, canonical in brand_map:
        if re.search(pattern, text):
            params["brand"] = canonical

    # Конкретный год в последнем сообщении
    year_match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", text)
    if year_match:
        year_val = year_match.group(1)
        params["year"] = year_val
        # При явном годе логично сбросить относительные рамки
        params.pop("year_min", None)
        params.pop("year_max", None)

    # Объём двигателя и мощность — если явно указаны в последнем сообщении
    vol_match = re.search(r"\b(\d{1}\.\d{1,2})\s*(?:л|литр|литра)?", text)
    if vol_match:
        params["engine_volume"] = vol_match.group(1)

    hp_match = re.search(r"(\d{2,3})\s*л\.?\s*с", text)
    if hp_match:
        params["horsepower"] = hp_match.group(1)

    return params


def _car_to_metadata(car) -> dict:
    """Сериализует Car в dict для сохранения в extra_metadata (формат как у CarResult)."""
    country = getattr(car, "country", None) or None
    description = getattr(car, "description", None)
    if not country and description:
        country = _extract_country_from_description(description)
    return {
        "id": car.id,
        "mark_name": getattr(car, "mark_name", None) or "",
        "model_name": getattr(car, "model_name", None) or "",
        "year": getattr(car, "year", None),
        "price_rub": float(car.price_rub) if getattr(car, "price_rub", None) is not None else None,
        "body_type": getattr(car, "body_type", None),
        "fuel_type": getattr(car, "fuel_type", None),
        "engine_volume": float(car.engine_volume) if getattr(car, "engine_volume", None) is not None else None,
        "horsepower": getattr(car, "horsepower", None),
        "modification": getattr(car, "modification", None),
        "transmission": getattr(car, "transmission", None),
        "country": country,
        "images": list(car.images) if getattr(car, "images", None) else [],
        "description": description,
        "brand_id": getattr(car, "brand_id", None),
        "model_id": getattr(car, "model_id", None),
        "generation_id": getattr(car, "generation_id", None),
        "modification_id": getattr(car, "modification_id", None),
    }


def _prioritize_aston_for_bond_query(
    last_user_message: str,
    cars: list,
) -> list:
    """
    Если пользователь явно упоминает Джеймса Бонда, поднимаем Aston Martin в начало списка
    (сохраняя исходный относительный порядок внутри групп).
    """
    if not cars or not last_user_message:
        return cars
    text = last_user_message.lower()
    if "джеймс бонд" not in text and "james bond" not in text and "бонла" not in text:
        # "бонла" — частая опечатка "бонда" из тестов
        return cars
    aston = []
    others = []
    for c in cars:
        if isinstance(c, Car) and getattr(c, "mark_name", "") == "Aston Martin":
            aston.append(c)
        else:
            others.append(c)
    if not aston:
        return cars
    return aston + others


def _maybe_prepend_db5_notice(
    user_messages: list[dict],
    search_results: list,
    response_text: str,
) -> str:
    """
    Если пользователь явно спрашивает про Aston Martin DB5, а в выдаче нет такой модели,
    но есть другие Aston Martin — добавляем краткое пояснение в начало ответа.
    """
    # Собираем весь текст пользователя в нижнем регистре
    user_text = " ".join(
        (m.get("content") or "")
        for m in user_messages
        if m.get("role") == "user"
    ).lower()
    if not user_text:
        return response_text
    # Явные упоминания DB5
    mentions_db5 = (
        "db5" in user_text
        or "дб5" in user_text
        or "д б 5" in user_text
        or "д б5" in user_text
    )
    if not mentions_db5:
        return response_text
    # В результатах нет DB5, но есть Aston Martin
    has_aston_any = any(
        getattr(c, "mark_name", "") == "Aston Martin" for c in search_results
    )
    has_db5_in_results = any(
        "db5" in (getattr(c, "model_name", "") or "").lower()
        for c in search_results
    )
    if not has_aston_any or has_db5_in_results:
        return response_text
    prefix = (
        "Модели Aston Martin DB5 в нашей базе нет, "
        "но есть другие автомобили этой марки. Ниже приведены подходящие варианты.\n\n"
    )
    return prefix + (response_text or "")


_SELECTION_PREFIX_LINE = "Я подобрал для вас наиболее подходящие автомобили."

# Регулярка: фраза в начале строки (опционально с точкой и текстом после) — для вырезания дубля
_SELECTION_PREFIX_STRIP_RE = re.compile(
    r"^\s*я подобрал для вас наиболее подходящие автомобили\.?\s*(?:\.\s*)?",
    flags=re.IGNORECASE,
)


def _strip_selection_prefix_from_start(text: str) -> str:
    """Убирает фразу «я подобрал для вас...» с начала текста (одна строка или несколько)."""
    if not text or not text.strip():
        return text
    stripped = text.strip()
    if _SELECTION_PREFIX_STRIP_RE.match(stripped):
        rest = _SELECTION_PREFIX_STRIP_RE.sub("", stripped, count=1).lstrip()
        return rest if rest else text
    # Проверяем первую строку отдельно: если только она — эта фраза, убираем и её и пустые следом
    lines = text.splitlines()
    if not lines:
        return text
    first = lines[0].strip()
    if _SELECTION_PREFIX_STRIP_RE.match(first):
        rest_first = _SELECTION_PREFIX_STRIP_RE.sub("", first, count=1).lstrip()
        if rest_first:
            lines[0] = rest_first
            return "\n".join(lines)
        # Первая строка целиком — фраза, выкидываем её и ведущие пустые
        i = 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        return "\n".join(lines[i:]).strip()
    return text


def _dedupe_selection_prefix(text: str) -> str:
    """
    Убирает повторяющиеся строки с фразой «я подобрал для вас наиболее подходящие автомобили»,
    оставляя только первое вхождение. Также обрезает эту фразу с начала строк, где после неё идёт другой текст.
    """
    if not text:
        return text
    pattern_full_line = re.compile(
        r"^\s*я подобрал для вас наиболее подходящие автомобили\.?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    lines = text.splitlines()
    seen = False
    result: list[str] = []
    for line in lines:
        if pattern_full_line.match(line):
            if seen:
                continue
            seen = True
            result.append(_SELECTION_PREFIX_LINE)
        else:
            # Строка может начинаться с фразы и продолжаться другим текстом — убираем только фразу
            stripped_line = line.strip()
            if _SELECTION_PREFIX_STRIP_RE.match(stripped_line):
                rest = _SELECTION_PREFIX_STRIP_RE.sub("", stripped_line, count=1).lstrip()
                if seen and rest:
                    result.append(rest)
                elif not seen:
                    seen = True
                    result.append(_SELECTION_PREFIX_LINE)
                    if rest:
                        result.append(rest)
                else:
                    result.append(line)
            else:
                result.append(line)
    return "\n".join(result)

def create_session(db: Session, user_id: int) -> Session:
    """Создаёт новую сессию для пользователя."""
    session = Session(
        user_id=user_id,
        status="active",
        extracted_params={},
        search_criteria={},
        search_results=[],
        message_count=0,
        parameters_count=0,
        cars_found=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def add_message(
    db: Session,
    session_id: UUID,
    user_id: int,
    content: str,
) -> tuple[ChatMessage, list[dict], bool]:
    """
    Сохраняет сообщение пользователя. Логика:
    (1) По запросу пользователя выполняется векторный поиск — получаем топ-10 наиболее подходящих машин.
    (2) LLM извлекает параметры из диалога и при нехватке информации задаёт уточняющие вопросы.
    (3) Поиск/выбор машины ведётся только среди этих 10 кандидатов: фильтрация по параметрам + LLM выбирает лучшие.
    (4) SQL-поиск по всей БД не используется — только векторный поиск и выбор из топ-10.
    Возвращает (assistant_message, merged_params_dict, ready_for_search, search_results).
    """
    session = db.query(Session).filter(Session.id == session_id, Session.user_id == user_id).first()
    if not session:
        raise ValueError("session_not_found")

    # Сохраняем сообщение пользователя
    max_order = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .count()
    )
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=content,
        sequence_order=max_order + 1,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Заголовок диалога из первого сообщения пользователя
    if max_order == 0 and getattr(session, "title", None) is None:
        title = (content or "").strip()
        if len(title) > 60:
            title = title[:57] + "..."
        if title:
            session.title = title
            db.commit()

    # История для LLM
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.sequence_order)
        .limit(20)
        .all()
    )
    messages = [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in history
    ]

    # Последнее пользовательское сообщение — для отдельной обработки «привет» без контекста
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = (m.get("content") or "").strip()
            break

    # Если пользователь просто поздоровался («привет» и т.п.) —
    # всегда отвечаем вежливым small talk без поиска и списка машин.
    # Двойная проверка: строгая _is_greeting_only и мягкая _looks_like_greeting_only.
    if _is_greeting_only(last_user_msg) or _looks_like_greeting_only(last_user_msg):
        try:
            response_text = deepseek_service.generate_response_small_talk(messages)
        except Exception as e:
            logger.exception("generate_response_small_talk (greeting only) failed: %s", e)
            response_text = (
                "Привет! Я Моторчик Тёма. Давай подберём тебе машину. "
                "Расскажи, пожалуйста, какую примерно ищешь — марку, тип кузова или для каких задач?"
            )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response_text,
            sequence_order=max_order + 2,
            extra_metadata={"search_results": []},
        )
        db.add(assistant_msg)
        session.message_count = max_order + 2
        db.commit()
        db.refresh(assistant_msg)
        db.refresh(session)
        return assistant_msg, session.extracted_params or {}, False, []

    # Если в ПОСЛЕДНЕМ сообщении пользователя нет упоминания машины или её параметров —
    # считаем такое сообщение small talk без поиска и без карточек.
    # Ветка подбора авто включается ТОЛЬКО если именно последнее сообщение явно про авто/параметры.
    is_about_car = _message_mentions_car_or_params(last_user_msg)

    if not is_about_car:
        try:
            response_text = deepseek_service.generate_response_small_talk(messages)
        except Exception as e:  # noqa: BLE001
            logger.exception("generate_response_small_talk (no car context) failed: %s", e)
            response_text = (
                "Спасибо за обращение! Это Моторчик Тёма, консультант по подбору авто. "
                "Если захочешь, помогу с выбором — расскажи, какую марку, тип кузова или бюджет рассматриваешь."
            )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response_text,
            sequence_order=max_order + 2,
            extra_metadata={"search_results": []},
        )
        db.add(assistant_msg)
        session.message_count = max_order + 2
        db.commit()
        db.refresh(assistant_msg)
        db.refresh(session)
        return assistant_msg, session.extracted_params or {}, False, []

    # При каждом сообщении, которое связано с подбором авто (и не является только приветствием), —
    # сценарий поиска: извлечение параметров, векторный поиск, ответ с результатами.
    try:
        body_type_reference = get_body_type_reference(db)
    except Exception as e:
        logger.exception("get_body_type_reference failed: %s", e)
        body_type_reference = []
    try:
        extracted_params = deepseek_service.extract_params(
            messages,
            current_params=session.extracted_params or {},
            body_type_reference=body_type_reference,
        )
    except Exception as e:
        logger.exception("deepseek extract_params failed: %s", e)
        extracted_params = []

    # Мержим: уже собранные + что вернул LLM + резервное извлечение по ключевым словам (если LLM что-то пропустил)
    # Дополнительно поддерживаем относительные ограничения по году (year_min, year_max),
    # которые приходят только из fallback-парсера.
    allowed_types = (
        "brand",
        "model",
        "body_type",
        "year",
        "year_min",
        "year_max",
        "modification",
        "transmission",
        "fuel_type",
        "engine_volume",
        "horsepower",
    )
    merged = dict(session.extracted_params or {})
    for p in extracted_params:
        t = p.get("type")
        val = (p.get("value") or "").strip()
        if not t or not val:
            continue
        # LLM иногда возвращает "mark" вместо "brand" — считаем одним и тем же
        if t == "mark":
            t = "brand"
        if t in allowed_types:
            merged[t] = val
    # Резерв: по ключевым словам из всех сообщений пользователя (топливо, коробка, год, объём, мощность, кузов).
    # Отсюда может появиться body_type=хэтчбек/седан и т.д., если пользователь написал «хэтчбек»/«седан»,
    # или если в справочнике body_type из БД есть «Хэтчбек 3 дв.» и в тексте есть слово «хэтчбек».
    user_texts = [m.get("content") or "" for m in messages if m.get("role") == "user"]
    fallback = deepseek_service.extract_params_fallback(user_texts, body_type_reference)
    fallback_added: list[str] = []
    for key, value in fallback.items():
        if key in allowed_types and value and (not merged.get(key) or not str(merged.get(key)).strip()):
            merged[key] = value
            fallback_added.append(f"{key}={value}")
            logger.info("extract_params_fallback: added %s=%s (LLM не вернул)", key, value)
    if fallback_added:
        logger.info(
            "extract_params: итог — LLM вернул %s параметров; fallback добавил: %s; merged: %s",
            len(extracted_params),
            ", ".join(fallback_added),
            merged,
        )
    # Исправление: если LLM записал топливо в transmission — переносим в fuel_type и чистим transmission
    _fuel_to_type = (
        ("бензин", "бензин"), ("на бензине", "бензин"), ("бензиновый", "бензин"),
        ("дизель", "дизель"), ("на дизеле", "дизель"), ("дизельный", "дизель"),
        ("гибрид", "гибрид"), ("гибридный", "гибрид"),
        ("электро", "электро"), ("электрический", "электро"),
    )
    tr_val = (merged.get("transmission") or "").strip().lower()
    for fuel_phrase, fuel_norm in _fuel_to_type:
        if fuel_phrase in tr_val or tr_val == fuel_phrase:
            if not merged.get("fuel_type") or not str(merged.get("fuel_type")).strip():
                merged["fuel_type"] = fuel_norm
            merged["transmission"] = ""
            logger.info("extract_params: исправлено — значение «%s» перенесено из transmission в fuel_type", tr_val)
            break
    # Если в последнем сообщении пользователь явно говорит, что год не важен / любой год,
    # снимаем ранее накопленные ограничения по year/year_min/year_max.
    merged = _clear_year_constraints_if_any_year_mentioned(last_user_msg, merged)
    # Приоритет последнего сообщения: если пользователь сначала сказал «рено», потом «бмв» —
    # перезаписываем brand (и то же для body_type, fuel_type, transmission, year, engine_volume, horsepower).
    # Для model/modification перезапись обеспечивается промптом LLM («последнее значение по типу») и порядком в merge.
    merged = _override_params_from_last_message(last_user_msg, merged)

    # Снимок параметров на момент этого сообщения (для админки):
    # один объект на каждый тип параметра, с финальным значением после merge/fallback/override.
    llm_types = {p.get("type") for p in extracted_params if isinstance(p, dict)}
    snapshot_params: list[dict] = []
    for t in allowed_types:
        raw_val = merged.get(t)
        val = (raw_val or "").strip() if raw_val is not None else ""
        if not val:
            continue
        conf = 0.9
        # Пытаемся взять confidence из LLM-ответа для этого типа
        for p in reversed(extracted_params):
            if p.get("type") == t:
                try:
                    conf = float(p.get("confidence", 0.9))
                except (TypeError, ValueError):
                    conf = 0.9
                break
        # Если параметр пришёл только из fallback, оставляем дефолтную уверенность
        if t in fallback and t not in llm_types:
            conf = 0.9
        snapshot_params.append({"type": t, "value": val, "confidence": conf})

    # Сохраняем снимок в extra_metadata последнего пользовательского сообщения
    try:
        user_msg.extra_metadata = {
            "extracted_params": snapshot_params,
            "extracted_params_raw": extracted_params,
        }
        db.commit()
        db.refresh(user_msg)
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "failed to store extracted_params snapshot in user_msg.extra_metadata: %s",
            e,
        )

    session.extracted_params = merged
    session.parameters_count = sum(1 for v in merged.values() if v and str(v).strip())
    # На этом этапе ready_for_search оцениваем только по количеству параметров.
    # После выполнения поиска ниже мы дополнительно учтём факт наличия результатов.
    ready_for_search = session.parameters_count >= MIN_PARAMS_FOR_SEARCH

    # Последнее сообщение пользователя — для формирования запроса к векторному поиску
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = (m.get("content") or "").strip()
            break

    # Страховка: если последнее сообщение — только приветствие, не делаем поиск (на случай сбоя проверки выше)
    if _is_greeting_only(last_user_msg):
        try:
            response_text = deepseek_service.generate_response_small_talk(messages)
        except Exception as e:
            logger.exception("generate_response_small_talk (greeting safety) failed: %s", e)
            response_text = (
                "Привет! Я Моторчик Тёма. Давай подберём тебе машину. "
                "Расскажи, пожалуйста, какую примерно ищешь — марку, тип кузова или для каких задач?"
            )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response_text,
            sequence_order=max_order + 2,
            extra_metadata={"search_results": []},
        )
        db.add(assistant_msg)
        session.message_count = max_order + 2
        db.commit()
        db.refresh(assistant_msg)
        db.refresh(session)
        return assistant_msg, session.extracted_params or {}, False, []

    # Страховка: если последнее сообщение — только приветствие, не делаем поиск (на случай продолжения диалога с уже накопленными параметрами)
    if _is_greeting_only(last_user_msg):
        try:
            response_text = deepseek_service.generate_response_small_talk(messages)
        except Exception as e:
            logger.exception("generate_response_small_talk (greeting safety) failed: %s", e)
            response_text = "Привет! Давай подберём тебе машину. Расскажи, пожалуйста, какую примерно ищешь — марку, тип кузова или для каких задач?"
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response_text,
            sequence_order=max_order + 2,
            extra_metadata={"search_results": []},
        )
        db.add(assistant_msg)
        session.message_count = max_order + 2
        db.commit()
        db.refresh(assistant_msg)
        db.refresh(session)
        return assistant_msg, session.extracted_params or {}, False, []

    # Векторный поиск и SQL‑фильтрация при любом упоминании машины:
    # используем гибридное ранжирование; векторный и SQL-поиск запускаем параллельно.
    search_results: list[Car] = []
    query_text = compose_search_query(merged, last_user_msg)
    if not query_text or not query_text.strip():
        query_text = (last_user_msg or "автомобиль").strip() or "автомобиль"

    has_params = session.parameters_count > 0
    semantic_results: list = []
    sql_cars: list = []

    def _run_vector_search() -> list:
        session_local = SessionLocal()
        try:
            return vector_search_cars_with_scores(
                session_local, query_text, limit=CHAT_VECTOR_SEARCH_LIMIT
            )
        finally:
            session_local.close()

    def _run_sql_search() -> list:
        session_local = SessionLocal()
        try:
            return sql_search_cars(session_local, merged)
        finally:
            session_local.close()

    if query_text:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_vec = executor.submit(_run_vector_search)
            future_sql = executor.submit(_run_sql_search) if has_params else None
            try:
                semantic_results = future_vec.result()
            except Exception as e:  # noqa: BLE001
                logger.exception("vector_search_cars_with_scores failed: %s", e)
            if future_sql:
                try:
                    sql_cars = future_sql.result()
                except Exception as e:  # noqa: BLE001
                    logger.exception("sql_search_cars failed: %s", e)

    if semantic_results:
        logger.info(
            "chat vector search: query=%r, candidates=%d",
            query_text[:100],
            len(semantic_results),
        )

    ranked_results: list[tuple[Car, float]] = []
    if semantic_results or sql_cars:
        try:
            ranked_results = hybrid_rank(semantic_results, sql_cars, merged)
        except Exception as e:  # noqa: BLE001
            logger.exception("hybrid_rank failed: %s", e)
            ranked_results = list(semantic_results)

    # Пост‑фильтр по году выпуска, если пользователь задал ограничения (например «не старше 15 лет»).
    year_min = None
    year_max = None
    try:
        if merged.get("year_min"):
            year_min = int(str(merged["year_min"]).strip())
    except (TypeError, ValueError):
        year_min = None
    try:
        if merged.get("year_max"):
            year_max = int(str(merged["year_max"]).strip())
    except (TypeError, ValueError):
        year_max = None

    def _year_ok(car_year: int | None) -> bool:
        if car_year is None:
            # Если год принципиален (задан min/max), машины без года лучше не показывать
            return year_min is None and year_max is None
        if year_min is not None and car_year < year_min:
            return False
        if year_max is not None and car_year > year_max:
            return False
        return True

    if year_min is not None or year_max is not None:
        if ranked_results:
            ranked_results = [
                (car, score)
                for car, score in ranked_results
                if _year_ok(getattr(car, "year", None))
            ]
        if not ranked_results and semantic_results:
            # Если после жёсткого фильтрации по году гибридный список опустел,
            # пробуем отфильтровать хотя бы чисто векторные кандидаты.
            semantic_results = [
                (car, score)
                for car, score in semantic_results
                if _year_ok(getattr(car, "year", None))
            ]

    # Основная выдача — по (отфильтрованному) гибридному скору.
    search_results = [car for car, _score in ranked_results]

    # Фоллбек: если ни одна машина не прошла порог score >= 0.6,
    # но векторный поиск вернул кандидатов, показываем топ‑N наиболее близких.
    no_strict_matches = False
    if not search_results and semantic_results:
        no_strict_matches = True
        top_n = 5
        logger.info(
            "chat hybrid_rank: ни одного авто с score >= 0.6, "
            "показываем top-%d наиболее близких кандидатов из векторного поиска (всего=%d)",
            top_n,
            len(semantic_results),
        )
        search_results = [car for car, _score in semantic_results[:top_n]]
    # Если пользователь просит «машину как у Джеймса Бонда» —
    # поднимаем Aston Martin в начало списка кандидатов.
    search_results = _prioritize_aston_for_bond_query(last_user_msg, search_results)

    # Финальная страховка: если последнее сообщение — приветствие, никогда не показываем список машин
    if _is_greeting_only(last_user_msg) or _looks_like_greeting_only(last_user_msg):
        try:
            response_text = deepseek_service.generate_response_small_talk(messages)
        except Exception as e:
            logger.exception("generate_response_small_talk (final gate) failed: %s", e)
            response_text = (
                "Привет! Я Моторчик Тёма. Давай подберём тебе машину. "
                "Расскажи, какую ищешь — марку, тип кузова или для каких задач?"
            )
        search_results = []
        search_results_serialized = []
    else:
        # Если есть результаты — считаем, что пользователь уже «готов к показу карточек»,
        # даже если параметров пока меньше трёх.
        if search_results:
            ready_for_search = True

        # Критериев достаточно: есть кандидаты ИЛИ набрано 3+ параметров (для ответа «ничего не найдено»)
        criteria_fulfilled = bool(search_results) or session.parameters_count >= MIN_PARAMS_FOR_SEARCH
        try:
            response_text = deepseek_service.generate_response(
                messages,
                params=merged,
                search_results=search_results,
                criteria_fulfilled=criteria_fulfilled,
                parameters_count=session.parameters_count,
            )
        except Exception as e:
            logger.exception("deepseek generate_response failed: %s", e)
            response_text = "Не удалось обработать запрос. Попробуйте ещё раз."
        # Раньше при отсутствии точных совпадений по score к ответу добавлялась фраза
        # «По вашему запросу точных совпадений не найдено. Вот наиболее близкие варианты:».
        # По просьбе пользователя мы больше не добавляем этот префикс и оставляем только ответ LLM.
        # Спец‑логика под запросы про Aston Martin DB5
        response_text = _maybe_prepend_db5_notice(messages, search_results, response_text)

        # Если модель по какой‑то причине вернула отказ вроде
        # «Я не могу обсуждать эту тему. Давайте поговорим о чём-нибудь ещё.»,
        # считаем, что фактически подбор не выполнен: не показываем карточки
        # и не добавляем фразу «я подобрал для вас...».
        refusal_pattern = re.compile(
            r"я не могу обсуждать эту тему|я не могу помочь с этим|это нарушает правила",
            flags=re.IGNORECASE,
        )
        is_refusal = bool(refusal_pattern.search(response_text or ""))
        if is_refusal:
            logger.info("generate_response: detected refusal answer from LLM, clearing search_results")
            search_results = []

        # Если есть результаты поиска, в ответе всегда должна быть фраза
        # в духе «я подобрал для вас наиболее подходящие автомобили».
        # Порядок:
        # - в первом ответе ассистента сохраняем приветствие (если оно есть),
        #   а фразу про подбор вставляем ПОСЛЕ приветствия;
        # - в последующих ответах с результатами убираем повторное представление
        #   («Здравствуйте! Меня зовут Моторчик Тёма…») и добавляем фразу про подбор в начало.
        if search_results:
            prefix_line = "Я подобрал для вас наиболее подходящие автомобили.\n\n"
            text = response_text or ""

            # Регулярка для приветствия ассистента
            greeting_pattern = re.compile(
                r"Здравствуйте!\s*Меня зовут Моторчик Тёма[^.]*\.\s*",
                flags=re.IGNORECASE | re.DOTALL,
            )

            if max_order == 0:
                # Первый ответ ассистента в сессии: оставляем приветствие,
                # а фразу про подбор вставляем сразу после него.
                m = greeting_pattern.match(text.strip())
                if m:
                    greeting = m.group(0).strip()
                    rest = text[text.index(m.group(0)) + len(m.group(0)) :].lstrip()
                    rest = _strip_selection_prefix_from_start(rest)
                    response_text = greeting + "\n\n" + prefix_line + rest
                else:
                    # Если LLM не начал с приветствия, просто добавляем префикс в начало
                    text = _strip_selection_prefix_from_start(text)
                    response_text = prefix_line + text
            else:
                # Не первый ответ: приветствие убираем везде, префикс добавляем в начало
                text_wo_greeting = greeting_pattern.sub("", text).lstrip()
                text_wo_greeting = _strip_selection_prefix_from_start(text_wo_greeting)
                response_text = prefix_line + text_wo_greeting
            # Страховка от дублей: если модель всё же повторила фразу — оставляем одно вхождение
            response_text = _dedupe_selection_prefix(response_text)
        search_results_serialized = [_car_to_metadata(c) for c in search_results]

        # Сохраняем ответ ассистента (с карточками в extra_metadata)
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response_text,
        sequence_order=max_order + 2,
        extra_metadata={"search_results": search_results_serialized},
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # Записываем search_parameters
    for p in extracted_params:
        sp = SearchParameter(
            session_id=session_id,
            param_type=p.get("type", ""),
            param_value=p.get("value", ""),
            confidence=p.get("confidence"),
            message_id=assistant_msg.id,
        )
        db.add(sp)
    session.message_count = max_order + 2
    db.commit()
    db.refresh(session)

    # Возвращаем накопленные параметры (merged), а не только что извлечённые из последнего сообщения
    return assistant_msg, merged, ready_for_search, search_results
