import logging
from beanie import init_beanie
from fastapi import Depends, FastAPI, UploadFile, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from db import User, db
from schemas import UserCreate, UserRead, UserUpdate
from users import auth_backend, current_active_user, fastapi_users, google_oauth_client
from typing import List, Dict
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from PIL import Image
import cv2
import base64
import uuid
from datetime import datetime, date, timedelta
import asyncio
import numpy as np
import os
from detect_circles_nomask_segregation import DetectCircle
from aws_config import AWSConfig
from utils.system_logger import log_request_stats as log_system_stats

app = FastAPI()

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_request_stats(request: Request, call_next):
    logger.info(f"Request {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status code: {response.status_code}")

    # Call the imported function to log request stats using system_logger's functionality
    log_system_stats(request.method, str(request.url))
    
    return response

# Mount the static directory for serving images
app.mount("/static", StaticFiles(directory="../static"), name="static")

# Jinja2 templates for HTML rendering
templates = Jinja2Templates(directory="../templates")

circles = DetectCircle()
aws_config = AWSConfig()

async def save_base64_image(base64_str, image_path):
    try:
        image_data = base64.b64decode(base64_str)
    except base64.binascii.Error:
        logger.error("Invalid base64 format")
        raise ValueError("Invalid base64 format. Please submit a valid base64-encoded image.")
    
    with open(image_path, 'wb') as f:
        f.write(image_data)
    
    logger.info(f"Image saved to {image_path}")
    return image_path

def count_objects_from_base64(circles, base64_str):
    image_data = base64.b64decode(base64_str)
    image_np = np.frombuffer(image_data, dtype=np.uint8)
    im = cv2.imdecode(image_np, flags=cv2.IMREAD_COLOR)
    result = circles.process_image(im)
    
    if result is None:
        logger.error("Error processing image")
        return None, "Error processing image"
    
    imge, ellips, _ = result
    return imge, f"{ellips} objects"

class CountRequest(BaseModel):
    base64_image: str

@app.post("/count")
async def count(
    request: Request,
    count_request: CountRequest,
    user: User = Depends(current_active_user)
):
    processed_img, count_text = count_objects_from_base64(circles, count_request.base64_image)
    processed_pil = Image.fromarray(processed_img)
    processed_image_path = f"../static/processed_{uuid.uuid4()}.png"
    processed_pil.save(processed_image_path)

    bucket_name = 'pi-processed-images'  # Replace with your bucket name
    object_name = f"processed_{uuid.uuid4()}.png"
    s3_image_url = aws_config.upload_to_s3(processed_image_path, bucket_name, object_name)

    current_utc_datetime = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    current_ist_datetime = current_utc_datetime + ist_offset
    ist_date = current_ist_datetime.date().isoformat()
    ist_time = current_ist_datetime.time().isoformat(timespec='seconds')

    count_info = {
        "ID": str(uuid.uuid4()),
        "Date": ist_date,
        "Time": ist_time,
        "Count": count_text,
        "Processed_Image_URL": s3_image_url
    }
    user.counts.append(count_info)

    await user.update({"$set": {"counts": user.counts}})
    logger.info("Count and image processed and saved")
    
    return {"Count": count_text, "Processed_Image_URL": s3_image_url}

@app.get("/user-counts", response_model=List[Dict])
async def get_user_counts(user: User = Depends(current_active_user)):
    logger.info("Retrieving user counts")
    return user.counts

@app.get("/user-counts/{date}", response_model=List[Dict])
async def get_user_counts_by_date(date: date, user: User = Depends(current_active_user)):
    filtered_counts = [count for count in user.counts if count["Date"] == date.isoformat()]
    logger.info(f"Retrieving user counts for date: {date}")
    return filtered_counts

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])
app.include_router(fastapi_users.get_oauth_router(google_oauth_client, auth_backend, "SECRET", associate_by_email=True, is_verified_by_default=True), prefix="/auth/google", tags=["auth"])

@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    logger.info(f"Authenticated route accessed by {user.email}")
    return {"message": f"Hello {user.email}!"}

@app.get("/logs")
async def get_logs():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    logs_path = os.path.join(current_file_dir, 'utils', 'logs.txt')
    
    if not os.path.isfile(logs_path):
        logger.warning("Log file not found")
        return {"error": "Log file not found."}
    
    logger.info("Logs retrieved")
    return FileResponse(logs_path)

@app.on_event("startup")
async def on_startup():
    logger.info("Application startup")
    await init_beanie(database=db, document_models=[User])

@app.get("/")
async def health_check():
    logger.debug("Health check endpoint called")
    return {"status": "UP"}
