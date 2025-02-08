from config import TOKEN
import asyncio
from aiogram import Bot, Dispatcher, types
from handlers import router,scheduler
from middlewares import LoggingMiddleware

bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.include_routers(router)
dp.message.middleware(LoggingMiddleware())

async def main():
    print("Бот запущен")
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())