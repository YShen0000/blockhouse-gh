from .settings import settings
from motor.motor_asyncio import AsyncIOMotorClient

# Create the MongoDB client
client = AsyncIOMotorClient(settings.MONGODB_URL)

# Get the database
db = client[settings.MONGODB_DB_NAME]
