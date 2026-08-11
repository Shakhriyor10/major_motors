import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Run the Major Motors leads Telegram bot (aiogram v3 long polling)'

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('Set TELEGRAM_BOT_TOKEN before starting the bot.')
        asyncio.run(self._run())

    async def _run(self):
        from aiogram import Bot, Dispatcher
        from crm.telegram_bot import router

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        dispatcher = Dispatcher()
        dispatcher.include_router(router)
        self.stdout.write(self.style.SUCCESS('Telegram bot started'))
        try:
            await dispatcher.start_polling(bot)
        finally:
            await bot.session.close()
