import logging
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    pass

# URL دیتابیس رو توی دیپلوی تنظیم می‌کنیم
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://botuser:yourpassword@cluster0.abcdef.mongodb.net/ieee_bot?retryWrites=true&w=majority")
DB_NAME = "ieee_bot"

# اتصال به MongoDB
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

async def setup_database():
    """تنظیم اولیه دیتابیس - MongoDB خودش کالکشن‌ها رو موقع استفاده می‌سازه"""
    try:
        # چک کردن اتصال
        await client.server_info()
        logger.info("Connected to MongoDB successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise DatabaseError("Cannot connect to MongoDB")

@asynccontextmanager
async def transaction():
    """تراکنش‌ها توی MongoDB به صورت دستی مدیریت می‌شن"""
    session = await client.start_session()
    try:
        async with session.start_transaction():
            yield db
            await session.commit_transaction()
    except Exception as e:
        await session.abort_transaction()
        logger.error(f"Transaction rolled back due to: {str(e)}")
        raise
    finally:
        await session.end_session()

async def get_user(user_id: str):
    user = await db.users.find_one({"user_id": user_id})
    return user

async def update_user(user_id: str, data: dict):
    data["user_id"] = user_id
    data["registered"] = 1
    await db.users.replace_one({"user_id": user_id}, data, upsert=True)
    logger.info(f"User updated: {user_id}")

async def get_events():
    events = await db.events.find().to_list(None)
    return events

async def add_event(title: str, date: str, description: str, photo: str = None):
    event = {"title": title, "date": date, "description": description, "photo": photo}
    await db.events.insert_one(event)
    logger.info(f"Event added: {title}")

async def get_courses():
    courses = await db.courses.find().to_list(None)
    return courses

async def add_course(*, title: str, cost: int, description: str, photo: str = None):
    if not title or len(title.strip()) < 3:
        raise DatabaseError("عنوان دوره باید حداقل ۳ کاراکتر باشد")
    if cost < 0:
        raise DatabaseError("هزینه نمی‌تواند منفی باشد")
    course = {"title": title, "cost": cost, "description": description, "photo": photo}
    await db.courses.insert_one(course)
    logger.info(f"Course added: {title}, cost={cost}, desc={description}")

async def get_visits():
    visits = await db.visits.find().to_list(None)
    return visits

async def add_visit(title: str, cost: int, description: str, photo: str = None):
    if not title or len(title.strip()) < 3:
        raise DatabaseError("عنوان بازدید باید حداقل ۳ کاراکتر باشد")
    if cost < 0:
        raise DatabaseError("هزینه نمی‌تواند منفی باشد")
    visit = {"title": title, "cost": cost, "description": description, "photo": photo}
    await db.visits.insert_one(visit)
    logger.info(f"Visit added: {title}, cost={cost}, desc={description}")

async def add_registration(user_id: str, reg_type: str, item_title: str, payment_photo: str) -> str:
    registration = {
        "user_id": user_id,
        "type": reg_type,
        "item_title": item_title,
        "payment_photo": payment_photo,
        "status": "pending"
    }
    result = await db.registrations.insert_one(registration)
    reg_id = str(result.inserted_id)
    logger.info(f"Registration added: {reg_id} for user {user_id}")
    return reg_id

async def get_registration(reg_id: str):
    from bson import ObjectId
    registration = await db.registrations.find_one({"_id": ObjectId(reg_id)})
    return registration

async def update_registration_status(reg_id: str, status: str):
    from bson import ObjectId
    await db.registrations.update_one({"_id": ObjectId(reg_id)}, {"$set": {"status": status}})
    logger.info(f"Registration {reg_id} status updated to {status}")

async def get_all_registrations():
    registrations = await db.registrations.aggregate([
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "user_id",
            "as": "user"
        }},
        {"$match": {"user.registered": 1}},
        {"$unwind": "$user"},
        {"$project": {
            "id": "$_id",
            "user_id": 1,
            "type": 1,
            "item_title": 1,
            "status": 1,
            "name": "$user.name"
        }}
    ]).to_list(None)
    return registrations

async def delete_course(title: str):
    await db.courses.delete_one({"title": title})
    await db.registrations.delete_many({"type": "course", "item_title": title})
    logger.info(f"Course {title} and related registrations deleted")

async def delete_visit(title: str):
    await db.visits.delete_one({"title": title})
    await db.registrations.delete_many({"type": "visit", "item_title": title})
    logger.info(f"Visit {title} and related registrations deleted")

async def get_all_registered_users():
    users = await db.users.find({"registered": 1}, {"user_id": 1}).to_list(None)
    return [user["user_id"] for user in users]

async def add_contact_message(user_id: str, message: str):
    contact = {"user_id": user_id, "message": message, "timestamp": datetime.datetime.utcnow()}
    await db.contacts.insert_one(contact)
    logger.info(f"Contact message added for user {user_id}")

async def get_all_contact_messages():
    messages = await db.contacts.aggregate([
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "user_id",
            "as": "user"
        }},
        {"$unwind": "$user"},
        {"$project": {
            "id": "$_id",
            "user_id": 1,
            "message": 1,
            "timestamp": 1,
            "name": "$user.name"
        }}
    ]).to_list(None)
    return messages

# اضافه کردن datetime برای timestamp
import datetime
