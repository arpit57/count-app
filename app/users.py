import os
from fastapi.responses import JSONResponse
import smtplib
from email.mime.text import MIMEText

from typing import Optional

from beanie import PydanticObjectId
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import BeanieUserDatabase, ObjectIDIDMixin
from httpx_oauth.clients.google import GoogleOAuth2

from db import User, get_user_db

SECRET = "SECRET"

google_oauth_client = GoogleOAuth2(
    os.getenv("GOOGLE_OAUTH_CLIENT_ID", "5875145151-uava2gmt1cmr7c6v2tginen6odlflv7a.apps.googleusercontent.com"),
    os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "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"),
)
from fastapi.responses import JSONResponse

class UserManager(ObjectIDIDMixin, BaseUserManager[User, PydanticObjectId]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    # async def on_after_forgot_password(
    #     self, user: User, token: str, request: Optional[Request] = None
    # ):
    #     print(f"User {user.id} has forgot their password. Reset token: {token} user email {user.email}")
        ####################################################################################

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        # Send email to the user with the reset password token
        await self.send_reset_password_email(user.email, token)

        print(user.email)
        
        # Return a JSONResponse with the reset password token
        return JSONResponse(content={"token": token})

    async def send_reset_password_email(self, email: str, token: str):
        # Correct SMTP server address for Gmail
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = "helpdesk@alluvium.in"
        smtp_password = "ooxi zbye qrvn smpj"  # Use the correct password or App Password for Gmail

        # Email content
        subject = "Reset Password Request"
        reset_password_url = f"http://127.0.0.1:8000/auth/reset-password?token={token}"

    # Create an HTML email body with a clickable hyperlink
        body = f"Click the following link to reset your password: <a href='{reset_password_url}'>{reset_password_url}</a>"

        sender_email = "helpdesk@alluvium.in"  # Use a valid email address accessible through the SMTP server
        recipient_email = email

        # Create MIMEText object
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        # Connect to SMTP server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())

        print(f"Password reset email sent to {recipient_email}.")




        #########################################################################################################
    
    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db: BeanieUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, PydanticObjectId](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
