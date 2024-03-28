from beanie import PydanticObjectId
from fastapi_users import schemas
from typing import Optional

class UserRead(schemas.BaseUser[PydanticObjectId]):
    pass


class UserCreate(schemas.BaseUserCreate):
    role: Optional[str] = None
    admin_key: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    pass