from typing import List, Dict, Union, Any

import motor.motor_asyncio
from beanie import Document
from fastapi_users.db import BaseOAuthAccount, BeanieBaseUser, BeanieUserDatabase
from pydantic import Field

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


async def get_user_db():
    yield BeanieUserDatabase(User, OAuthAccount)
