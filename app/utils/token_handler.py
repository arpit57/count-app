import jwt
from datetime import datetime
import logging as logger

def generate_jwt(data, secret, duration):
    expire = datetime.utcnow() + duration
    data.update({"exp": expire})
    token = jwt.encode(data, secret, algorithm="HS256")
    return token

def decode_jwt(token, secret):
    try:
        # Decode the token
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        # Handle expired token
        logger.error("The verification token has expired.")
        return None
    except jwt.InvalidTokenError:
        # Handle invalid token
        logger.error("Invalid token.")
        return None
