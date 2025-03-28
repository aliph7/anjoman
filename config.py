from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")  # توکن بات رو توی فایل .env بذار
CARD_NUMBER = "1234-5678-9012-3456"  # شماره کارت برای پرداخت
ADMIN_IDS = [123456789, 987654321]  # آیدی عددی ادمین‌ها