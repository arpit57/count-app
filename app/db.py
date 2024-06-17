from typing import List, Dict, Any, Optional
import logging
import motor.motor_asyncio
from beanie import Document
from fastapi_users.db import BaseOAuthAccount, BeanieBaseUser, BeanieUserDatabase
from pydantic import Field
from datetime import datetime

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "mongodb+srv://alvisionpi:k91f0hxBQ0DeX3OW@atlascluster.2jvy8lq.mongodb.net/alvisionpi?retryWrites=true"


def get_database_client():
    """Create and return a MongoDB client instance, handling any exceptions."""
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(
            DATABASE_URL, uuidRepresentation="standard"
        )
        logger.info("Connected to MongoDB")
        return client
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        return None  # Or raise an exception if you prefer to handle it higher up


client = get_database_client()
db = client["alvisionpi"] if client else None


class OAuthAccount(BaseOAuthAccount):
    pass


class User(BeanieBaseUser, Document):
    counts: List[Dict[str, Any]] = Field(default_factory=list)
    oauth_accounts: List[OAuthAccount] = Field(default_factory=list)
    role: str = Field(default="user")
    count_requests: List[Dict[str, Any]] = Field(default_factory=list)
    associated_users: List[str] = Field(default_factory=list)
    session_active: bool = Field(default=False)
    subscription_id: Optional[str] = Field(default=None)
    subscription_status: Optional[str] = Field(default=None)
    subscription_type: Optional[str] = Field(default=None)
    subscription_start_date: Optional[datetime] = Field(default=None)


async def get_user_db():
    logger.info("Retrieving user database")
    yield BeanieUserDatabase(User, OAuthAccount)


logger.info("Database connection initialized")
