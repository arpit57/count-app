# app/users.py

import smtplib
from email.mime.text import MIMEText
from typing import Optional
import logging
from beanie import PydanticObjectId
from fastapi import Depends, Request, APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.db import BeanieUserDatabase, ObjectIDIDMixin
from db import User, get_user_db
from datetime import timedelta
from utils.token_handler import generate_jwt, decode_jwt
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET = "SECRET"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str


class UserManager(ObjectIDIDMixin, BaseUserManager[User, PydanticObjectId]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    def generate_verification_token(self, user: User):
        # Generates a JWT token for email verification
        data = {"user_id": str(user.id)}
        return generate_jwt(data, self.verification_token_secret, timedelta(hours=48))

    async def verify_token(self, token: str):
        # Verifies the token and if valid, activates the user
        claims = decode_jwt(token, self.verification_token_secret)
        if claims and "user_id" in claims:
            user_id = claims["user_id"]
            user = await self.get(user_id)
            if user and not user.is_verified:
                # Use Beanie's document update methods
                await user.set({"is_verified": True})
                return True
        return False

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        token = self.generate_verification_token(user)

        # Send email verification
        await self.send_verification_email(user.email, token)
        logger.info(f"Verification email sent to {user.email}.")

    async def send_verification_email(self, email: str, token: str):
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = "helpdesk@alluvium.in"
        smtp_password = "ooxi zbye qrvn smpj"
        subject = "Email Verification"
        verification_url = f"http://35.154.136.249:8000/auth/verify?token={token}"
        body = f"Please click the following link to verify your email: <a href='{verification_url}'>Verify</a>"
        sender_email = "helpdesk@alluvium.in"
        recipient_email = email

        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())
        logger.info(f"Verification email sent to {recipient_email}.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        # Send email to the user with the reset password token
        await self.send_reset_password_email(user.email, token)
        logger.info(f"Reset password token sent to {user.email}")
        return JSONResponse(content={"token": token})

    async def send_reset_password_email(self, email: str, token: str):
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = "helpdesk@alluvium.in"
        smtp_password = "ooxi zbye qrvn smpj"
        subject = "Reset Password Request"
        reset_password_url = f"http://alvision-reset-password.s3-website.ap-south-1.amazonaws.com/?token={token}"
        body = f"Click the following link to reset your password: <a href='{reset_password_url}'>Reset Password</a>"
        sender_email = "helpdesk@alluvium.in"
        recipient_email = email
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.sendmail(sender_email, [recipient_email], msg.as_string())
            logger.info(f"Password reset email sent to {recipient_email}.")
        except Exception as e:
            logger.error(
                f"Failed to send password reset email to {recipient_email}: {e}"
            )

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        logger.info(
            f"Verification requested for user {user.id}. Verification token: {token}"
        )


async def get_user_manager(user_db: BeanieUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)  # No sesison timeout


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, PydanticObjectId](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)

# Create a new router for the auth routes
auth_router = APIRouter()


@auth_router.post("/jwt/login", response_model=TokenResponse)
async def login(
    request: OAuth2PasswordRequestForm = Depends(),
    user_manager: UserManager = Depends(get_user_manager),
):
    user = await user_manager.authenticate(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )

    if user.session_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already logged in from another device",
        )

    jwt_strategy = auth_backend.get_strategy()
    access_token = await jwt_strategy.write_token(user)

    await user.set({"session_active": True})  # Set session_active to True

    return TokenResponse(
        access_token=str(access_token), token_type="bearer", role=user.role
    )


@auth_router.post("/jwt/logout")
async def logout(user: User = Depends(current_active_user)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    await user.set({"session_active": False})  # Set session_active to False
    return JSONResponse(content={"message": "Successfully logged out"})


@auth_router.get("/verify")
async def verify(token: str, user_manager: UserManager = Depends(get_user_manager)):
    # Logic to verify the token and activate the user
    result = await user_manager.verify_token(token)
    if result:
        return JSONResponse(content={"message": "Email verified successfully."})
    else:
        return JSONResponse(
            content={"error": "Invalid or expired token."}, status_code=400
        )
