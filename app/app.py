from beanie import init_beanie
from fastapi import Depends, FastAPI, HTTPException, status

from fastapi.middleware.cors import CORSMiddleware
from db import User, db
from schemas import UserCreate, UserRead, UserUpdate
from users import auth_backend, current_active_user, fastapi_users,google_oauth_client
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse,  JSONResponse

from typing import List, Dict
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from pydantic import BaseModel


from fastapi.templating import Jinja2Templates
import torch
from PIL import Image
from io import BytesIO
import cv2
import base64
import uuid
from datetime import datetime, date

import numpy as np
from contextlib import asynccontextmanager

from detect_circles_nomask import DetectCircle

from aws_config import AWSConfig

app = FastAPI()

# Define CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

###################################################################################
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
        raise ValueError("Invalid base64 format. Please submit a valid base64-encoded image.")

    with open(image_path, 'wb') as f:
        f.write(image_data)

    return image_path

def count_objects_from_base64(circles, base64_str):
    # Decode base64 to obtain image bytes
    image_data = base64.b64decode(base64_str)
    image_np = np.frombuffer(image_data, dtype=np.uint8)
    im = cv2.imdecode(image_np, flags=cv2.IMREAD_COLOR)

    result = circles.process_image(im)
    if result is None:
        # Handle the error appropriately
        return None, "Error processing image"
    imge, ellips, _ = result

    return imge, f"{ellips} objects"

class CountRequest(BaseModel):
    base64_image: str


# Update the /count route
@app.post("/count")
async def count(
    request: Request,
    count_request: CountRequest,
    user: User = Depends(current_active_user)
):
    try:
        image_path = await save_base64_image(count_request.base64_image, f"../static/{uuid.uuid4()}.png")
    except ValueError as e:
        return {"error": str(e)}

    processed_img, count_text = count_objects_from_base64(circles, count_request.base64_image)
    processed_pil = Image.fromarray(processed_img)

    processed_image_path = f"../static/processed_{uuid.uuid4()}.png"
    processed_pil.save(processed_image_path)

    bucket_name = 'pi-processed-images'  # Replace with your new bucket name
    object_name = f"processed_{uuid.uuid4()}.png"  # You can use the same name as local or a different one
    # s3_image_url = upload_to_s3(processed_image_path, bucket_name, object_name)
    s3_image_url = aws_config.upload_to_s3(processed_image_path, bucket_name, object_name)

    current_utc_datetime = datetime.utcnow()

    # Split the datetime into date and time components
    utc_date = current_utc_datetime.date().isoformat()  # Format the date as a string in 'YYYY-MM-DD' format
    utc_time = current_utc_datetime.time().isoformat(timespec='seconds')  # Format the time as a string in 'HH:MM:SS' format

    # Update the count_info dictionary with the new structure
    count_info = {
        "ID": str(uuid.uuid4()),
        "Date": utc_date,
        "Time": utc_time,
        "Count": count_text,  # Assuming count_text is a variable holding the count as a string
        "Processed_Image_URL": s3_image_url,  # Assuming processed_image_path is the path to the processed image
    }
    user.counts.append(count_info)

    # Save the updated user model to the database
    await user.update(
        {
            "$set": {
                "counts": user.counts
            }
        }
    )

    return count_text
    # return {"type": str(ty)}

# Function to save the uploaded file
def save_uploaded_file(file: UploadFile, destination: str):
    with open(destination, "wb+") as buffer:
        buffer.write(file.file.read())


@app.get("/user-counts", response_model=List[Dict])
async def get_user_counts(user: User = Depends(current_active_user)):
    """
    Retrieve count data for the currently logged-in user.
    """
    return user.counts

@app.get("/user-counts/{date}", response_model=List[Dict])
async def get_user_counts_by_date(date: date, user: User = Depends(current_active_user)):
    """
    Retrieve count data for the currently logged-in user for a specific date.
    """
    # Filter the counts for the given date
    filtered_counts = [count for count in user.counts if count["Date"] == date.isoformat()]
    return filtered_counts


###################################################################################

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate),prefix="/auth",tags=["auth"],)
app.include_router(fastapi_users.get_reset_password_router(),prefix="/auth",tags=["auth"],)
app.include_router(fastapi_users.get_verify_router(UserRead),prefix="/auth",tags=["auth"],)
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate),prefix="/users",tags=["users"],)
app.include_router(fastapi_users.get_oauth_router(google_oauth_client, auth_backend, "SECRET",associate_by_email=True,is_verified_by_default=True),prefix="/auth/google",tags=["auth"],)


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}


@app.on_event("startup")
async def on_startup():
    await init_beanie(
        database=db,
        document_models=[User]
    )

@app.get("/")
async def health_check():
    return {"status": "UP2"}