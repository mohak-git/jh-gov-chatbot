from pymongo import AsyncMongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure

from .config import settings
from .logging import setup_logging

logger = setup_logging(__name__)


class Database:
    client: AsyncMongoClient = None

    async def connect(self):
        if self.client is None:
            try:
                self.client = AsyncMongoClient(
                    settings.MONGO_URI, serverSelectionTimeoutMS=5000
                )
                await self.client.admin.command("ping")
                logger.info("Successfully connected to MongoDB")
            except (ConnectionFailure, ConfigurationError) as e:
                logger.error(f"Could not connect to MongoDB: {e}")
                self.client = None
                raise e

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Closed MongoDB connection")

    def get_db(self):
        if self.client is None:
            raise RuntimeError(
                "Database not connected. Call 'await db.connect()' first."
            )
        return self.client[settings.DB_NAME]


db = Database()


def get_database():
    return db.get_db()
