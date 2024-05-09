#app/db.py

from typing import List, Dict, Any
import logging
import motor.motor_asyncio
from beanie import Document
from fastapi_users.db import BaseOAuthAccount, BeanieBaseUser, BeanieUserDatabase
from pydantic import Field

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "mongodb+srv://alvisionpi:k91f0hxBQ0DeX3OW@atlascluster.2jvy8lq.mongodb.net/alvisionpi?retryWrites=true"
client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL, uuidRepresentation="standard"
)
db = client["alvisionpi"]

class OAuthAccount(BaseOAuthAccount):
    pass

class User(BeanieBaseUser, Document):
    counts: List[Dict[str, Any]] = Field(default_factory=list)
    oauth_accounts: List[OAuthAccount] = Field(default_factory=list)
    role: str = Field(default="user")
    count_requests: List[Dict[str, Any]] = Field(default_factory=list)
    associated_users: List[str] = Field(default_factory=list)
    
async def get_user_db():
    logger.info("Retrieving user database")
    yield BeanieUserDatabase(User, OAuthAccount)

logger.info("Database connection initialized")

# You might want to handle potential exceptions that can occur during database connection
# For example, catching exceptions during the client connection setup
try:
    client = motor.motor_asyncio.AsyncIOMotorClient(
        DATABASE_URL, uuidRepresentation="standard"
    )
    db = client["alvisionpi"]
    logger.info("Connected to MongoDB")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")
