from asgiref.sync import sync_to_async
from django.conf import settings

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .models import LeadEntry


router = Router()
PAGE_SIZE = 5


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
        f'Статус: {lead.get_status_display()}'
    )


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
