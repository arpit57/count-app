# app/schemas.py

from beanie import PydanticObjectId
from fastapi_users import schemas
from typing import Optional
from pydantic import validator, Field


class UserRead(schemas.BaseUser[PydanticObjectId]):
    pass


class UserCreate(schemas.BaseUserCreate):
    role: Optional[str] = Field(default="user", example="user")

    @validator("password")
    def validate_password_complexity(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char in "!@#$%^&*()" for char in value):
            raise ValueError(
                "Password must contain at least one special character (!@#$%^&*())"
            )
        return value


class UserUpdate(schemas.BaseUserUpdate):
    pass
