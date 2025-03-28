from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# تعریف منوی اصلی
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 دوره‌های آموزشی"), KeyboardButton(text="🎯 رویدادها")],
        [KeyboardButton(text="🏛 بازدیدها"), KeyboardButton(text="👤 پروفایل من")],
        [KeyboardButton(text="📝 ثبت‌نام دوره/بازدید")]
    ],
    resize_keyboard=True
)