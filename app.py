import os
import asyncio

from aiogram import Bot, Dispatcher


from handlers.user_private import user_private_router
from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=os.getenv("API_TOKEN_BOT"))
dp = Dispatcher()
dp.include_router(user_private_router)


async def main():

    await bot.delete_webhook(drop_pending_updates=True)  # чтобы те обновления, которые присылались боту ,когда он был в офлайне к нему не приходили
    await dp.start_polling(bot)   # бот начинает слушать сервер телеграм


asyncio.run(main())