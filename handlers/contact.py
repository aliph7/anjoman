from aiogram import Router, types, Dispatcher
from aiogram.filters import Command
from database.db import add_contact_message

router = Router()

CONTACT_INFO = """
📞 **راه‌های ارتباطی با ما:**\n
📌 ایمیل: `support@example\.com`\n
📌 تلگرام: [ارتباط با ادمین](https://t.me/admin_username)\n
📌 گروه انجمن: [ورود به گروه](https://t.me/group_link)\n
📩 *لطفاً پیام خود را ارسال کنید، تیم ما در اسرع وقت پاسخ خواهد داد\.*
"""

ADMIN_ID = 100851995  # 🔹 آی‌دی عددی ادمین را اینجا وارد کنید
user_contacting = set()

@router.message(Command("contact"))
async def contact_info(message: types.Message):
    """ ارسال اطلاعات تماس و فعال‌سازی امکان ارسال پیام برای ادمین """
    user_contacting.add(message.from_user.id)
    await message.answer(CONTACT_INFO, parse_mode="MarkdownV2", disable_web_page_preview=True)

@router.message()
async def forward_to_admin(message: types.Message):
    """ فقط پیام‌های مرتبط با `/contact` را به ادمین فوروارد کن و توی دیتابیس ذخیره کن """
    if message.from_user.id not in user_contacting:
        return
    if not message.text:
        await message.answer("⚠️ لطفاً فقط پیام متنی ارسال کنید!")
        return
    add_contact_message(str(message.from_user.id), message.text)
    await message.forward(ADMIN_ID)
    await message.answer("✅ پیام شما به مدیریت ارسال شد!")
    user_contacting.remove(message.from_user.id)

def register_handlers(dp: Dispatcher):
    dp.include_router(router)
