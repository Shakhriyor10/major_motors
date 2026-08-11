import logging
from html import escape

from asgiref.sync import async_to_sync
from django.conf import settings


logger = logging.getLogger(__name__)


def format_lead_message(lead, contact_type, created=True):
    employee = str(lead.employee) if lead.employee_id else 'Не указан'
    interaction = 'Позвонил' if contact_type == 'call' else 'Посетил автосалон'
    heading = 'Новый лид' if created else 'Новое обращение лида'
    comment = lead.comment or '—'
    if len(comment) > 2500:
        comment = comment[:2499] + '…'
    return (
        f'<b>🔔 {heading}</b>\n\n'
        f'<b>Имя:</b> {escape(lead.name)}\n'
        f'<b>Телефон:</b> {escape(lead.phone)}\n'
        f'<b>Тип обращения:</b> {interaction}\n'
        f'<b>Кто обслужил:</b> {escape(employee)}\n'
        f'<b>Комментарий:</b> {escape(comment)}'
    )


async def _send_lead_message(text):
    from aiogram import Bot
    from aiogram.enums import ParseMode

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=settings.TELEGRAM_LEADS_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    finally:
        await bot.session.close()


def notify_lead_saved(lead, contact_type, created=True):
    """Notify Telegram without making lead creation depend on Telegram uptime."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_LEADS_CHAT_ID:
        return False
    try:
        async_to_sync(_send_lead_message)(
            format_lead_message(lead, contact_type, created=created)
        )
        return True
    except Exception:
        logger.exception('Could not send lead #%s to Telegram', lead.pk)
        return False
