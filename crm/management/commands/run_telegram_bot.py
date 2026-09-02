import asyncio
from contextlib import suppress

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
        from crm.telegram_bot import reminder_loop, router

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        dispatcher = Dispatcher()
        dispatcher.include_router(router)
        reminder_task = asyncio.create_task(reminder_loop(bot))
        self.stdout.write(self.style.SUCCESS('Telegram bot started'))
        try:
            await dispatcher.start_polling(bot)
        finally:
            reminder_task.cancel()
            with suppress(asyncio.CancelledError):
                await reminder_task
            await bot.session.close()
