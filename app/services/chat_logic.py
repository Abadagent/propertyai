from app.models.conversation import Conversation
from app.models.lead import Lead
from app.models.account import Account

from app.services.faq import try_answer_faq
from app.services.bot_access import can_bot_reply, get_bot_block_reason
from app.services.lead_notifier import send_lead_to_telegram


# =====================
# ТЕКСТЫ БОТА
# =====================

def first_question():
    return (
        "Здравствуйте 🙂\n"
        "Помогу быстро сориентироваться по недвижимости.\n"
        "Подскажите, вас интересует покупка, аренда или продажа?"
    )


def ask_property_type():
    return "Какой тип недвижимости рассматриваете: квартира, дом, участок или коммерция?"


def ask_district():
    return "В каком районе, городе или локации смотрите объект?"


def ask_rooms():
    return "Сколько комнат нужно? Если не принципиально — можно так и написать."


def ask_budget():
    return "На какой бюджет ориентируетесь? Можно написать примерно, например: до 30 млн."


def ask_purpose():
    return "Для каких целей рассматриваете объект: для себя, под аренду, инвестицию или перепродажу?"


def ask_name():
    return "И последний момент: как я могу к вам обращаться?"


def final_reply():
    return "Спасибо 🙂 Я передал вашу заявку специалисту. Он свяжется с вами в ближайшее время."


def fallback_request_type():
    return "Подскажите, пожалуйста: вас интересует покупка, аренда или продажа недвижимости?"


def fallback_property_type():
    return "Уточните, пожалуйста: вас интересует квартира, дом, участок или коммерческая недвижимость?"


def fallback_district():
    return "Подскажите, пожалуйста, район, город или удобную вам локацию."


def fallback_rooms():
    return "Напишите, сколько комнат рассматриваете. Например: 1-комнатную, 2 комнаты или не принципиально."


def fallback_budget():
    return "Подскажите примерный бюджет. Например: до 25 млн, 300 тысяч в месяц или без строгого лимита."


def fallback_purpose():
    return "Для чего нужен объект: для себя, для аренды, для инвестиций или для перепродажи?"


def fallback_name():
    return "Как я могу к вам обращаться?"


def off_topic_reply(current_question: str):
    return (
        "К сожалению, мы занимаемся только недвижимостью 🙂\n"
        "Что вас интересует именно в сфере недвижимости?\n\n"
        f"{current_question}"
    )


def payment_reply():
    return (
        "💳 Подключение доступа:\n\n"
        "Тариф: 10 000 тг / 30 дней\n"
        "После оплаты подписка активируется, и бот продолжит работу.\n\n"
        "Если оплатили — напишите: оплатил"
    )


def pricing_reply():
    return (
        "💼 Тарифы:\n\n"
        "Базовый — 10 000 тг / 30 дней\n"
        "Подходит для запуска и теста бота.\n\n"
        "Если хотите подключить — напишите: оплата"
    )


def paid_confirmation_reply():
    return "Спасибо! Проверяем оплату. Обычно это занимает до 5 минут 🙂"


def whatsapp_not_connected_reply():
    return (
        "📱 WhatsApp пока не подключён.\n"
        "Подключите Green API / WhatsApp, и бот сразу продолжит работу."
    )


def subscription_inactive_reply():
    return (
        "❌ Подписка не активна или истекла.\n\n"
        "Чтобы продолжить работу, напишите: оплата\n"
        "Если хотите сначала посмотреть цену — напишите: тариф"
    )


def bot_paused_reply():
    return "⏸ Бот сейчас на паузе. Снимите паузу в кабинете, чтобы продолжить работу."


def manager_connected_reply():
    return "👤 Диалог уже передан менеджеру. Бот больше не отвечает в этой переписке."


def account_not_found_reply():
    return "Аккаунт не найден. Проверьте авторизацию и попробуйте снова."


def unknown_block_reply():
    return "Бот временно недоступен. Проверьте настройки подключения и статус доступа."


# =====================
# УТИЛИТЫ
# =====================

def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def has_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def is_question(text: str):
    text = normalize_text(text)
    return "?" in text or text.startswith(
        ("что", "как", "где", "сколько", "есть ли", "можно ли", "какой", "какая", "когда")
    )


def try_faq(text):
    answer = try_answer_faq(text)
    if not answer:
        return None
    return {"reply": answer}


def is_payment_request(text: str) -> bool:
    text = normalize_text(text)
    payment_words = [
        "оплата",
        "оплатить",
        "купить доступ",
        "подключить",
        "подключение",
        "активировать",
        "доступ",
    ]
    return has_any(text, payment_words)


def is_pricing_request(text: str) -> bool:
    text = normalize_text(text)
    pricing_words = [
        "тариф",
        "тарифы",
        "цена",
        "стоимость",
        "сколько стоит",
        "прайс",
    ]
    return has_any(text, pricing_words)


def is_paid_confirmation(text: str) -> bool:
    text = normalize_text(text)
    return "оплатил" in text or "оплатила" in text or "оплатили" in text


def block_reason_reply(reason: str) -> str:
    if reason == "account_not_found":
        return account_not_found_reply()

    if reason == "whatsapp_not_connected":
        return whatsapp_not_connected_reply()

    if reason == "subscription_inactive":
        return subscription_inactive_reply()

    if reason == "bot_paused":
        return bot_paused_reply()

    if reason == "manager_connected":
        return manager_connected_reply()

    return unknown_block_reply()


def is_greeting_only(text: str) -> bool:
    text = normalize_text(text)

    greetings = [
        "салем",
        "салам",
        "привет",
        "здравствуйте",
        "здрасьте",
        "добрый день",
        "добрый вечер",
        "доброе утро",
        "хай",
        "hello",
        "hi",
        "ассаламу алейкум",
        "алейкум салам",
    ]

    return text in greetings


def looks_offtopic(text: str) -> bool:
    text = normalize_text(text)

    obvious_offtopic = [
        "хлеб",
        "морожен",
        "клубник",
        "напитк",
        "пицц",
        "шаурм",
        "погода",
        "анекдот",
        "кофе",
        "чай",
        "еда",
        "продукт",
        "яблок",
        "банан",
        "доставка еды",
    ]
    return has_any(text, obvious_offtopic)


def contains_location_markers(text: str) -> bool:
    text = normalize_text(text)

    location_words = [
        "район",
        "мкр",
        "микрорайон",
        "улица",
        "ул",
        "проспект",
        "пр",
        "город",
        "жк",
        "квартал",
        "центр",
        "левый берег",
        "правый берег",
        "алматы",
        "астана",
        "шымкент",
        "караганда",
        "актау",
        "атырау",
        "актобе",
        "павлодар",
        "костанай",
        "усть-каменогорск",
        "семей",
        "тарaз",
        "талдыкорган",
        "туркестан",
        "кызылорда",
        "петропавловск",
        "кокшетау",
        "уральск",
    ]

    return has_any(text, location_words)


def is_valid_district_answer(raw_text: str) -> bool:
    text = normalize_text(raw_text)

    if len(text) < 2:
        return False

    if is_greeting_only(text):
        return False

    if looks_offtopic(text):
        return False

    if parse_request_type(text):
        return False

    if parse_property_type(text):
        return False

    if parse_rooms(text):
        return False

    if parse_budget(text):
        return False

    if parse_purpose(text):
        return False

    if is_question(text):
        return False

    if contains_location_markers(text):
        return True

    # Разрешаем короткие реальные ответы вроде "нурсая", "самал", "ботанический"
    words = text.split()
    if len(words) <= 4 and all(len(w) >= 2 for w in words):
        return True

    return False


def is_valid_rooms_answer(raw_text: str) -> bool:
    text = normalize_text(raw_text)

    if is_greeting_only(text):
        return False

    if looks_offtopic(text):
        return False

    parsed = parse_rooms(text)
    return parsed is not None


def is_valid_name_answer(raw_text: str) -> bool:
    text = normalize_text(raw_text)

    if len(text) < 2:
        return False

    if is_greeting_only(text):
        return False

    if looks_offtopic(text):
        return False

    if parse_request_type(text):
        return False

    if parse_property_type(text):
        return False

    if parse_rooms(text):
        return False

    if parse_budget(text):
        return False

    if parse_purpose(text):
        return False

    if contains_location_markers(text):
        return False

    if len(text.split()) > 4:
        return False

    return True


# =====================
# РАСПОЗНАВАНИЕ СМЫСЛА
# =====================

def parse_request_type(text: str):
    text = normalize_text(text)

    if has_any(text, ["куп", "покуп", "приобр"]):
        return "покупка"

    if has_any(text, ["аренд", "снять", "съем", "съём"]):
        return "аренда"

    if has_any(text, ["прод", "прода", "реализ"]):
        return "продажа"

    return None


def parse_property_type(text: str):
    text = normalize_text(text)

    if "квартир" in text:
        return "квартира"

    if "дом" in text or "коттедж" in text or "таунхаус" in text:
        return "дом"

    if "участ" in text or "земл" in text:
        return "участок"

    if "коммер" in text or "офис" in text or "магазин" in text or "помещ" in text:
        return "коммерция"

    return None


def parse_rooms(text: str):
    text = normalize_text(text)

    if has_any(text, ["не принцип", "неважно", "без разницы", "любое", "любая"]):
        return "не принципиально"

    if text in ["1", "1к", "1 к"]:
        return "1"

    if text in ["2", "2к", "2 к"]:
        return "2"

    if text in ["3", "3к", "3 к"]:
        return "3"

    if text in ["4", "4к", "4 к"]:
        return "4"

    if text in ["5", "5+", "5 к", "5к"]:
        return "5+"

    room_patterns = {
        "1": ["1-ком", "1 ком", "одноком", "одна ком", "1 комнат", "1 комнатную"],
        "2": ["2-ком", "2 ком", "двухком", "две ком", "2 комнат", "2 комнатную"],
        "3": ["3-ком", "3 ком", "трехком", "трёхком", "3 комнат", "3 комнатную"],
        "4": ["4-ком", "4 ком", "четырехком", "четырёхком", "4 комнат", "4 комнатную"],
        "5+": ["5-ком", "5 ком", "многоком", "много комнат", "5 комнат"],
    }

    for normalized, variants in room_patterns.items():
        if has_any(text, variants):
            return normalized

    if "студ" in text:
        return "студия"

    return None


def parse_budget(text: str):
    text = normalize_text(text)

    if has_any(text, ["без лимита", "не знаю", "пока не знаю", "не определ", "не принцип"]):
        return text

    has_digits = any(ch.isdigit() for ch in text)
    if not has_digits:
        return None

    if has_any(text, ["млн", "миллион", "тыс", "тенге", "тг", "$", "usd", "доллар", "в месяц", "ежемесячно"]):
        return text

    if has_digits and len(text) >= 2:
        return text

    return None


def parse_purpose(text: str):
    text = normalize_text(text)

    if has_any(text, ["для себя", "себе", "жить", "прожив", "собственного проживания"]):
        return "для себя"

    if has_any(text, ["инвест", "вложен"]):
        return "инвестиция"

    if has_any(text, ["перепрод", "перепродажа"]):
        return "перепродажа"

    if has_any(text, ["сдач", "под аренду", "сдавать"]):
        return "под аренду"

    return None


def parse_name(text: str):
    text = text.strip()

    if len(text) < 2:
        return None

    bad_variants = [
        "не скажу",
        "не важно",
        "без имени",
        "не хочу",
        "зачем",
        "ааа",
        "хлеб",
        "мороженое",
        "клубника",
        "напитки",
        "продукты",
    ]

    if normalize_text(text) in bad_variants:
        return None

    if not is_valid_name_answer(text):
        return None

    return text


# =====================
# ИЗВЛЕЧЕНИЕ ДАННЫХ
# =====================

def extract_entities(text: str):
    normalized = normalize_text(text)

    return {
        "request_type": parse_request_type(normalized),
        "property_type": parse_property_type(normalized),
        "rooms": parse_rooms(normalized),
        "budget": parse_budget(normalized),
        "purpose": parse_purpose(normalized),
    }


def fill_conversation_from_entities(conversation, entities: dict):
    if not conversation.request_type and entities.get("request_type"):
        conversation.request_type = entities["request_type"]

    if not conversation.property_type and entities.get("property_type"):
        conversation.property_type = entities["property_type"]

    if not conversation.rooms and entities.get("rooms"):
        conversation.rooms = entities["rooms"]

    if not conversation.budget and entities.get("budget"):
        conversation.budget = entities["budget"]

    if not conversation.purpose and entities.get("purpose"):
        conversation.purpose = entities["purpose"]


def get_next_question(conversation):
    if not conversation.request_type:
        conversation.state = "asked_request_type"
        return fallback_request_type()

    if not conversation.property_type:
        conversation.state = "asked_property_type"
        return ask_property_type()

    if not conversation.district:
        conversation.state = "asked_district"
        return ask_district()

    if not conversation.rooms:
        conversation.state = "asked_rooms"
        return ask_rooms()

    if not conversation.budget:
        conversation.state = "asked_budget"
        return ask_budget()

    if not conversation.purpose:
        conversation.state = "asked_purpose"
        return ask_purpose()

    if not conversation.name:
        conversation.state = "asked_name"
        return ask_name()

    conversation.state = "waiting_manager"
    return None


def create_lead_from_conversation(db, account, conversation):
    lead = Lead(
        account_id=conversation.account_id,
        name=conversation.name,
        phone=conversation.phone,
        request_type=conversation.request_type,
        property_type=conversation.property_type,
        district=conversation.district,
        rooms=conversation.rooms,
        budget=conversation.budget,
        purpose=conversation.purpose,
    )

    db.add(lead)
    db.commit()

    send_lead_to_telegram(account, lead)


# =====================
# ОСНОВНАЯ ЛОГИКА
# =====================

def process_message(db, account: Account, phone: str, text: str):
    raw_text = text.strip()
    text = normalize_text(raw_text)

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.phone == phone,
            Conversation.account_id == account.id,
        )
        .first()
    )

    if not conversation:
        conversation = Conversation(
            phone=phone,
            account_id=account.id,
            state="new",
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    if is_pricing_request(raw_text):
        return {"reply": pricing_reply()}

    if is_payment_request(raw_text):
        return {"reply": payment_reply()}

    if is_paid_confirmation(raw_text):
        return {"reply": paid_confirmation_reply()}

    if not can_bot_reply(account, conversation):
        reason = get_bot_block_reason(account, conversation)
        return {"reply": block_reason_reply(reason)}

    valid_states = {
        "new",
        "asked_request_type",
        "asked_property_type",
        "asked_district",
        "asked_rooms",
        "asked_budget",
        "asked_purpose",
        "asked_name",
        "waiting_manager",
    }

    if conversation.state not in valid_states:
        conversation.state = "new"
        db.commit()

    if conversation.state == "waiting_manager":
        faq = try_faq(raw_text)
        if faq:
            return faq

        if looks_offtopic(text):
            return {
                "reply": "К сожалению, мы занимаемся только недвижимостью 🙂 Специалист скоро свяжется с вами по вашей заявке."
            }

        return {"reply": "Спасибо, я зафиксировал сообщение. Специалист скоро свяжется с вами 🙂"}

    if is_question(raw_text):
        faq = try_faq(raw_text)
        if faq:
            return faq

    if conversation.state == "new":
        entities = extract_entities(raw_text)
        fill_conversation_from_entities(conversation, entities)
        next_question = get_next_question(conversation)
        db.commit()

        if not any(entities.values()):
            return {"reply": first_question()}

        return {"reply": next_question or final_reply()}

    if conversation.state == "asked_request_type":
        parsed = parse_request_type(text)
        if not parsed:
            if looks_offtopic(text):
                return {"reply": off_topic_reply(fallback_request_type())}
            return {"reply": fallback_request_type()}

        conversation.request_type = parsed
        fill_conversation_from_entities(conversation, extract_entities(raw_text))
        next_question = get_next_question(conversation)
        db.commit()
        return {"reply": next_question or final_reply()}

    if conversation.state == "asked_property_type":
        parsed = parse_property_type(text)
        if not parsed:
            if looks_offtopic(text):
                return {"reply": off_topic_reply(fallback_property_type())}
            return {"reply": fallback_property_type()}

        conversation.property_type = parsed
        fill_conversation_from_entities(conversation, extract_entities(raw_text))
        next_question = get_next_question(conversation)
        db.commit()
        return {"reply": next_question or final_reply()}

    if conversation.state == "asked_district":
        if not is_valid_district_answer(raw_text):
            if looks_offtopic(text):
                return {"reply": off_topic_reply(fallback_district())}
            return {"reply": fallback_district()}

        conversation.district = raw_text
        fill_conversation_from_entities(conversation, extract_entities(raw_text))
        next_question = get_next_question(conversation)
        db.commit()
        return {"reply": next_question or final_reply()}

    if conversation.state == "asked_rooms":
        parsed = parse_rooms(text)
        if not parsed:
            if looks_offtopic(text):
                return {"reply": off_topic_reply(fallback_rooms())}
            return {"reply": fallback_rooms()}

        conversation.rooms = parsed
        fill_conversation_from_entities(conversation, extract_entities(raw_text))
        next_question = get_next_question(conversation)
        db.commit()
        return {"reply": next_question or final_reply()}

    if conversation.state == "asked_budget":
        parsed = parse_budget(text)
        if not parsed:
            if looks_offtopic(text):
                return {"reply": off_topic_reply(fallback_budget())}
            return {"reply": fallback_budget()}

        conversation.budget = parsed
        fill_conversation_from_entities(conversation, extract_entities(raw_text))
        next_question = get_next_question(conversation)
        db.commit()
        return {"reply": next_question or final_reply()}

    if conversation.state == "asked_purpose":
        parsed = parse_purpose(text)
        if not parsed:
            if looks_offtopic(text):
                return {"reply": off_topic_reply(fallback_purpose())}
            return {"reply": fallback_purpose()}

        conversation.purpose = parsed
        fill_conversation_from_entities(conversation, extract_entities(raw_text))
        next_question = get_next_question(conversation)
        db.commit()
        return {"reply": next_question or final_reply()}

    if conversation.state == "asked_name":
        parsed = parse_name(raw_text)
        if not parsed:
            if looks_offtopic(text):
                return {"reply": off_topic_reply(fallback_name())}
            return {"reply": fallback_name()}

        conversation.name = parsed
        conversation.state = "waiting_manager"
        conversation.lead_sent = True
        db.commit()

        create_lead_from_conversation(db, account, conversation)

        return {"reply": final_reply()}

    return {"reply": first_question()}