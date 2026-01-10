from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

class Database:
    client: AsyncIOMotorClient = None
    
    def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        print(f"Connected to MongoDB at {settings.MONGO_URI}")
        
    def close(self):
        if self.client:
            self.client.close()
            print("Closed MongoDB connection")
            
    def get_db(self):
        if self.client is None:
            self.connect()
        return self.client[settings.DB_NAME]

db = Database()

def get_database():
    return db.get_db()
