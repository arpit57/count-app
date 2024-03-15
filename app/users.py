import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional
import logging

from beanie import PydanticObjectId
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import BeanieUserDatabase, ObjectIDIDMixin

from httpx_oauth.clients.google import GoogleOAuth2

from db import User, get_user_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET = "SECRET"

google_oauth_client = GoogleOAuth2(
    os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
)

class UserManager(ObjectIDIDMixin, BaseUserManager[User, PydanticObjectId]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.info(f"User {user.id} has registered.")

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        # Send email to the user with the reset password token
        await self.send_reset_password_email(user.email, token)
        logger.info(f"Reset password token sent to {user.email}")

        return JSONResponse(content={"token": token})

    async def send_reset_password_email(self, email: str, token: str):
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = "helpdesk@alluvium.in"
        smtp_password = "ooxi zbye qrvn smpj"  # Securely handle the SMTP password

        subject = "Reset Password Request"
        reset_password_url = f"http://127.0.0.1:8000/auth/reset-password?token={token}"

        body = f"Click the following link to reset your password: <a href='{reset_password_url}'>{reset_password_url}</a>"
        sender_email = "helpdesk@alluvium.in"
        recipient_email = email

        msg = MIMEText(body, 'html')
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
            logger.error(f"Failed to send password reset email to {recipient_email}: {e}")

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        logger.info(f"Verification requested for user {user.id}. Verification token: {token}")

async def get_user_manager(user_db: BeanieUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=60*60*24*30)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, PydanticObjectId](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
