from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from database.db import (add_event, add_course, add_visit, get_registration, 
                        update_registration_status, get_user, get_all_registrations, 
                        get_courses, get_visits, delete_course, delete_visit, 
                        get_all_registered_users, get_all_contact_messages)
import logging
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId
import pandas as pd
from io import BytesIO

load_dotenv()

logger = logging.getLogger(__name__)

class AdminStates(StatesGroup):
    admin_panel = State()
    waiting_for_course_title = State()
    waiting_for_course_cost = State()
    waiting_for_course_desc = State()
    waiting_for_course_photo = State()
    waiting_for_event_title = State()
    waiting_for_event_date = State()
    waiting_for_event_desc = State()
    waiting_for_event_photo = State()
    waiting_for_visit_title = State()
    waiting_for_visit_cost = State()
    waiting_for_visit_desc = State()
    waiting_for_visit_photo = State()
    waiting_for_reg_id = State()
    waiting_for_confirmation = State()
    waiting_for_item_selection = State()
    waiting_for_registrant_selection = State()
    waiting_for_item_to_delete = State()
    waiting_for_contact_selection = State()

# استفاده از لیست ADMINS به جای یک ADMIN_ID
ADMINS = [int(x) for x in os.getenv("ADMINS", "0").split(",") if x]

admin_menu = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="➕ رویداد جدید"), types.KeyboardButton(text="➕ دوره جدید")],
        [types.KeyboardButton(text="➕ بازدید جدید"), types.KeyboardButton(text="✅ تأیید ثبت‌نام")],
        [types.KeyboardButton(text="📋 لیست ثبت‌نام‌ها"), types.KeyboardButton(text="🗑️ حذف دوره/بازدید")],
        [types.KeyboardButton(text="📬 پیام‌های تماس")],
        [types.KeyboardButton(text="لغو")]
    ],
    resize_keyboard=True
)

cancel_kb = types.ReplyKeyboardMarkup(
    keyboard=[[types.KeyboardButton(text="لغو")]],
    resize_keyboard=True
)

async def admin_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    await message.reply("به پنل ادمین خوش اومدی!", reply_markup=admin_menu)
    await state.set_state(AdminStates.admin_panel)

# اضافه کردن دوره
async def start_add_course(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    logger.info("Add course triggered")
    await message.reply("عنوان دوره رو وارد کن:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_course_title)

async def process_course_title(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    title = message.text.strip()
    if len(title) < 3:
        await message.reply("عنوان دوره باید حداقل ۳ حرف باشد!")
        return
    await state.update_data(course_title=title)
    await message.reply("هزینه دوره رو وارد کن (به تومان، فقط عدد):", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_course_cost)

async def process_course_cost(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    try:
        cost = int(message.text.strip())
        if cost < 0:
            await message.reply("هزینه نمی‌تونه منفی باشه!")
            return
        await state.update_data(course_cost=cost)
        await message.reply("توضیحات دوره رو وارد کن:", reply_markup=cancel_kb)
        await state.set_state(AdminStates.waiting_for_course_desc)
    except ValueError:
        await message.reply("هزینه باید عدد باشه! دوباره وارد کن:")

async def process_course_desc(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    desc = message.text.strip()
    await state.update_data(course_desc=desc)
    await message.reply("عکس دوره رو بفرست (یا 'رد شدن' رو بزن اگه نمی‌خوای عکس بذاری):", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_course_photo)

async def process_course_photo(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    photo = None
    if message.text == "رد شدن":
        photo = None
    elif message.photo:
        photo = message.photo[-1].file_id
    else:
        await message.reply("لطفاً یه عکس بفرست یا 'رد شدن' رو بزن!")
        return
    data = await state.get_data()
    title = data["course_title"]
    cost = data["course_cost"]
    desc = data["course_desc"]
    try:
        await add_course(title=title, cost=cost, description=desc, photo=photo)
        await message.reply("✅ دوره با موفقیت اضافه شد!", reply_markup=admin_menu)
        users = await get_all_registered_users()
        caption = f"📚 دوره جدید: {title}\nهزینه: {cost} تومان\nتوضیحات: {desc}"
        for user_id in users:
            try:
                if photo:
                    await message.bot.send_photo(user_id, photo, caption=caption)
                else:
                    await message.bot.send_message(user_id, caption)
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {str(e)}")
        await state.set_state(AdminStates.admin_panel)
    except Exception as e:
        logger.error(f"Error adding course: {str(e)}")
        await message.reply("❌ یه مشکلی پیش اومد! دوباره امتحان کن.")
    finally:
        await state.clear()

# اضافه کردن رویداد
async def start_add_event(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    logger.info("Add event triggered")
    await message.reply("عنوان رویداد رو وارد کن:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_event_title)

async def process_event_title(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    title = message.text.strip()
    if len(title) < 3:
        await message.reply("عنوان رویداد باید حداقل ۳ حرف باشد!")
        return
    await state.update_data(event_title=title)
    await message.reply("تاریخ رویداد رو وارد کن (مثال: 1403-01-01):", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_event_date)

async def process_event_date(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    date = message.text.strip()
    await state.update_data(event_date=date)
    await message.reply("توضیحات رویداد رو وارد کن:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_event_desc)

async def process_event_desc(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    desc = message.text.strip()
    await state.update_data(event_desc=desc)
    await message.reply("عکس رویداد رو بفرست (یا 'رد شدن' رو بزن اگه نمی‌خوای عکس بذاری):", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_event_photo)

async def process_event_photo(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    photo = None
    if message.text == "رد شدن":
        photo = None
    elif message.photo:
        photo = message.photo[-1].file_id
    else:
        await message.reply("لطفاً یه عکس بفرست یا 'رد شدن' رو بزن!")
        return
    data = await state.get_data()
    title = data["event_title"]
    date = data["event_date"]
    desc = data["event_desc"]
    try:
        await add_event(title, date, desc, photo)
        await message.reply("✅ رویداد با موفقیت اضافه شد!", reply_markup=admin_menu)
        users = await get_all_registered_users()
        caption = f"🎉 رویداد جدید: {title}\nتاریخ: {date}\nتوضیحات: {desc}"
        for user_id in users:
            try:
                if photo:
                    await message.bot.send_photo(user_id, photo, caption=caption)
                else:
                    await message.bot.send_message(user_id, caption)
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {str(e)}")
        await state.set_state(AdminStates.admin_panel)
    except Exception as e:
        logger.error(f"Error adding event: {str(e)}")
        await message.reply("❌ یه مشکلی پیش اومد! دوباره امتحان کن.")
    finally:
        await state.clear()

# اضافه کردن بازدید
async def start_add_visit(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    logger.info("Add visit triggered")
    await message.reply("عنوان بازدید رو وارد کن:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_visit_title)

async def process_visit_title(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    title = message.text.strip()
    if len(title) < 3:
        await message.reply("عنوان بازدید باید حداقل ۳ حرف باشد!")
        return
    await state.update_data(visit_title=title)
    await message.reply("هزینه بازدید رو وارد کن (به تومان، فقط عدد):", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_visit_cost)

async def process_visit_cost(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    try:
        cost = int(message.text.strip())
        if cost < 0:
            await message.reply("هزینه نمی‌تونه منفی باشه!")
            return
        await state.update_data(visit_cost=cost)
        await message.reply("توضیحات بازدید رو وارد کن:", reply_markup=cancel_kb)
        await state.set_state(AdminStates.waiting_for_visit_desc)
    except ValueError:
        await message.reply("هزینه باید عدد باشه! دوباره وارد کن:")

async def process_visit_desc(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    desc = message.text.strip()
    await state.update_data(visit_desc=desc)
    await message.reply("عکس بازدید رو بفرست (یا 'رد شدن' رو بزن اگه نمی‌خوای عکس بذاری):", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_visit_photo)

async def process_visit_photo(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    photo = None
    if message.text == "رد شدن":
        photo = None
    elif message.photo:
        photo = message.photo[-1].file_id
    else:
        await message.reply("لطفاً یه عکس بفرست یا 'رد شدن' رو بزن!")
        return
    data = await state.get_data()
    title = data["visit_title"]
    cost = data["visit_cost"]
    desc = data["visit_desc"]
    try:
        await add_visit(title, cost, desc, photo)
        await message.reply("✅ بازدید با موفقیت اضافه شد!", reply_markup=admin_menu)
        users = await get_all_registered_users()
        caption = f"🏛 بازدید جدید: {title}\nهزینه: {cost} تومان\nتوضیحات: {desc}"
        for user_id in users:
            try:
                if photo:
                    await message.bot.send_photo(user_id, photo, caption=caption)
                else:
                    await message.bot.send_message(user_id, caption)
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {str(e)}")
        await state.set_state(AdminStates.admin_panel)
    except Exception as e:
        logger.error(f"Error adding visit: {str(e)}")
        await message.reply("❌ یه مشکلی پیش اومد! دوباره امتحان کن.")
    finally:
        await state.clear()

async def start_confirm_registration(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    await message.reply("لطفاً ID ثبت‌نام رو وارد کن:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_reg_id)

async def process_reg_id(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    
    reg_id = message.text.strip()
    logger.debug(f"Received reg_id: {reg_id}")
    
    # اعتبارسنجی reg_id
    try:
        # چک کردن اینکه reg_id یه ObjectId معتبره یا نه
        if len(reg_id) != 24 or not all(c in "0123456789abcdefABCDEF" for c in reg_id):
            await message.reply("ID ثبت‌نام باید یه رشته 24 کاراکتری هگزادسیمال باشه! دوباره وارد کن:", reply_markup=cancel_kb)
            return
        ObjectId(reg_id)  # تست تبدیل به ObjectId
        
        registration = await get_registration(reg_id)
        if not registration:
            await message.reply("این ID ثبت‌نام وجود نداره! دوباره وارد کن:", reply_markup=cancel_kb)
            return
        
        user_id = registration["user_id"]
        item_type = registration["type"]
        item_title = registration["item_title"]
        confirm_kb = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="✅ تأیید"), types.KeyboardButton(text="❌ رد")],
                [types.KeyboardButton(text="لغو")]
            ],
            resize_keyboard=True
        )
        user = await get_user(str(user_id))
        user_info = (
            f"اسم: {user['name']}\n"
            f"رشته: {user['field']}\n"
            f"شماره دانشجویی: {user['student_id']}\n"
            f"تلفن: {user['phone']}\n"
            f"ایمیل: {user['email']}"
        ) if user else "اطلاعات کاربر پیدا نشد!"
        await message.reply(
            f"ثبت‌نام:\nکاربر: {user_id}\n{user_info}\nنوع: {item_type}\nعنوان: {item_title}\nوضعیت: {registration['status']}\n"
            "انتخاب کن:",
            reply_markup=confirm_kb
        )
        await state.update_data(reg_id=reg_id)
        await state.set_state(AdminStates.waiting_for_confirmation)
    except ValueError as e:
        logger.error(f"Invalid reg_id format: {reg_id}, error: {str(e)}")
        await message.reply("ID ثبت‌نام نامعتبره! باید یه رشته 24 کاراکتری هگزادسیمال باشه (مثل 507f1f77bcf86cd799439011):", reply_markup=cancel_kb)
    except Exception as e:
        logger.error(f"Error processing reg_id {reg_id}: {str(e)}")
        await message.reply("خطایی پیش اومد! دوباره امتحان کن:", reply_markup=cancel_kb)

async def process_reg_confirmation(message: types.Message, state: FSMContext):
    if message.text == "لغو":
        await message.reply("عملیات لغو شد.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    data = await state.get_data()
    reg_id = data["reg_id"]
    registration = await get_registration(reg_id)
    user_id = registration["user_id"]
    try:
        if message.text == "✅ تأیید":
            await update_registration_status(reg_id, "confirmed")
            await message.reply("✅ ثبت‌نام تأیید شد!", reply_markup=admin_menu)
            await message.bot.send_message(user_id, "✅ ثبت‌نامت تأیید شد! خوش اومدی.")
        elif message.text == "❌ رد":
            await update_registration_status(reg_id, "rejected")
            await message.reply("❌ ثبت‌نام رد شد!", reply_markup=admin_menu)
            await message.bot.send_message(user_id, "❌ ثبت‌نامت رد شد. لطفاً با ادمین تماس بگیر.")
        else:
            await message.reply("لطفاً یکی از گزینه‌ها رو انتخاب کن!")
            return
        await state.set_state(AdminStates.admin_panel)
    except Exception as e:
        logger.error(f"Error updating registration: {str(e)}")
        await message.reply("❌ یه مشکلی پیش اومد! دوباره امتحان کن.")
    finally:
        await state.clear()

async def show_items_list(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    courses = await get_courses()
    visits = await get_visits()
    if not courses and not visits:
        await message.reply("هیچ دوره یا بازدیدی وجود نداره!", reply_markup=admin_menu)
        return
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=f"دوره: {c['title']}")] for c in courses] +
                 [[types.KeyboardButton(text=f"بازدید: {v['title']}")] for v in visits] +
                 [[types.KeyboardButton(text="🔙 بازگشت")]],
        resize_keyboard=True
    )
    await message.reply("دوره‌ها و بازدیدها:\nانتخاب کن تا ثبت‌نام‌کننده‌ها رو ببینی:", reply_markup=kb)
    await state.set_state(AdminStates.waiting_for_item_selection)

async def download_registrations_excel(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    data = await state.get_data()
    item_type = data["item_type"]
    item_title = data["item_title"]
    try:
        registrations = await get_all_registrations()
        registrants = [r for r in registrations if r["type"] == item_type and r["item_title"] == item_title and r["status"] == "confirmed"]
        if not registrants:
            await message.reply(f"هیچ ثبت‌نام تأییدشده‌ای برای '{item_title}' وجود نداره!", reply_markup=admin_menu)
            await state.set_state(AdminStates.admin_panel)
            return

        # آماده‌سازی داده‌ها برای اکسل
        data = []
        for reg in registrants:
            user = await get_user(str(reg["user_id"]))
            data.append({
                "نام": user.get("name", "نامشخص") if user else "نامشخص",
                "رشته": user.get("field", "نامشخص") if user else "نامشخص",
                "شماره دانشجویی": user.get("student_id", "نامشخص") if user else "نامشخص",
                "تلفن": user.get("phone", "نامشخص") if user else "نامشخص",
                "ایمیل": user.get("email", "نامشخص") if user else "نامشخص",
                "نوع": reg.get("type", "نامشخص"),
                "عنوان": reg.get("item_title", "نامشخص"),
                "وضعیت": reg.get("status", "نامشخص"),
                "شناسه ثبت‌نام": str(reg.get("_id", "نامشخص"))
            })

        # ایجاد DataFrame با pandas
        df = pd.DataFrame(data)

        # ذخیره فایل اکسل در حافظه
        output = BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)

        # ارسال فایل به کاربر
        safe_title = item_title.replace(" ", "_").replace("/", "_")  # جایگزینی کاراکترهای نامعتبر
        filename = f"{safe_title}_registrations.xlsx"
        await message.reply_document(
            types.BufferedInputFile(output.getvalue(), filename=filename),
            caption=f"📊 فایل اکسل ثبت‌نام‌های '{item_title}'",
            reply_markup=admin_menu
        )
        await state.set_state(AdminStates.admin_panel)
    except Exception as e:
        logger.error(f"Error generating Excel file: {str(e)}")
        await message.reply("❌ خطایی در تولید فایل اکسل رخ داد! دوباره امتحان کن.", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)

async def show_registrants(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    if message.text == "🔙 بازگشت":
        await message.reply("برگشتی به منوی ادمین!", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    item_type, item_title = message.text.split(": ", 1)
    item_type = "course" if item_type == "دوره" else "visit"
    registrations = await get_all_registrations()
    registrants = [r for r in registrations if r["type"] == item_type and r["item_title"] == item_title and r["status"] == "confirmed"]
    if not registrants:
        await message.reply(f"هیچ ثبت‌نام تأییدشده‌ای توی '{item_title}' وجود نداره!", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📊 دانلود اکسل ثبت‌نام‌ها")]] +
                 [[types.KeyboardButton(text=r["name"])] for r in registrants] + 
                 [[types.KeyboardButton(text="🔙 بازگشت")]],
        resize_keyboard=True
    )
    await state.update_data(item_type=item_type, item_title=item_title)
    await message.reply(f"ثبت‌نام‌کننده‌های تأییدشده‌ی '{item_title}':\nانتخاب کن تا مشخصاتش رو ببینی یا فایل اکسل رو دانلود کن:", reply_markup=kb)
    await state.set_state(AdminStates.waiting_for_registrant_selection)

async def show_registrant_details(message: types.Message, state: FSMContext):
    if message.text == "🔙 بازگشت":
        await show_items_list(message, state)
        return
    if message.text == "📊 دانلود اکسل ثبت‌نام‌ها":
        await download_registrations_excel(message, state)
        return
    data = await state.get_data()
    item_type = data["item_type"]
    item_title = data["item_title"]
    registrations = await get_all_registrations()
    registrant = next((r for r in registrations if r["name"] == message.text and r["type"] == item_type and r["item_title"] == item_title), None)
    if not registrant:
        await message.reply("این فرد پیدا نشد! دوباره انتخاب کن:")
        return
    user = await get_user(registrant["user_id"])
    response = (
        f"📋 مشخصات ثبت‌نام:\n"
        f"اسم: {user['name']}\n"
        f"رشته: {user['field']}\n"
        f"شماره دانشجویی: {user['student_id']}\n"
        f"تلفن: {user['phone']}\n"
        f"ایمیل: {user['email']}\n"
        f"نوع: {registrant['type']}\n"
        f"عنوان: {registrant['item_title']}\n"
        f"وضعیت: {registrant['status']}"
    )
    await message.reply(response, reply_markup=admin_menu)
    await state.set_state(AdminStates.admin_panel)

async def start_delete_item(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    courses = await get_courses()
    visits = await get_visits()
    if not courses and not visits:
        await message.reply("هیچ دوره یا بازدیدی برای حذف وجود نداره!", reply_markup=admin_menu)
        return
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=f"دوره: {c['title']}")] for c in courses] +
                 [[types.KeyboardButton(text=f"بازدید: {v['title']}")] for v in visits] +
                 [[types.KeyboardButton(text="🔙 بازگشت")]],
        resize_keyboard=True
    )
    await message.reply("دوره یا بازدیدی که می‌خوای حذف کنی رو انتخاب کن:", reply_markup=kb)
    await state.set_state(AdminStates.waiting_for_item_to_delete)

async def process_item_deletion(message: types.Message, state: FSMContext):
    if message.text == "🔙 بازگشت":
        await message.reply("برگشتی به منوی ادمین!", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    item_type, item_title = message.text.split(": ", 1)
    try:
        if item_type == "دوره":
            await delete_course(item_title)
            await message.reply(f"✅ دوره '{item_title}' با موفقیت حذف شد!", reply_markup=admin_menu)
        elif item_type == "بازدید":
            await delete_visit(item_title)
            await message.reply(f"✅ بازدید '{item_title}' با موفقیت حذف شد!", reply_markup=admin_menu)
        else:
            await message.reply("گزینه نامعتبر! دوباره انتخاب کن:")
            return
        await state.set_state(AdminStates.admin_panel)
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        await message.reply("❌ یه مشکلی پیش اومد! دوباره امتحان کن.")
    finally:
        await state.clear()

async def show_contact_messages(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ دسترسی نداری!")
        return
    contacts = await get_all_contact_messages()
    if not contacts:
        await message.reply("هیچ پیامی از کاربران وجود نداره!", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=f"{c['name']} - {c['timestamp']}")] for c in contacts] +
                 [[types.KeyboardButton(text="🔙 بازگشت")]],
        resize_keyboard=True
    )
    await message.reply("پیام‌های تماس:\nانتخاب کن تا جزئیات رو ببینی:", reply_markup=kb)
    await state.set_state(AdminStates.waiting_for_contact_selection)

async def show_contact_details(message: types.Message, state: FSMContext):
    if message.text == "🔙 بازگشت":
        await message.reply("برگشتی به منوی ادمین!", reply_markup=admin_menu)
        await state.set_state(AdminStates.admin_panel)
        return
    contacts = await get_all_contact_messages()
    selected = next((c for c in contacts if f"{c['name']} - {c['timestamp']}" == message.text), None)
    if not selected:
        await message.reply("این پیام پیدا نشد! دوباره انتخاب کن:")
        return
    user = await get_user(selected["user_id"])
    response = (
        f"📬 جزئیات پیام:\n"
        f"اسم: {selected['name']}\n"
        f"آی‌دی کاربر: {selected['user_id']}\n"
        f"پیام: {selected['message']}\n"
        f"زمان: {selected['timestamp']}\n"
        f"ایمیل: {user['email'] if user else 'نامشخص'}"
    )
    await message.reply(response, reply_markup=admin_menu)
    await state.set_state(AdminStates.admin_panel)

def register_handlers(dp: Dispatcher):
    dp.message.register(admin_cmd, Command(commands=["admin"]))
    dp.message.register(start_add_course, lambda message: message.text == "➕ دوره جدید", AdminStates.admin_panel)
    dp.message.register(process_course_title, AdminStates.waiting_for_course_title)
    dp.message.register(process_course_cost, AdminStates.waiting_for_course_cost)
    dp.message.register(process_course_desc, AdminStates.waiting_for_course_desc)
    dp.message.register(process_course_photo, AdminStates.waiting_for_course_photo)
    dp.message.register(start_add_event, lambda message: message.text == "➕ رویداد جدید", AdminStates.admin_panel)
    dp.message.register(process_event_title, AdminStates.waiting_for_event_title)
    dp.message.register(process_event_date, AdminStates.waiting_for_event_date)
    dp.message.register(process_event_desc, AdminStates.waiting_for_event_desc)
    dp.message.register(process_event_photo, AdminStates.waiting_for_event_photo)
    dp.message.register(start_add_visit, lambda message: message.text == "➕ بازدید جدید", AdminStates.admin_panel)
    dp.message.register(process_visit_title, AdminStates.waiting_for_visit_title)
    dp.message.register(process_visit_cost, AdminStates.waiting_for_visit_cost)
    dp.message.register(process_visit_desc, AdminStates.waiting_for_visit_desc)
    dp.message.register(process_visit_photo, AdminStates.waiting_for_visit_photo)
    dp.message.register(start_confirm_registration, lambda message: message.text == "✅ تأیید ثبت‌نام", AdminStates.admin_panel)
    dp.message.register(process_reg_id, AdminStates.waiting_for_reg_id)
    dp.message.register(process_reg_confirmation, AdminStates.waiting_for_confirmation)
    dp.message.register(show_items_list, lambda message: message.text == "📋 لیست ثبت‌نام‌ها", AdminStates.admin_panel)
    dp.message.register(show_registrants, AdminStates.waiting_for_item_selection)
    dp.message.register(show_registrant_details, AdminStates.waiting_for_registrant_selection)
    dp.message.register(start_delete_item, lambda message: message.text == "🗑️ حذف دوره/بازدید", AdminStates.admin_panel)
    dp.message.register(process_item_deletion, AdminStates.waiting_for_item_to_delete)
    dp.message.register(show_contact_messages, lambda message: message.text == "📬 پیام‌های تماس", AdminStates.admin_panel)
    dp.message.register(show_contact_details, AdminStates.waiting_for_contact_selection)
