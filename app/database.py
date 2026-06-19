from databases import Database
from app.config import settings

db = Database(settings.database_url)

async def connect():
    await db.connect()

async def disconnect():
    await db.disconnect()
