import logging
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiohttp import web
from database.db import setup_database
from handlers.admin import register_handlers as register_admin_handlers
from handlers.register import register_handlers as register_register_handlers
from handlers.contact import register_handlers as register_contact_handlers
from keyboards import main_menu

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# متغیرهای محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [int(x) for x in os.getenv("ADMINS", "0").split(",") if x]
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://anjoman.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", 8000))

# تعریف سراسری Bot و Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

CONTACT_INFO = """
📞 **راه‌های ارتباطی با ما:**\n
📌 تلگرام: [ارتباط با ادمین](https://t.me/Tut_ECS)\n
📌 کانال انجمن: [ورود به کانال](https://t.me/electrical_sut)\n
📩 *لطفاً پیام خود را ارسال کنید، تیم ما در اسرع وقت پاسخ خواهد داد\.*
"""

# تابع کمکی برای فرار کاراکترهای خاص در MarkdownV2
def escape_markdown_v2(text: str) -> str:
    reserved_chars = r"_*[]()~`>#+-=|{}.!"
    for char in reserved_chars:
        text = text.replace(char, f"\\{char}")
    return text

async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    welcome_text = (
        "👋 به ربات انجمن علمی مهندسی برق و کامپیوتر دانشگاه صنعتی تبریز خوش آمدید!\n\n"
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
    courses = await get_courses()
    if not courses:
        await message.reply("هیچ دوره‌ای موجود نیست!", reply_markup=main_menu)
        return
    
    # ارسال هر دوره به صورت پیام جداگانه
    for course in courses:
        # فرمت‌بندی و فرار کاراکترها
        description = course["description"][:800]  # محدود به 800 کاراکتر
        text = (
            "📚 *دوره آموزشی:*\n"  # باز و بسته کردن درست Markdown
            f"*عنوان:* {escape_markdown_v2(course['title'])}\n"
            f"*هزینه:* {escape_markdown_v2(str(course['cost']))} تومان\n"
            f"*توضیحات:* {escape_markdown_v2(description)}"
        )
        logger.debug(f"Sending course: {course['title']}, photo: {course.get('photo')}, caption length: {len(text)}")
        try:
            if course.get("photo"):  # اگه عکس داره
                await message.bot.send_photo(
                    chat_id=message.chat.id,
                    photo=course["photo"],
                    caption=text,
                    parse_mode="MarkdownV2"
                )
            else:  # اگه عکس نداره
                await message.bot.send_message(
                    chat_id=message.chat.id,
                    text=text,
                    parse_mode="MarkdownV2"
                )
            await asyncio.sleep(0.5)  # تأخیر برای جلوگیری از اسپم
        except Exception as e:
            logger.error(f"Error sending course {course['title']}: {str(e)}")
            await message.reply(f"خطا در نمایش دوره {course['title']}", reply_markup=main_menu)
    
    await message.reply("این‌ها دوره‌های موجود بودن!", reply_markup=main_menu)

async def show_events(message: types.Message):
    from database.db import get_events
    events = await get_events()
    if not events:
        await message.reply("هیچ رویدادی موجود نیست!", reply_markup=main_menu)
        return
    response = "🎯 رویدادها:\n\n"
    for event in events:
        response += f"عنوان: {event['title']}\nتاریخ: {event['date']}\nتوضیحات: {event['description']}\n\n"
    await message.reply(response, reply_markup=main_menu)

async def show_visits(message: types.Message):
    from database.db import get_visits
    visits = await get_visits()
    if not visits:
        await message.reply("هیچ بازدیدی موجود نیست!", reply_markup=main_menu)
        return
    response = "🏛 بازدیدها:\n\n"
    for visit in visits:
        response += f"عنوان: {visit['title']}\nهزینه: {visit['cost']} تومان\nتوضیحات: {visit['description']}\n\n"
    await message.reply(response, reply_markup=main_menu)

async def show_profile(message: types.Message):
    from database.db import get_user
    user = await get_user(str(message.from_user.id))
    if not user or not user['registered']:
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

async def show_contact(message: types.Message):
    await message.reply(CONTACT_INFO, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=main_menu)

def register_handlers(dp: Dispatcher):
    dp.message.register(start_cmd, Command(commands=["start"]))
    dp.message.register(show_courses, lambda msg: msg.text == "📚 دوره‌های آموزشی")
    dp.message.register(show_events, lambda msg: msg.text == "🎯 رویدادها")
    dp.message.register(show_visits, lambda msg: msg.text == "🏛 بازدیدها")
    dp.message.register(show_profile, lambda msg: msg.text == "👤 پروفایل من")
    dp.message.register(show_contact, lambda msg: msg.text == "📞 تماس با ما")
    register_admin_handlers(dp)
    register_register_handlers(dp)
    register_contact_handlers(dp)

async def on_startup(_):
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    await setup_database()
    register_handlers(dp)
    logger.info("Bot started")

async def handle_webhook(request):
    update = types.Update(**(await request.json()))
    await dp.feed_update(bot=bot, update=update)
    return web.Response(text="OK", status=200)

async def main():
    try:
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not set")
            return

        app = web.Application()
        app.add_routes([web.post(WEBHOOK_PATH, handle_webhook)])
        app.on_startup.append(on_startup)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"Server started on port {PORT}")

        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"Bot crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
