from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database.db import get_user, update_user, get_courses, get_visits, add_registration
import logging
import os
from dotenv import load_dotenv
from keyboards import main_menu

load_dotenv()

logger = logging.getLogger(__name__)

class RegisterStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_field = State()
    waiting_for_student_id = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    main_menu = State()
    waiting_for_course = State()
    waiting_for_visit = State()
    waiting_for_receipt = State()

# استفاده از لیست ADMINS به جای یک ADMIN_ID
ADMINS = [int(x) for x in os.getenv("ADMINS", "0").split(",") if x]

register_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 ثبت‌نام دوره"), KeyboardButton(text="🏢 ثبت‌نام بازدید")],
        [KeyboardButton(text="🔙 بازگشت به منوی اصلی")]
    ],
    resize_keyboard=True
)

cancel_button = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="لغو")]],
    resize_keyboard=True
)

async def register_cmd(message: types.Message, state: FSMContext):
    user = await get_user(str(message.from_user.id))  # اضافه کردن await
    if user and user.get("registered", 0):  # چک کردن registered به‌صورت امن
        await message.reply("به بخش ثبت‌نام خوش اومدی!", reply_markup=register_menu)
        await state.set_state(RegisterStates.main_menu)
    else:
        await message.reply("لطفاً اسمت رو وارد کن:", reply_markup=cancel_button)
        await state.set_state(RegisterStates.waiting_for_name)

async def process_name(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("ثبت‌نام لغو شد.", reply_markup=main_menu)
        await state.clear()
        return
    await state.update_data(name=message.text)
    await message.reply("رشته‌ات رو وارد کن:", reply_markup=cancel_button)
    await state.set_state(RegisterStates.waiting_for_field)

async def process_field(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("ثبت‌نام لغو شد.", reply_markup=main_menu)
        await state.clear()
        return
    await state.update_data(field=message.text)
    await message.reply("شماره دانشجوییت رو وارد کن:", reply_markup=cancel_button)
    await state.set_state(RegisterStates.waiting_for_student_id)

async def process_student_id(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("ثبت‌نام لغو شد.", reply_markup=main_menu)
        await state.clear()
        return
    await state.update_data(student_id=message.text)
    await message.reply("شماره تلفنت رو وارد کن:", reply_markup=cancel_button)
    await state.set_state(RegisterStates.waiting_for_phone)

async def process_phone(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("ثبت‌نام لغو شد.", reply_markup=main_menu)
        await state.clear()
        return
    await state.update_data(phone=message.text)
    await message.reply("ایمیلت رو وارد کن:", reply_markup=cancel_button)
    await state.set_state(RegisterStates.waiting_for_email)

async def process_email(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("ثبت‌نام لغو شد.", reply_markup=main_menu)
        await state.clear()
        return
    data = await state.get_data()
    await update_user(str(message.from_user.id), {  # اضافه کردن await
        "name": data["name"],
        "field": data["field"],
        "student_id": data["student_id"],
        "phone": data["phone"],
        "email": message.text
    })
    await message.reply("✅ ثبت‌نام اولیه کامل شد! حالا می‌تونی دوره یا بازدید رو انتخاب کنی:", reply_markup=register_menu)
    await state.set_state(RegisterStates.main_menu)

async def return_to_main_menu(message: types.Message, state: FSMContext):
    await message.reply("برگشتی به منوی اصلی!", reply_markup=main_menu)
    await state.clear()

async def course_register(message: types.Message, state: FSMContext):
    courses = await get_courses()  # اضافه کردن await
    if not courses:
        await message.reply("هیچ دوره‌ای موجود نیست!", reply_markup=register_menu)
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c["title"])] for c in courses] + [[KeyboardButton(text="🔙 بازگشت")]],
        resize_keyboard=True
    )
    await message.reply("دوره مورد نظرت رو انتخاب کن:", reply_markup=kb)
    await state.set_state(RegisterStates.waiting_for_course)

async def process_course(message: types.Message, state: FSMContext):
    if message.text == "🔙 بازگشت":
        await message.reply("برگشتی به منوی ثبت‌نام:", reply_markup=register_menu)
        await state.set_state(RegisterStates.main_menu)
        return
    courses = await get_courses()  # اضافه کردن await
    course = next((c for c in courses if c["title"] == message.text), None)
    if not course:
        await message.reply("این دوره وجود نداره! دوباره انتخاب کن:")
        return
    await state.update_data(selected_item=message.text, item_type="course", cost=course["cost"])
    await message.reply(
        f"هزینه دوره '{message.text}': {course['cost']} تومان\n"
        "شماره حساب: 1234-5678-9012-3456\n"
        "لطفاً مبلغ رو پرداخت کن و عکس فیش رو بفرست:",
        reply_markup=cancel_button
    )
    await state.set_state(RegisterStates.waiting_for_receipt)

async def visit_register(message: types.Message, state: FSMContext):
    visits = await get_visits()  # اضافه کردن await
    if not visits:
        await message.reply("هیچ بازدیدی موجود نیست!", reply_markup=register_menu)
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=v["title"])] for v in visits] + [[KeyboardButton(text="🔙 بازگشت")]],
        resize_keyboard=True
    )
    await message.reply("بازدید مورد نظرت رو انتخاب کن:", reply_markup=kb)
    await state.set_state(RegisterStates.waiting_for_visit)

async def process_visit(message: types.Message, state: FSMContext):
    if message.text == "🔙 بازگشت":
        await message.reply("برگشتی به منوی ثبت‌نام:", reply_markup=register_menu)
        await state.set_state(RegisterStates.main_menu)
        return
    visits = await get_visits()  # اضافه کردن await
    visit = next((v for v in visits if v["title"] == message.text), None)
    if not visit:
        await message.reply("این بازدید وجود نداره! دوباره انتخاب کن:")
        return
    await state.update_data(selected_item=message.text, item_type="visit", cost=visit["cost"])
    await message.reply(
        f"هزینه بازدید '{message.text}': {visit['cost']} تومان\n"
        "شماره حساب: 1234-5678-9012-3456\n"
        "لطفاً مبلغ رو پرداخت کن و عکس فیش رو بفرست:",
        reply_markup=cancel_button
    )
    await state.set_state(RegisterStates.waiting_for_receipt)

async def process_receipt(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("ثبت‌نام لغو شد.", reply_markup=main_menu)
        await state.clear()
        return
    if not message.photo:
        await message.reply("لطفاً عکس فیش پرداخت رو بفرست!", reply_markup=cancel_button)
        return
    data = await state.get_data()
    reg_id = await add_registration(str(message.from_user.id), data["item_type"], data["selected_item"], message.photo[-1].file_id)  # اضافه کردن await
    await message.reply("✅ فیشت ثبت شد! منتظر تأیید ادمین باش.", reply_markup=main_menu)
    bot = message.bot
    await bot.send_photo(
        ADMINS[0],  # فرض می‌کنیم اولین ادمین پیام رو دریافت کنه
        message.photo[-1].file_id,
        caption=f"درخواست ثبت‌نام\nکاربر: {message.from_user.id}\n{data['item_type']}: {data['selected_item']}\nID: {reg_id}"
    )
    await state.clear()

def register_handlers(dp: Dispatcher):
    dp.message.register(register_cmd, lambda message: message.text == "📝 ثبت‌نام دوره/بازدید")
    dp.message.register(process_name, RegisterStates.waiting_for_name)
    dp.message.register(process_field, RegisterStates.waiting_for_field)
    dp.message.register(process_student_id, RegisterStates.waiting_for_student_id)
    dp.message.register(process_phone, RegisterStates.waiting_for_phone)
    dp.message.register(process_email, RegisterStates.waiting_for_email)
    dp.message.register(course_register, lambda message: message.text == "📚 ثبت‌نام دوره", RegisterStates.main_menu)
    dp.message.register(visit_register, lambda message: message.text == "🏢 ثبت‌نام بازدید", RegisterStates.main_menu)
    dp.message.register(return_to_main_menu, lambda message: message.text == "🔙 بازگشت به منوی اصلی", RegisterStates.main_menu)
    dp.message.register(process_course, RegisterStates.waiting_for_course)
    dp.message.register(process_visit, RegisterStates.waiting_for_visit)
    dp.message.register(process_receipt, RegisterStates.waiting_for_receipt)
