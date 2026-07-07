import html


def _safe(value) -> str:
    return html.escape(str(value), quote=False)


def _format_telegram_username(username: str | None) -> str:
    if not username:
        return "не указан"
    return "@" + _safe(username.lstrip("@"))


def _telegram_user_link(user_id: int | None, label: str) -> str:
    if not user_id:
        return "не указан"
    return f'<a href="tg://user?id={int(user_id)}">{_safe(label)}</a>'


def build_client_notification_text(job, carrier) -> str:
    carrier_name = carrier.contact_name or carrier.company_name or "перевозчик"
    return (
        f"Перевозчик найден и принял заказ №{job.id}.\n\n"
        f"Компания: {_safe(carrier.company_name or 'не указана')}\n"
        f"Контакт: {_safe(carrier.contact_name or 'не указано')}\n"
        f"Telegram: {_telegram_user_link(carrier.telegram_user_id, carrier_name)}\n"
        f"Телефон: {_safe(carrier.phone or 'не указан')}\n\n"
        "Свяжитесь напрямую и согласуйте детали перевозки.\n\n"
        "После разговора вернитесь в этот чат и подтвердите, состоялась ли сделка."
    )


def _format_client_identity(job) -> str:
    if job.client_telegram_user_id is not None and job.client_telegram_username:
        return _telegram_user_link(job.client_telegram_user_id, job.client_telegram_username)
    return _safe(job.customer_name or "S/N")


def _format_client_username(job) -> str:
    if job.client_telegram_username:
        return _format_telegram_username(job.client_telegram_username)
    return "S/N"


def build_carrier_notification_text(job, carrier) -> str:
    return (
        f"Заказ №{job.id} закреплён за вами.\n\n"
        f"Клиент: {_format_client_identity(job)}\n"
        f"Username: {_format_client_username(job)}\n"
        f"Телефон: {_safe(job.client_phone or 'не указан')}\n"
        f"WhatsApp: {_safe(job.client_whatsapp or 'не указан')}\n\n"
        "Свяжитесь с клиентом и согласуйте детали перевозки.\n\n"
        "После разговора вернитесь в этот чат и подтвердите, состоялась ли сделка."
    )

