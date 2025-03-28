from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter  # برای کار با state
from config import ADMIN_IDS
from main import bot

router = Router()

# تعریف FSM
class Contact(StatesGroup):
    waiting_for_message = State()

# تابع ثبت هندلرها
async def register_contact_handlers(dp):
    @dp.message(lambda msg: msg.text == "ارتباط با ادمین")
    async def contact_handler(message: types.Message):
        await message.reply("لطفاً پیام خود را ارسال کنید:")
        await Contact.waiting_for_message.set()

    @router.message(StateFilter(Contact.waiting_for_message))
    async def process_contact_message(message: types.Message, state: FSMContext):
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f"پیام جدید:\nاز: {message.from_user.id}\nمتن: {message.text}\nبرای مشاهده: /inbox")
        await message.reply("پیام شما ارسال شد!")
        await state.finish()