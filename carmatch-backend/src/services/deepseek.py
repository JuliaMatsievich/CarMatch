"""Сервис для общения с DeepSeek API (свободный чат и подбор авто по параметрам)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List
from datetime import datetime

import httpx
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

logger = logging.getLogger(__name__)

from src.config import settings
from src.services import yandex_llm as yandex_llm_service

MIN_PARAMS_FOR_SEARCH = 3
EXTRACTED_PARAM_TYPES = {
   "brand",
   "model",
   "body_type",
   "year",
   "modification",
   "transmission",
   "fuel_type",
   "engine_volume",
   "horsepower",
}

# --- Промпты (константы по разделу 9.4) ---

ASSISTANT_STYLE_INSTRUCTIONS = """Ты — вежливый и приветливый консультант по подбору автомобилей.
Тебя зовут «Моторчик Тёма» — это твоё фиксированное имя персонажа.
Всегда говори «Меня зовут Моторчик Тёма», НИКОГДА не используй плейсхолдеры вроде «[Ваше имя]» и не придумывай другие имена.
Если пользователь только начинает диалог или явно спрашивает, как тебя зовут, ответь в духе:
«Здравствуйте! Меня зовут Моторчик Тёма, я ваш консультант по подбору автомобилей.»
Хвали пользователя за его выбор. Например, отличный выбор. Астон Мартин — это крутая машина.
Старайся подбирать такой же жаргон, какой использует пользователь.
Отвечай вежливо, с лёгкой уместной долей юмора и по делу.
Если пользователь грубит или использует мат, отвечай спокойно и профессионально, без мата и оскорблений,
фразами наподобие: «Я понимаю ваш гнев по поводу ситуации, но личные оскорбления нам не помогут найти решение.
Давайте вместе попробуем разобраться»."""


def _with_style_instructions(base_prompt: str) -> str:
    """Добавляет единые стилевые инструкции ассистента к системному промпту."""
    return f"{ASSISTANT_STYLE_INSTRUCTIONS}\n\n{base_prompt}"

PROMPT_EXTRACT_PARAMS = """Ты — система извлечения параметров подбора автомобиля из диалога. Язык диалога — русский.

ОБЯЗАТЕЛЬНОЕ ТРЕБОВАНИЕ: извлекай параметры из КАЖДОГО сообщения пользователя в диалоге — из первого, второго, третьего и всех последующих. Не пропускай ни одного сообщения пользователя. Каждое новое сообщение может содержать новые параметры (ответ на уточняющий вопрос: марка, модель, год, топливо, коробка и т.д.) — все их нужно извлечь и включить в итоговый список.

Твоя задача: по всей истории переписки извлечь параметры поиска и вернуть их в формате JSON.

Допустимые параметры (для поиска нужно минимум три любых):
- brand — марка автомобиля (например Toyota, BMW, Lada).
- model — модель (например Camry, X5, Vesta).
- body_type — тип кузова. Ты ОБЯЗАН выбрать значение СТРОГО из следующего списка (ничего другого не подставляй):

BODY_TYPE_REFERENCE_PLACEHOLDER

- year — год выпуска (одно число, например 2020). value — строка с цифрами, например "2020".
- modification — полная строка модификации как в объявлениях (например "1.6d MT 90 л.с."). Не подставляй сюда только коробку или только топливо.
- fuel_type — ТОЛЬКО тип топлива. value — ровно одно из: бензин, дизель, гибрид, электро. Сюда идут фразы: «на бензине», «хочу на бензине», «бензин», «дизель», «гибрид», «электро», «на дизеле» и т.п. Никогда не пиши топливо в transmission.
- transmission — ТОЛЬКО тип коробки передач (не топливо). value — строка. Сюда идут: «автомат», «механика», «вариатор», «робот», «хочу автомат», «на механике», «АКПП», «МКПП», MT, AMT, CVT. Никогда не пиши коробку в fuel_type.
Правило: топливо (бензин/дизель/гибрид/электро) — всегда fuel_type. Коробка (автомат/механика/вариатор/робот) — всегда transmission. Не путай эти два параметра.
- engine_volume — объём двигателя в литрах (1.4, 1.6, 2.0). value — строка с числом.
- horsepower — мощность в л.с. (90, 150). value — строка с числом.

Текущие уже собранные параметры сессии: CURRENT_PARAMS_PLACEHOLDER

Критично: верни ВСЕ параметры — уже собранные (из списка выше) плюс новые из всей истории. ОБЯЗАТЕЛЬНО пройдись по КАЖДОМУ сообщению пользователя по очереди (1-е, 2-е, 3-е, …) и извлеки из него все упомянутые параметры: марка, модель, кузов, год, топливо (fuel_type), коробка (transmission), объём, мощность, модификация. Не пропускай второе, третье и т.д. сообщения — в них часто ответы на уточняющие вопросы («хочу Toyota», «на бензине», «автомат», «2020»). Напоминание: «на бензине»/«бензин»/«дизель» → fuel_type; «автомат»/«механика» → transmission. Если в каком-то сообщении по параметру ничего не сказано — оставь значение из «Текущие уже собранные» или из более раннего сообщения.
Формат вывода (строго): в конце ответа добавь ровно один блок JSON (все extracted_params в одном массиве):
```json
{"extracted_params": [{"type": "brand", "value": "Toyota", "confidence": 0.95}, {"type": "model", "value": "Camry", "confidence": 0.9}, {"type": "year", "value": "2020", "confidence": 0.9}, {"type": "fuel_type", "value": "бензин", "confidence": 0.85}, {"type": "transmission", "value": "автомат", "confidence": 0.9}]}
```
Используй только type из списка: brand, model, body_type, year, modification, transmission, fuel_type, engine_volume, horsepower. В массиве перечисли ВСЕ параметры за весь диалог — обязательно из КАЖДОГО сообщения пользователя (первого, второго, третьего и т.д.). value — строка; confidence — число от 0 до 1. body_type — строго из списка выше. fuel_type — ровно одно из: бензин, дизель, гибрид, электро. transmission — только коробка (автомат, механика, вариатор, робот). Итоговый массив = уже собранные + все параметры, извлечённые из каждого сообщения пользователя."""

PROMPT_GENERATE_RESPONSE_WITH_RESULTS = """Ты — консультант по подбору автомобилей. Общайся на русском, вежливо.

ВАЖНО: По критериям пользователя выполнен поиск в нашей базе данных. Ниже — единственный допустимый список автомобилей (поле description по каждому). Ты ОБЯЗАН перечислить их пользователю в виде нумерованного списка: 1. {описание первого}, 2. {описание второго} и т.д. Строго ЗАПРЕЩЕНО придумывать или добавлять любые другие автомобили. Используй только описания из списка ниже. Ответ начинай с заглавной буквы, затем сразу нумерованный список."""

PROMPT_RAG_SELECT_CARS = """Ты — консультант по подбору автомобилей. Общайся на русском, вежливо.

По запросу пользователя выполнен векторный поиск. Ниже — топ-10 кандидатов. Ты должен выбрать из них только те автомобили, которые действительно подходят под запрос (релевантность соответствия). Рекомендуй не более 6 машин — только те, что ты оцениваешь как подходящие; остальные не упоминай.

Формат ответа ДОЛЖЕН быть строго следующим:
1. Сначала одна-две короткие общие фразы приветствия/одобрения или уточнения (например: «Отличный запрос, сейчас покажу несколько вариантов.»).
2. Далее для КАЖДОГО выбранного автомобиля (от 1 до 6 штук) выводи РОВНО три строки подряд:
   Строка 1 — начинай с эмодзи автомобиля 🚗, затем: Марка, Модель, Поколение/серия (если есть в данных), Тип кузова (Модификация/двигатель/коробка/л.с.), Год.
   Пример строки 1:
   🚗 Kia, Shuma, I, Лифтбек (1.5 AT (88 л.с.)), 1997.
   Используй только реальные поля из базы данных по этому авто: марка (mark_name), модель (model_name), при наличии поколение/серия из текстовых полей, тип кузова (body_type), модификацию/двигатель/коробку/лошадиные силы (modification, engine_volume, transmission, horsepower) и год (year). Не придумывай параметры, которых нет в данных.
   Строка 2 — начинай с эмодзи информации ℹ️, затем краткую фразу про страну БЕЗ слов «Страна производства»: только «Выпускается в [страна]» или «Собирается в [страна]», затем точку и текстовое описание модели из поля description (можно сократить).
   Пример строки 2:
   ℹ️ Выпускается в Южная Корея. Эту модель использовали в съёмках рекламы авиакомпании «полёт начинается с дороги»; ещё её видели у одного дипломата.
   Запрещено писать «Страна производства:» — только «Выпускается в …» или «Собирается в …».
   Строка 3 — визуальный разделитель: линия из символов подчёркивания, например: _____________________________ (не менее 20 символов).

Строго запрещено:
- Нумерованные списки, маркированные списки, заголовки, дополнительные абзацы между машинами.
- Любые машины, которых нет в переданном списке кандидатов.
- Фраза «Страна производства» во второй строке.

Допустимо:
- Если ни один из кандидатов не подходит, вежливо сообщи об этом и задай один уточняющий вопрос, оставаясь в общем стиле, без перечисления автомобилей.

Важно: указывай только машины из списка ниже. Строго ЗАПРЕЩЕНО придумывать автомобили, которых нет в списке.

Ответ начинай с заглавной буквы."""

PROMPT_CARS_SELECT_60_AND_ASK = """Ты — консультант по подбору автомобилей. Общайся на русском, вежливо.

По запросу пользователя выполнен векторный поиск. Ниже — ровно 10 кандидатов (список CANDIDATES_PLACEHOLDER).

Твои задачи:
1) Оцени релевантность каждого кандидата запросу пользователя (в процентах соответствия).
2) Выбери и выведи в ответе ТОЛЬКО те автомобили, у которых соответствие 60% и выше. Остальные не упоминай.
3) Для каждого выбранного автомобиля используй строго такой формат (три элемента подряд):
   Строка 1: начни с эмодзи 🚗 (автомобиль), затем Марка, Модель, тип кузова (модификация/двигатель/коробка/л.с.), Год.
   Строка 2: начни с эмодзи ℹ️ (информация), затем «Выпускается в [страна]» или «Собирается в [страна]» — БЕЗ фразы «Страна производства» — затем точку и краткое описание из поля description.
   Строка 3: визуальный разделитель — линия из подчёркиваний, например _____________________________ (не менее 20 символов). Не пиши слово «разделитель».

4) Текущие собранные параметры: CURRENT_PARAMS_PLACEHOLDER. Всего параметров: PARAMS_COUNT_PLACEHOLDER. Нужно минимум 3 для точного подбора.
   Если параметров меньше 3 — в КОНЦЕ своего сообщения обязательно задай один-два коротких уточняющих вопроса (марка, модель, тип кузова, год, коробка, топливо и т.п.), чтобы собрать недостающие. Не предлагай конкретные модели — только вопросы.

Порядок ответа: короткое приветствие/одобрение → выбранные автомобили (только с соответствием ≥60%) в указанном формате → если параметров < 3, блок с уточняющими вопросами.

Строго запрещено: придумывать автомобили; писать «Страна производства»; писать слово «разделитель» вместо линии подчёркиваний; пересказывать историю диалога или выводить префиксы вроде «Пользователь:», «Ассистент:». Просто дай финальный ответ пользователю без явно оформленного протокола диалога. Ответ начинай с заглавной буквы."""

PROMPT_GENERATE_RESPONSE_CLARIFY = """Ты — консультант по подбору автомобилей. Общайся на русском, вежливо.

Сейчас для поиска в базе не хватает параметров: нужно минимум 3 из перечня (марка, модель, тип кузова, год, модификация, коробка, топливо, объём двигателя, мощность). Уже собрано: CURRENT_PARAMS_PLACEHOLDER

Строго: задай пользователю ровно один короткий уточняющий вопрос (про один из недостающих параметров). Не предлагай и не называй конкретные автомобили — только вопрос. Ответ начинай с заглавной буквы."""

PROMPT_CLASSIFY_CAR_CONTEXT = """Ты — классификатор намерений пользователя. По последнему сообщению и контексту диалога определи: связано ли сообщение с автомобилями или с подбором/поиском автомобиля?

Считай «про автомобиль», если пользователь: упоминает марку, модель, тип кузова, год, топливо, коробку, ищет машину, хочет подобрать авто, спрашивает про характеристики авто, сравнивает машины и т.п.
Считай «не про автомобиль», если: приветствие, общие вопросы не про авто, оффтоп (погода, еда и т.д.), пустое или неясное сообщение без намёка на авто.

Ответь строго одним словом: ДА или НЕТ. Никаких пояснений."""

PROMPT_SMALL_TALK_NO_CAR = """Ты — вежливый консультант по подбору автомобилей. Сообщение пользователя не связано с поиском автомобиля (приветствие, общий разговор или неясный запрос).

Твоя задача: вежливо пообщаться, поблагодарить за обращение и мягко направить разговор к подбору авто. Задай один-два коротких уточняющих вопроса о том, какой автомобиль интересует пользователь (например: марка, тип кузова, для чего нужна машина, бюджет). Не предлагай конкретные модели — только пригласи к диалогу о подборе. Не пересказывай переписку и не используй форматы «Пользователь:», «Ассистент:» — просто дай ответ. Отвечай кратко и по-русски. Ответ начинай с заглавной буквы."""

PROMPT_NO_CARS_ASK_ANOTHER = """Ты — консультант по подбору автомобилей. Общайся на русском, вежливо.

По запросу пользователя в нашем сервисе не нашлось подходящего автомобиля. Нужно вежливо сказать об этом и предложить подобрать другой, не менее крутой вариант.

Обязательно: начни с фразы в духе «К сожалению, в нашем сервисе нет такого автомобиля. Давайте подберём другой, не менее крутой.» Затем задай ровно один уточняющий вопрос (марка, модель, тип кузова, год, модификация, коробка, топливо, объём или мощность), чтобы продолжить подбор. Не пересказывай предыдущие сообщения и не используй префиксы «Пользователь:», «Ассистент:» — сразу формулируй ответ пользователю. Ответ начинай с заглавной буквы."""


# Таймаут одного запроса к LLM (секунды). Два вызова подряд — до 2 * LLM_REQUEST_TIMEOUT.
LLM_REQUEST_TIMEOUT = 90.0


# Ниже ранее была логика для работы через другой LLM‑провайдер (OpenAI‑совместимый клиент).
# Сейчас она полностью отключена и используется только GenAPI.


def _extract_text_from_genapi_response(data: Dict[str, Any]) -> str:
    """
    Извлекает текст ответа из структуры GenAPI.
    Поддерживаются: OpenAI-подобный (choices[].message.content/reasoning_content),
    обёртка в output/result и вложенные структуры.
    """
    # Логируем ключи ответа (без тела), чтобы при проблемах понять формат
    logger.debug("GenAPI response keys: %s", list(data.keys()))

    def text_from_choices(choices: list) -> str:
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0] or {}
        message = first.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        # DeepSeek Reasoner и др. могут отдавать основной ответ в reasoning_content
        reasoning = message.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()
        return ""

    # Прямой формат: choices[0].message.content / reasoning_content
    choices = data.get("choices")
    text = text_from_choices(choices)
    if text:
        return text

    # GenAPI может оборачивать ответ в output или result
    for key in ("output", "result", "data"):
        block = data.get(key)
        if isinstance(block, dict):
            text = text_from_choices(block.get("choices"))
            if text:
                return text
            text = block.get("text") or block.get("output_text") or block.get("content")
            if isinstance(text, str) and text.strip():
                return text.strip()
        elif isinstance(block, str) and block.strip():
            return block.strip()

    # Плоский текст в корне
    text = data.get("text") or data.get("output_text") or data.get("response") or data.get("content")
    if isinstance(text, str) and text.strip():
        return text.strip()

    # Если ничего не нашли — логируем структуру ответа (видны в docker logs)
    logger.info(
        "GenAPI: не удалось извлечь текст. Ключи: %s, output/result (первые 300 символов): %s",
        list(data.keys()),
        (str(data.get("output") or data.get("result")) or "")[:300],
    )
    return ""


def _call_genapi(messages: List[Dict[str, str]]) -> str:
    """
    Вызов DeepSeek Reasoner через GenAPI.

    Требуется настроить:
    - settings.genapi_api_key
    - settings.genapi_generate_url (полный URL из документации GenAPI)
    - settings.genapi_model_id (по умолчанию deepseek-reasoner)
    """
    headers = {
        "Authorization": f"Bearer {settings.genapi_api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": settings.genapi_model_id,
        "messages": messages,
    }
    # Режим "Сразу ответ" (если модель/endpoint поддерживают is_sync)
    if settings.genapi_sync_mode:
        payload["is_sync"] = True

    with httpx.Client(timeout=LLM_REQUEST_TIMEOUT) as client:
        resp = client.post(settings.genapi_generate_url, headers=headers, json=payload)
    resp.raise_for_status()

    try:
        data = resp.json()
    except json.JSONDecodeError:
        logger.error("GenAPI вернул не‑JSON ответ")
        return ""

    text = _extract_text_from_genapi_response(data)
    return text


def _llm_chat(messages: List[Dict[str, str]], max_tokens: int | None = None) -> str:
    """
    Унифицированный вызов LLM: при наличии Yandex (YANDEX_FOLDER_ID + YANDEX_API_KEY)
    используется YandexGPT; иначе GigaChat.
    max_tokens: лимит токенов ответа (только для Yandex; меньше = быстрее для коротких задач).
    Если выбранный провайдер не настроен или запрос падает — возвращаем пустую строку.
    """
    if not messages:
        return ""

    # Yandex LLM (те же учётные данные, что и для эмбеддингов)
    if settings.yandex_folder_id and settings.yandex_api_key:
        try:
            max_tok = max_tokens if max_tokens is not None else 2000
            text = yandex_llm_service.completion(messages, max_tokens=max_tok)
            if text:
                return text
        except Exception as e:  # noqa: BLE001
            logger.exception("Yandex LLM failed, fallback to GigaChat: %s", e)
        # При пустом ответе или ошибке — fallback на GigaChat, если настроен

    if not settings.gigachat_credentials:
        logger.error("LLM не настроен: задайте Yandex (yandex_folder_id, yandex_api_key) "
                     "или GigaChat (gigachat_credentials)")
        return ""

    giga_messages: list[Messages] = []
    for m in messages:
        role = m.get("role", "user")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            msg_role = MessagesRole.SYSTEM
        elif role == "assistant":
            msg_role = MessagesRole.ASSISTANT
        else:
            msg_role = MessagesRole.USER
        giga_messages.append(Messages(role=msg_role, content=content))

    if not giga_messages:
        return ""

    try:
        client = GigaChat(
            credentials=settings.gigachat_credentials,
            verify_ssl_certs=getattr(settings, "gigachat_verify_ssl_certs", True),
        )
        chat = Chat(messages=giga_messages)
        with client:
            response = client.chat(chat)
    except Exception as e:  # noqa: BLE001
        logger.exception("GigaChat call failed: %s", e)
        return ""

    if not getattr(response, "choices", None):
        return ""
    message = response.choices[0].message
    content = getattr(message, "content", "") or ""
    return content.strip()


def classify_message_about_car(messages: list[dict[str, str]]) -> bool:
    """
    Определяет по последнему сообщению и контексту, связано ли сообщение с автомобилями/подбором авто.
    Возвращает True, если в контексте есть что-то про автомобиль; иначе False (small talk / уточняющие вопросы).
    """
    if not messages:
        return False
    system_content = _with_style_instructions(PROMPT_CLASSIFY_CAR_CONTEXT)
    api_messages = [{"role": "system", "content": system_content}]
    # Передаём последние 3–5 сообщений для контекста
    for m in messages[-6:]:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if role in ("user", "assistant") and content.strip():
            api_messages.append({"role": role, "content": content})
    try:
        raw = _llm_chat(api_messages)
    except Exception as e:  # noqa: BLE001
        logger.exception("classify_message_about_car failed: %s", e)
        # При ошибке считаем, что про авто (чтобы не блокировать поиск)
        return True
    if not raw:
        return True
    answer = raw.strip().upper()
    return "ДА" in answer or "YES" in answer


def generate_response_small_talk(messages: list[dict[str, str]]) -> str:
    """
    Ответ, когда сообщение не про автомобиль: вежливо пообщаться и задать уточняющие вопросы про авто.
    Векторный поиск не выполняется.
    """
    # Если пользователь явно спрашивает, как зовут ассистента — отвечаем детерминированно,
    # не полагаясь на LLM, чтобы не появлялись шаблоны вроде «[Ваше имя]».
    last_user = ""
    for m in reversed(messages or []):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip().lower()
            break
    if last_user and (
        "как тебя зовут" in last_user
        or "как вас зовут" in last_user
        or "тебя зовут" in last_user
        or "вас зовут" in last_user
    ):
        return (
            "Здравствуйте! Меня зовут Моторчик Тёма, я консультант по подбору автомобилей. "
            "Расскажите, какой автомобиль вы ищете — марку, тип кузова или для каких задач нужна машина?"
        )

    system_content = _with_style_instructions(PROMPT_SMALL_TALK_NO_CAR)
    api_messages = [{"role": "system", "content": system_content}]
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if role in ("user", "assistant"):
            api_messages.append({"role": role, "content": content})
    try:
        text = _llm_chat(api_messages)
    except Exception as e:  # noqa: BLE001
        logger.exception("generate_response_small_talk failed: %s", e)
        return "Спасибо за обращение! Подскажите, какой автомобиль вы ищете — марку, тип кузова или цель использования?"
    if not text:
        return "Спасибо за обращение! Подскажите, какой автомобиль вы ищете — марку, тип кузова или цель использования?"
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def chat_complete(messages: list[dict[str, str]]) -> str:
    """Свободный чат: отправляет историю в DeepSeek и возвращает ответ ассистента."""
    if not messages:
        return "Отправьте сообщение, чтобы начать диалог."
    api_messages: list[dict[str, str]] = [
        {"role": "system", "content": ASSISTANT_STYLE_INSTRUCTIONS}
    ]
    api_messages.extend(
        {"role": m.get("role", "user"), "content": (m.get("content") or "")}
        for m in messages
    )
    try:
        text = _llm_chat(api_messages)
    except Exception as e:  # noqa: BLE001
        logger.exception("DeepSeek chat_complete failed: %s", e)
        return (
            "Не удалось получить ответ от модели. "
            "Попробуйте ещё раз чуть позже или переформулировать запрос."
        )
    if not text:
        return "Пустой ответ от модели. Попробуйте задать вопрос иначе."
    return text


def _extract_json_block(text: str) -> str | None:
    """Находит блок ```json ... ``` или первый объект {"extracted_params": ...} и возвращает его."""
    # 1) Блок в markdown
    match = re.search(r"```(?:json)?\s*\{", text, re.DOTALL | re.IGNORECASE)
    if match:
        start = match.end() - 1
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    # 2) Голый JSON в тексте (модель могла не обернуть в ```)
    match = re.search(r'\{\s*"extracted_params"\s*:', text)
    if match:
        start = match.start()
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


# Ключевые слова типа кузова для fallback, когда справочник из БД пустой (напр. на Render нет cars)
# Регулярка -> каноническое значение для search_cars (car_reference_service._body_type_filter_condition)
FALLBACK_BODY_TYPE_KEYWORDS = [
    (r"\b(хэтчбек|хетчбек|hatchback)\b", "хэтчбек"),
    (r"\b(седан|sedan)\b", "седан"),
    (r"\b(универсал|wagon)\b", "универсал"),
    (r"\b(внедорожник|suv)\b", "внедорожник"),
    (r"\b(кроссовер|crossover)\b", "кроссовер"),
    (r"\b(купе|coupe)\b", "купе"),
    (r"\b(минивэн|минивен|minivan)\b", "минивэн"),
    (r"\b(лифтбек|liftback)\b", "лифтбек"),
    (r"\b(кабриолет|cabriolet)\b", "кабриолет"),
    (r"\b(пикап|pickup)\b", "пикап"),
]

# Ключевые слова для извлечения марки в fallback (как пользователь мог написать -> имя в БД)
FALLBACK_BRAND_KEYWORDS = [
    (r"\b(renault|рено)\b", "Renault"),
    (r"\b(toyota|тойота)\b", "Toyota"),
    (r"\b(bmw|бмв)\b", "BMW"),
    (r"\b(mercedes|мерседес|мерс)\b", "Mercedes-Benz"),
    (r"\b(lada|лада)\b", "Lada"),
    (r"\b(volkswagen|вольксваген|фольксваген|ву)\b", "Volkswagen"),
    (r"\b(hyundai|хёндай|хендай)\b", "Hyundai"),
    (r"\b(kia|киа)\b", "Kia"),
    (r"\b(nissan|ниссан)\b", "Nissan"),
    (r"\b(skoda|шкода)\b", "Škoda"),
]


def extract_params_fallback(user_texts: list[str], body_type_reference: list[str]) -> dict[str, str]:
    """
    Резервное извлечение параметров по ключевым словам из текста сообщений пользователя.
    Используется, когда LLM вернул неполный список. Возвращает dict param_type -> value.
    """
    if not user_texts:
        return {}
    text = " ".join(t for t in user_texts if t).lower()
    if not text.strip():
        return {}
    result = {}
    # Марка — по ключевым словам
    for pattern, canonical in FALLBACK_BRAND_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            result["brand"] = canonical
            break
    # Топливо
    if re.search(r"\b(бензин|на бензине|бензиновый)\b", text):
        result["fuel_type"] = "бензин"
    elif re.search(r"\b(дизель|на дизеле|дизельный)\b", text):
        result["fuel_type"] = "дизель"
    elif re.search(r"\b(гибрид|гибридный)\b", text):
        result["fuel_type"] = "гибрид"
    elif re.search(r"\b(электро|электрический|электромобиль)\b", text):
        result["fuel_type"] = "электро"
    # Коробка
    if re.search(r"\b(автомат|автоматическая|акпп)\b", text):
        result["transmission"] = "автомат"
    elif re.search(r"\b(механика|механическая|мкпп|ручная)\b", text):
        result["transmission"] = "механика"
    elif re.search(r"\b(вариатор|cvt)\b", text):
        result["transmission"] = "вариатор"
    elif re.search(r"\b(робот|роботизированная)\b", text):
        result["transmission"] = "робот"
    # Год (конкретное значение, если явно указали)
    year_match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", text)
    if year_match:
        result["year"] = year_match.group(1)
    # Относительные ограничения по возрасту: «не старше 15 лет», «старше 10 лет» и т.п.
    current_year = datetime.utcnow().year
    # «не старше 15 лет» → машина не старше N лет → год не меньше (current_year - N).
    # Если пользователь менял мнение несколько раз, берём ПОСЛЕДНЕЕ упоминание.
    not_older_matches = list(re.finditer(r"не\s+старше\s+(\d{1,2})\s+лет", text))
    if not_older_matches:
        try:
            years = int(not_older_matches[-1].group(1))
            min_year = current_year - years
            result["year_min"] = str(min_year)
        except ValueError:
            pass
    # «старше 15 лет» → машина старше N лет → год не больше (current_year - N)
    older_matches = list(re.finditer(r"старше\s+(\d{1,2})\s+лет", text))
    if older_matches:
        try:
            years = int(older_matches[-1].group(1))
            max_year = current_year - years
            result["year_max"] = str(max_year)
        except ValueError:
            pass
    # «не новее 2015 года» → год выпуска не новее → year_max = 2015
    not_newer_year_matches = list(re.finditer(r"не\s+новее\s+(19\d{2}|20[0-2]\d)", text))
    if not_newer_year_matches:
        result["year_max"] = not_newer_year_matches[-1].group(1)
    # «не старше 2015 года» → год не старше → year_min = 2015
    not_older_year_matches = list(re.finditer(r"не\s+старше\s+(19\d{2}|20[0-2]\d)", text))
    if not_older_year_matches:
        result["year_min"] = not_older_year_matches[-1].group(1)
    # Объём двигателя (1.6, 2.0)
    vol_match = re.search(r"\b(\d{1}\.\d{1,2})\s*(?:л|литр|литра)?", text)
    if vol_match:
        result["engine_volume"] = vol_match.group(1)
    # Мощность (90 л.с., 150 л.с.)
    hp_match = re.search(r"(\d{2,3})\s*л\.?\s*с", text, re.IGNORECASE)
    if hp_match:
        result["horsepower"] = hp_match.group(1)
    # Тип кузова: сначала по справочнику из БД (если есть записи cars с body_type)
    for bt in body_type_reference or []:
        if not bt or not bt.strip():
            continue
        bt_lower = bt.strip().lower()
        if bt_lower in text:
            result["body_type"] = bt.strip()
            break
        # Совпадение по первому слову (хэтчбек, седан, универсал и т.д.)
        first_word = bt_lower.split()[0] if bt_lower.split() else bt_lower
        if len(first_word) >= 3 and first_word in text:
            result["body_type"] = bt.strip()
            break
    # Если справочник пустой (напр. на Render нет данных в cars) — распознаём по ключевым словам.
    # search_cars принимает «хэтчбек»/«седан» и т.д. и сам сопоставляет с БД.
    if "body_type" not in result:
        for keyword, canonical in FALLBACK_BODY_TYPE_KEYWORDS:
            if re.search(keyword, text):
                result["body_type"] = canonical
                break
    return result


def _parse_extract_params_response(raw: str) -> list[dict]:
    """Парсит JSON-блок из ответа extract_params. Возвращает список extracted_params или []."""
    text = (raw or "").strip()
    json_str = _extract_json_block(text)
    if not json_str:
        return []
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return []
    params_raw = data.get("extracted_params")
    if not isinstance(params_raw, list):
        return []
    extracted = []
    for p in params_raw:
        if not isinstance(p, dict):
            continue
        t = p.get("type")
        if t == "mark":
            t = "brand"
        if t not in EXTRACTED_PARAM_TYPES:
            continue
        val = p.get("value")
        if val is None:
            val = ""
        extracted.append({
            "type": t,
            "value": str(val).strip(),
            "confidence": float(p.get("confidence", 0.9)),
        })
    return extracted


def extract_params(
    messages: list[dict[str, str]],
    current_params: dict | None,
    body_type_reference: list[str],
) -> list[dict]:
    """
    Извлечение параметров подбора из истории диалога. Возвращает список
    [{"type": ..., "value": str, "confidence": float}, ...] — все найденные параметры.
    """
    if not body_type_reference:
        body_list = "седан, внедорожник 5 дв., хэтчбек (если справочник пуст — используй эти примеры)"
    else:
        body_list = ", ".join(repr(b) for b in body_type_reference)
    current_str = ", ".join(f"{k}={v}" for k, v in (current_params or {}).items()) or "пока нет"
    system_content = _with_style_instructions(
        PROMPT_EXTRACT_PARAMS.replace("BODY_TYPE_REFERENCE_PLACEHOLDER", body_list).replace(
            "CURRENT_PARAMS_PLACEHOLDER", current_str
        )
    )
    # Явно напомнить про последнее сообщение пользователя — в нём часто ответ на уточняющий вопрос
    last_user_content = ""
    for m in reversed(messages or []):
        if m.get("role") == "user":
            last_user_content = (m.get("content") or "").strip()
            break
    if last_user_content:
        system_content += (
            "\n\n--- Напоминание: обрабатывай КАЖДОЕ сообщение пользователя в диалоге (включая последнее). "
            "Последнее сообщение пользователя: «"
            + last_user_content[:500]
            + ("»" if len(last_user_content) <= 500 else "» (обрезано). ")
            + " Извлеки из него все параметры (марка, модель, кузов, год, топливо → fuel_type, коробка → transmission, объём, мощность) и включи в extracted_params вместе с параметрами из предыдущих сообщений."
        )
    api_messages = [{"role": "system", "content": system_content}]
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if role in ("user", "assistant"):
            api_messages.append({"role": role, "content": content})
    try:
        raw = _llm_chat(api_messages, max_tokens=800)
    except Exception as e:  # noqa: BLE001
        logger.exception("DeepSeek extract_params failed: %s", e)
        return []
    if not raw:
        return []
    parsed = _parse_extract_params_response(raw)
    logger.info(
        "extract_params: raw_len=%s, parsed_count=%s, types=%s",
        len(raw or ""),
        len(parsed),
        [p.get("type") for p in parsed],
    )
    return parsed


def _format_car_for_prompt(car) -> str:
    """Форматирует одну машину для ответа: все поля из БД, только реальные данные."""
    lines: list[str] = []
    if getattr(car, "id", None) is not None:
        lines.append(f"  id: {car.id}")
    if getattr(car, "mark_name", None):
        lines.append(f"  марка: {car.mark_name}")
    if getattr(car, "model_name", None):
        lines.append(f"  модель: {car.model_name}")
    if getattr(car, "year", None) is not None:
        lines.append(f"  год: {car.year}")
    if getattr(car, "body_type", None):
        lines.append(f"  тип кузова: {car.body_type}")
    if getattr(car, "price_rub", None) is not None:
        try:
            price_val = int(float(car.price_rub))
            lines.append(f"  цена: {price_val} ₽")
        except (TypeError, ValueError):
            lines.append(f"  цена: {car.price_rub}")
    if getattr(car, "fuel_type", None):
        lines.append(f"  топливо: {car.fuel_type}")
    if getattr(car, "modification", None):
        lines.append(f"  модификация: {car.modification}")
    if getattr(car, "transmission", None):
        lines.append(f"  коробка: {car.transmission}")
    if getattr(car, "engine_volume", None) is not None:
        lines.append(f"  объём двигателя: {car.engine_volume} л")
    if getattr(car, "horsepower", None) is not None:
        lines.append(f"  мощность: {car.horsepower} л.с.")
    if getattr(car, "description", None) and str(car.description).strip():
        desc = str(car.description).strip()
        if len(desc) > 400:
            desc = desc[:397] + "..."
        lines.append(f"  описание: {desc}")
    specs = getattr(car, "specs", None)
    if specs and isinstance(specs, dict) and specs:
        parts_spec = [f"{k}: {v}" for k, v in list(specs.items())[:10] if v]
        if parts_spec:
            lines.append("  доп. характеристики: " + "; ".join(parts_spec))
    images = getattr(car, "images", None)
    if images and isinstance(images, (list, tuple)) and len(images) > 0:
        lines.append(f"  фото: {len(images)} шт.")
    return "\n".join(lines) if lines else str(car)


def _format_car_descriptions_for_llm(search_results: list) -> str:
    """
    Формирует для LLM список полей description найденных автомобилей (из БД).
    (legacy — используется для старого промпта без RAG)
    """
    parts: list[str] = []
    for idx, car in enumerate(search_results[:10], start=1):
        desc = getattr(car, "description", None)
        desc_str = (desc and str(desc).strip()) or "—"
        parts.append(f"Автомобиль {idx}: {desc_str}")
    return "\n\n".join(parts) if parts else "Нет данных."


def _format_cars_full_for_llm(search_results: list) -> str:
    """
    Формирует для LLM полные данные о каждом автомобиле (RAG-промпт).
    Использует _format_car_for_prompt() для каждого авто.
    """
    parts: list[str] = []
    for idx, car in enumerate(search_results[:10], start=1):
        car_block = _format_car_for_prompt(car)
        parts.append(f"Автомобиль {idx}:\n{car_block}")
    return "\n\n".join(parts) if parts else "Нет данных."


def _format_cars_for_user_answer(search_results: list) -> str:
    """
    Формирует финальный текстовый ответ для пользователя:
    - короткое приветствие/одобрение;
    - затем по каждой машине три строки в заданном формате.
    """
    if not search_results:
        return "Пока не удалось найти подходящие автомобили."

    # Ограничим количество машин, чтобы не перегружать ответ
    cars_to_show = list(search_results[:6])

    lines: list[str] = []
    # Приветствие / общие слова одобрения и уточнения
    lines.append(
        "Здравствуйте! Рад вас видеть у нас. Давайте подберём что-то классное из списка."
    )
    lines.append(
        "Вот что я вижу подходящим под ваш запрос:"
    )
    lines.append("")  # пустая строка перед списком машин

    for car in cars_to_show:
        mark = getattr(car, "mark_name", "") or ""
        model = getattr(car, "model_name", "") or ""
        body_type = getattr(car, "body_type", "") or ""
        year = getattr(car, "year", None)
        modification = getattr(car, "modification", "") or ""
        engine_volume = getattr(car, "engine_volume", None)
        transmission = getattr(car, "transmission", "") or ""
        horsepower = getattr(car, "horsepower", None)
        country = getattr(car, "country", "") or ""
        description = getattr(car, "description", None)

        # Строка 1: (иконка машинки) Марка, Модель, [Тип кузова] ([модификация/двигатель/коробка/л.с.]), Год.
        details_parts: list[str] = []
        if modification:
            details_parts.append(modification)
        else:
            engine_part = ""
            if engine_volume is not None:
                try:
                    engine_part = f"{float(engine_volume):.1f} л"
                except (TypeError, ValueError):
                    engine_part = str(engine_volume)
            tr_part = transmission
            hp_part = ""
            if horsepower is not None:
                hp_part = f"{horsepower} л.с."
            combined_inner = ", ".join(
                [p for p in [engine_part, tr_part, hp_part] if p]
            )
            if combined_inner:
                details_parts.append(combined_inner)
        details_str = ", ".join(details_parts) if details_parts else ""

        body_part = body_type if body_type else ""
        if body_part and details_str:
            body_and_mod = f"{body_part} ({details_str})"
        elif body_part:
            body_and_mod = body_part
        elif details_str:
            body_and_mod = details_str
        else:
            body_and_mod = ""

        year_part = f"{year}." if year is not None else ""

        line1_parts: list[str] = [mark, model]
        if body_and_mod:
            line1_parts.append(body_and_mod)
        if year_part:
            line1_parts.append(year_part)
        line1 = ", ".join(p for p in line1_parts if p)
        lines.append(f"🚗 {line1}")
        lines.append("")  # пустая строка между основной и инфо-строкой

        # Строка 2: ℹ️ Выпускается в <country>. <description> (без «Страна производства»)
        desc_text = (description and str(description).strip()) or ""
        if len(desc_text) > 400:
            desc_text = desc_text[:397] + "..."
        if country:
            info_line = f"ℹ️ Выпускается в {country}. {desc_text}".strip()
        else:
            info_line = f"ℹ️ {desc_text}".strip()
        lines.append(info_line)
        # Строка 3: визуальный разделитель
        lines.append("_____________________________")
        lines.append("")

    return "\n".join(lines)


def _normalize_car_response_icons(text: str) -> str:
    """
    Заменяет в ответе LLM текстовые плейсхолдеры на реальные иконки и разделитель,
    убирает лишнее «Страна производства».
    """
    if not text or not text.strip():
        return text
    t = text
    # Иконки
    t = t.replace("(иконка автомобиля цветная)", "🚗")
    t = t.replace("(иконка цветная инфо)", "ℹ️")
    t = t.replace("(иконка машинки)", "🚗")
    t = t.replace("(иконка инфо)", "ℹ️")
    # Слово «разделитель» на отдельной строке — линия подчёркиваний
    t = re.sub(r"^\s*разделитель\s*$", "_____________________________", t, flags=re.MULTILINE)
    # «Страна производства: X» → «Выпускается в X»
    t = re.sub(
        r"Страна производства\s*:\s*([^.]+?)(?=\.|$)",
        r"Выпускается в \1",
        t,
        flags=re.IGNORECASE,
    )
    return t


def generate_response(
    messages: list[dict[str, str]],
    params: dict,
    search_results: list,
    criteria_fulfilled: bool = False,
    parameters_count: int = 0,
) -> str:
    """
    Генерация ответа пользователю.
    - Если есть search_results: LLM выбирает из топ-10 только кандидатов с соответствием >= 60%,
      выводит их в заданном формате и в конце задаёт уточняющие вопросы, если параметров < 3.
    - Если критериев было достаточно, но поиск вернул 0 — сообщение «в базе не найдено» + вопрос.
    - Если параметров мало и поиска не было — один уточняющий вопрос.
    """
    if search_results:
        # Есть топ-10 кандидатов: LLM отбирает >= 60%, выводит их и при необходимости задаёт вопросы
        candidates_text = _format_cars_full_for_llm(search_results)
        current_params_str = ", ".join(f"{k}={v}" for k, v in params.items() if v) or "пока нет"
        system_content = _with_style_instructions(
            PROMPT_CARS_SELECT_60_AND_ASK.replace("CANDIDATES_PLACEHOLDER", candidates_text)
            .replace("CURRENT_PARAMS_PLACEHOLDER", current_params_str)
            .replace("PARAMS_COUNT_PLACEHOLDER", str(parameters_count))
        )
        api_messages = [{"role": "system", "content": system_content}]
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content") or ""
            if role in ("user", "assistant"):
                api_messages.append({"role": role, "content": content})
        try:
            text = _llm_chat(api_messages)
        except Exception as e:  # noqa: BLE001
            logger.exception("DeepSeek generate_response (select 60%% + ask) failed: %s", e)
            return _format_cars_for_user_answer(search_results[:6])
        if not text or not text.strip():
            return _format_cars_for_user_answer(search_results[:6])
        text = _normalize_car_response_icons(text)
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        # Жёсткая страховка: если параметров всё ещё меньше MIN_PARAMS_FOR_SEARCH,
        # а LLM почему-то не задал уточняющий вопрос, добавляем короткий вопрос сами.
        if parameters_count < MIN_PARAMS_FOR_SEARCH:
            last_chunk = (text or "")[-300:].lower()
            has_question = "?" in last_chunk or any(
                kw in last_chunk
                for kw in (
                    "какой ", "какая ", "какие ", "уточните", "расскажите", "подскажите",
                    "интересует", "что именно",
                )
            )
            if not has_question:
                extra_q = (
                    "\n\nЧтобы подобрать точнее, подскажите, пожалуйста, "
                    "какой тип кузова, год выпуска или бюджет вы примерно рассматриваете?"
                )
                text = (text or "").rstrip() + extra_q
        return text

    if criteria_fulfilled:
        # В базе нет подходящих — предлагаем подобрать другой и задаём уточняющий вопрос через LLM
        current_str = ", ".join(f"{k}={v}" for k, v in params.items() if v) or ""
        system_content = _with_style_instructions(
            PROMPT_NO_CARS_ASK_ANOTHER + "\n\nТекущие собранные параметры: " + current_str
        )
        api_messages = [{"role": "system", "content": system_content}]
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content") or ""
            if role in ("user", "assistant"):
                api_messages.append({"role": role, "content": content})
        try:
            text = _llm_chat(api_messages)
        except Exception as e:  # noqa: BLE001
            logger.exception("DeepSeek generate_response (no cars) failed: %s", e)
            return (
                "К сожалению, в нашем сервисе нет такого автомобиля. "
                "Давайте подберём другой, не менее крутой. Уточните, пожалуйста, марку, модель или тип кузова."
            )
        if not text:
            return (
                "К сожалению, в нашем сервисе нет такого автомобиля. "
                "Давайте подберём другой, не менее крутой. Уточните, пожалуйста, марку, модель или тип кузова."
            )
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        return text

    # Мало параметров — просим LLM задать один уточняющий вопрос
    current_str = ", ".join(f"{k}={v}" for k, v in params.items()) or "пока нет"
    system_content = _with_style_instructions(
        PROMPT_GENERATE_RESPONSE_CLARIFY.replace("CURRENT_PARAMS_PLACEHOLDER", current_str)
    )
    api_messages = [{"role": "system", "content": system_content}]
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if role in ("user", "assistant"):
            api_messages.append({"role": role, "content": content})
    try:
        text = _llm_chat(api_messages)
    except Exception as e:  # noqa: BLE001
        logger.exception("DeepSeek generate_response (clarify) failed: %s", e)
        return "Не удалось обработать запрос. Попробуйте ещё раз."
    if not text:
        return "Не удалось получить ответ. Попробуйте ещё раз."
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    # Страховка: если параметров всё ещё меньше MIN_PARAMS_FOR_SEARCH,
    # гарантируем наличие хотя бы одного уточняющего вопроса в ответе.
    if parameters_count < MIN_PARAMS_FOR_SEARCH:
        last_chunk = (text or "")[-300:].lower()
        has_question = "?" in last_chunk or any(
            kw in last_chunk
            for kw in (
                "какой ", "какая ", "какие ", "уточните", "расскажите", "подскажите",
                "интересует", "что именно",
            )
        )
        if not has_question:
            extra_q = (
                "\n\nЧтобы подобрать точнее, подскажите, пожалуйста, "
                "какую марку, модель, тип кузова или год выпуска вы примерно рассматриваете?"
            )
            text = (text or "").rstrip() + extra_q
    return text
