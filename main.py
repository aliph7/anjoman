import logging
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from database.db import setup_database
from handlers.admin import register_handlers as register_admin_handlers
from handlers.register import register_handlers as register_register_handlers
from keyboards import main_menu  # ایمپورت از keyboards.py

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    welcome_text = (
        "👋 به ربات IEEE خوش آمدید!\n\n"
        "از منوی زیر می‌توانید:\n"
        "📚 دوره‌های آموزشی را مشاهده کنید\n"
        "🎯 در رویدادها شرکت کنید\n"
        "🏛 در بازدیدها ثبت‌نام کنید\n"
        "👤 پروفایل خود را مدیریت کنید\n"
        "📝 در دوره یا بازدید ثبت‌نام کنید"
    )
    await message.reply(welcome_text, reply_markup=main_menu)

async def show_courses(message: types.Message):
    from database.db import get_courses
    courses = get_courses()
    if not courses:
        await message.reply("هیچ دوره‌ای موجود نیست!")
        return
    response = "📚 دوره‌های آموزشی:\n\n"
    for course in courses:
        response += f"عنوان: {course['title']}\nهزینه: {course['cost']} تومان\nتوضیحات: {course['description']}\n\n"
    await message.reply(response, reply_markup=main_menu)

async def show_events(message: types.Message):
    from database.db import get_events
    events = get_events()
    if not events:
        await message.reply("هیچ رویدادی موجود نیست!")
        return
    response = "🎯 رویدادها:\n\n"
    for event in events:
        response += f"عنوان: {event[0]}\nتاریخ: {event[1]}\nتوضیحات: {event[2]}\n\n"
    await message.reply(response, reply_markup=main_menu)

async def show_visits(message: types.Message):
    from database.db import get_visits
    visits = get_visits()
    if not visits:
        await message.reply("هیچ بازدیدی موجود نیست!")
        return
    response = "🏛 بازدیدها:\n\n"
    for visit in visits:
        response += f"عنوان: {visit['title']}\nهزینه: {visit['cost']} تومان\nتوضیحات: {visit['description']}\n\n"
    await message.reply(response, reply_markup=main_menu)

async def show_profile(message: types.Message):
    from database.db import get_user
    user = get_user(str(message.from_user.id))
    if not user or not user[6]:  # registered = 0
        await message.reply("لطفاً اول ثبت‌نام کن! از '📝 ثبت‌نام دوره/بازدید' استفاده کن.")
        return
    response = (
        f"👤 پروفایل شما:\n"
        f"اسم: {user['name']}\n"
        f"رشته: {user['field']}\n"
        f"شماره دانشجویی: {user['student_id']}\n"
        f"تلفن: {user['phone']}\n"
        f"ایمیل: {user['email']}"
    )
    await message.reply(response, reply_markup=main_menu)

def register_handlers(dp: Dispatcher):
    dp.message.register(start_cmd, Command(commands=["start"]))
    dp.message.register(show_courses, lambda msg: msg.text == "📚 دوره‌های آموزشی")
    dp.message.register(show_events, lambda msg: msg.text == "🎯 رویدادها")
    dp.message.register(show_visits, lambda msg: msg.text == "🏛 بازدیدها")
    dp.message.register(show_profile, lambda msg: msg.text == "👤 پروفایل من")
    register_admin_handlers(dp)
    register_register_handlers(dp)

async def main():
    try:
        if not BOT_TOKEN or not ADMIN_ID:
            logger.error("BOT_TOKEN or ADMIN_ID not set in .env")
            return
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        register_handlers(dp)
        setup_database()
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main())