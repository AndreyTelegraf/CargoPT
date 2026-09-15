from __future__ import annotations

from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

from app.bot.carrier_locale import normalize_carrier_locale


CAMPAIGN_KEY = "urgent_availability_2026_09"
CALLBACK_PREFIX = "urg1"
RESPONSE_CODES = (
    "same_day",
    "next_day",
    "two_three_days",
    "no_urgent",
)


REPORT_RESPONSE_LABELS_RU = {
    "same_day": "может выехать в тот же день",
    "next_day": "может выехать на следующий день",
    "two_three_days": "нужно 2–3 дня",
    "no_urgent": "не хочет получать срочные заявки",
}


SURVEY_TEXT = {
    "pt": (
        "Breve questionário da CargoPT\n\n"
        "Muitos pedidos novos chegam menos de 72 horas antes do transporte. "
        "Queremos enviar-lhe apenas os pedidos urgentes que pode considerar.\n\n"
        "Qual é normalmente a antecedência mínima de que precisa, "
        "se tiver um veículo disponível?\n\n"
        "A resposta serve apenas para configurar as notificações. "
        "Não é um compromisso de aceitar um serviço específico."
    ),
    "en": (
        "Short CargoPT survey\n\n"
        "Many new requests arrive less than 72 hours before transport. "
        "We want to send you only the urgent requests you may be able to consider.\n\n"
        "What is the minimum notice you usually need, if you have a vehicle available?\n\n"
        "Your answer is only used to configure notifications. "
        "It is not a commitment to accept a specific job."
    ),
    "ru": (
        "Короткий опрос CargoPT\n\n"
        "Многие новые заявки приходят менее чем за 72 часа до перевозки. "
        "Хотим присылать вам только те срочные заявки, которые вы можете рассматривать.\n\n"
        "Какой минимальный срок до выезда вам обычно нужен, "
        "если есть свободная машина?\n\n"
        "Ответ нужен только для настройки уведомлений. "
        "Он не обязывает вас принимать конкретную заявку."
    ),
}


RESPONSE_LABELS = {
    "pt": {
        "same_day": "Consigo no próprio dia",
        "next_day": "Consigo no dia seguinte",
        "two_three_days": "Preciso de 2–3 dias",
        "no_urgent": "Não quero pedidos urgentes",
    },
    "en": {
        "same_day": "I can do the same day",
        "next_day": "I can do the next day",
        "two_three_days": "I need 2–3 days",
        "no_urgent": "I do not want urgent requests",
    },
    "ru": {
        "same_day": "Могу в тот же день",
        "next_day": "Могу на следующий день",
        "two_three_days": "Нужно 2–3 дня",
        "no_urgent": "Не хочу срочные заявки",
    },
}


SAVED_TEXT = {
    "pt": "Resposta guardada: {answer}. Pode alterá-la premindo outro botão.",
    "en": "Answer saved: {answer}. You can change it by pressing another button.",
    "ru": "Ответ сохранён: {answer}. Его можно изменить, нажав другую кнопку.",
}


def survey_text(locale: str | None) -> str:
    return SURVEY_TEXT[normalize_carrier_locale(locale)]


def response_label(locale: str | None, response_code: str) -> str:
    language = normalize_carrier_locale(locale)
    if response_code not in RESPONSE_CODES:
        raise ValueError("unsupported urgent survey response")
    return RESPONSE_LABELS[language][response_code]


def saved_text(locale: str | None, response_code: str) -> str:
    language = normalize_carrier_locale(locale)
    return SAVED_TEXT[language].format(
        answer=response_label(language, response_code)
    )


def build_urgent_survey_report_text(
    *,
    carrier_id: int,
    carrier_label: str,
    carrier_telegram_username: str | None,
    locale: str,
    response_code: str,
    previous_response_code: str | None,
) -> str:
    if response_code not in RESPONSE_CODES:
        raise ValueError("unsupported urgent survey response")
    if (
        previous_response_code is not None
        and previous_response_code not in RESPONSE_CODES
    ):
        raise ValueError("unsupported previous urgent survey response")

    username = (carrier_telegram_username or "").strip().lstrip("@")
    telegram_line = f"@{username}" if username else "не указан"
    if previous_response_code is None:
        status_line = "Новый ответ"
    else:
        status_line = (
            "Ответ изменён: "
            f"{REPORT_RESPONSE_LABELS_RU[previous_response_code]} → "
            f"{REPORT_RESPONSE_LABELS_RU[response_code]}"
        )

    return (
        "📨 Ответ перевозчика по срочным выездам\n\n"
        f"Компания: {carrier_label}\n"
        f"Telegram: {telegram_line}\n"
        f"ID перевозчика: {carrier_id}\n"
        f"Язык опроса: {normalize_carrier_locale(locale).upper()}\n"
        f"Ответ: {REPORT_RESPONSE_LABELS_RU[response_code]}\n"
        f"Статус: {status_line}"
    )


def build_urgent_survey_keyboard(
    *,
    survey_id: int,
    locale: str | None,
    selected_response: str | None = None,
) -> InlineKeyboardMarkup:
    language = normalize_carrier_locale(locale)
    rows = []
    for code in RESPONSE_CODES:
        label = RESPONSE_LABELS[language][code]
        if code == selected_response:
            label = f"✅ {label}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{CALLBACK_PREFIX}:{survey_id}:{code}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def parse_urgent_survey_callback(value: str | None) -> tuple[int, str] | None:
    parts = (value or "").split(":")
    if len(parts) != 3 or parts[0] != CALLBACK_PREFIX:
        return None
    try:
        survey_id = int(parts[1])
    except ValueError:
        return None
    response_code = parts[2]
    if survey_id <= 0 or response_code not in RESPONSE_CODES:
        return None
    return survey_id, response_code
