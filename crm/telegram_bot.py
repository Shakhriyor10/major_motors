import asyncio
import logging
from html import escape

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import F
from django.utils import timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .models import LeadEntry


router = Router()
PAGE_SIZE = 5
logger = logging.getLogger(__name__)


def _is_allowed(user_id):
    allowed = settings.TELEGRAM_ALLOWED_USER_IDS
    return not allowed or user_id in allowed


def _load_leads(page):
    page = max(page, 0)
    queryset = LeadEntry.objects.select_related('employee').order_by('-updated_at')
    total = queryset.count()
    leads = list(queryset[page * PAGE_SIZE:(page + 1) * PAGE_SIZE])
    return leads, total


def _lead_text(lead):
    if lead.last_call_at and (not lead.visit_date or lead.last_call_at >= lead.visit_date):
        interaction = f'Позвонил ({lead.last_call_at:%d.%m.%Y})'
    elif lead.visit_date:
        interaction = f'Посетил ({lead.visit_date:%d.%m.%Y})'
    else:
        interaction = 'Не указан'
    comment = lead.comment or '—'
    if len(comment) > 350:
        comment = comment[:349] + '…'
    return (
        f'#{lead.pk} — {lead.name}\n'
        f'📞 {lead.phone}\n'
        f'📌 {interaction}\n'
        f'👤 {lead.employee or "Не указан"}\n'
        f'💬 {comment}\n'
        f'📅 Следующее действие: {lead.next_action_date.strftime("%d.%m.%Y") if lead.next_action_date else "Не указано"}\n'
        f'Статус: {lead.get_status_display()}'
    )


def _load_upcoming_leads(limit=20):
    return list(
        LeadEntry.objects.select_related('employee')
        .exclude(status=LeadEntry.Status.CLOSED)
        .filter(next_action_date__isnull=False)
        .order_by('next_action_date', 'name')[:limit]
    )


def _load_due_leads():
    today = timezone.localdate()
    return list(
        LeadEntry.objects.select_related('employee')
        .exclude(status=LeadEntry.Status.CLOSED)
        .filter(next_action_date__lte=today)
        .exclude(next_action_notified_date=F('next_action_date'))
        .order_by('next_action_date', 'name')
    )


def _mark_reminder_sent(lead_id, action_date):
    LeadEntry.objects.filter(pk=lead_id, next_action_date=action_date).update(
        next_action_notified_date=action_date
    )


def _upcoming_text(leads):
    if not leads:
        return 'Ближайших запланированных звонков пока нет.'
    today = timezone.localdate()
    items = []
    for lead in leads:
        if lead.next_action_date < today:
            date_label = f'ПРОСРОЧЕНО · {lead.next_action_date:%d.%m.%Y}'
        elif lead.next_action_date == today:
            date_label = 'СЕГОДНЯ'
        else:
            date_label = lead.next_action_date.strftime('%d.%m.%Y')
        items.append(
            f'<b>{date_label}</b> · {escape(lead.name)}\n'
            f'📞 {escape(lead.phone)}\n'
            f'👤 {escape(str(lead.employee) if lead.employee else "Не указан")}'
        )
    return '<b>📅 Ближайшие звонки и покупки</b>\n\n' + '\n\n'.join(items)


def _reminder_text(lead):
    today = timezone.localdate()
    overdue = lead.next_action_date < today
    heading = '⚠️ Просроченное действие по лиду' if overdue else '⏰ Сегодня нужно связаться с лидом'
    return (
        f'<b>{heading}</b>\n\n'
        f'<b>Дата:</b> {lead.next_action_date:%d.%m.%Y}\n'
        f'<b>Имя:</b> {escape(lead.name)}\n'
        f'<b>Телефон:</b> {escape(lead.phone)}\n'
        f'<b>Менеджер:</b> {escape(str(lead.employee) if lead.employee else "Не указан")}\n'
        f'<b>Комментарий:</b> {escape(lead.comment or "—")}'
    )


async def reminder_loop(bot):
    """Send each due reminder once; a changed action date can be notified again."""
    while True:
        try:
            if settings.TELEGRAM_LEADS_CHAT_ID:
                due_leads = await sync_to_async(_load_due_leads, thread_sensitive=True)()
                for lead in due_leads:
                    await bot.send_message(
                        chat_id=settings.TELEGRAM_LEADS_CHAT_ID,
                        text=_reminder_text(lead),
                        parse_mode='HTML',
                    )
                    await sync_to_async(_mark_reminder_sent, thread_sensitive=True)(
                        lead.pk, lead.next_action_date
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Telegram lead reminder check failed')
        await asyncio.sleep(60)


def _keyboard(page, total):
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text='← Назад', callback_data=f'leads:{page - 1}'))
    if (page + 1) * PAGE_SIZE < total:
        buttons.append(InlineKeyboardButton(text='Далее →', callback_data=f'leads:{page + 1}'))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None


async def _render_leads(page):
    leads, total = await sync_to_async(_load_leads, thread_sensitive=True)(page)
    if not leads:
        return 'Лидов пока нет.', None
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    text = f'📋 Лиды — страница {page + 1}/{pages}\n\n' + '\n\n'.join(
        _lead_text(lead) for lead in leads
    )
    return text, _keyboard(page, total)


@router.message(CommandStart())
async def start(message: Message):
    if not _is_allowed(message.from_user.id):
        await message.answer('У вас нет доступа к лидам.')
        return
    await message.answer('Бот Major Motors CRM готов. Для просмотра последних лидов: /leads')


@router.message(Command('leads'))
async def leads(message: Message):
    if not _is_allowed(message.from_user.id):
        await message.answer('У вас нет доступа к лидам.')
        return
    text, markup = await _render_leads(0)
    await message.answer(text, reply_markup=markup)


@router.message(Command('upcoming'))
async def upcoming(message: Message):
    if not _is_allowed(message.from_user.id):
        await message.answer('У вас нет доступа к лидам.')
        return
    upcoming_leads = await sync_to_async(_load_upcoming_leads, thread_sensitive=True)()
    await message.answer(_upcoming_text(upcoming_leads), parse_mode='HTML')


@router.message(Command('chatid'))
async def chat_id(message: Message):
    """Show the current chat ID to simplify initial group configuration."""
    await message.answer(f'ID этого чата: <code>{message.chat.id}</code>', parse_mode='HTML')


@router.callback_query(F.data.startswith('leads:'))
async def leads_page(callback: CallbackQuery):
    if not _is_allowed(callback.from_user.id):
        await callback.answer('Нет доступа', show_alert=True)
        return
    try:
        page = max(0, int(callback.data.split(':', 1)[1]))
    except (TypeError, ValueError):
        page = 0
    text, markup = await _render_leads(page)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()
