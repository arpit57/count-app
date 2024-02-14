from beanie import init_beanie
from fastapi import Depends, FastAPI, HTTPException, status

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
from datetime import datetime

import numpy as np
from contextlib import asynccontextmanager

from utils.detect_circles1 import DetectCircle

import asyncio

app = FastAPI()

###################################################################################
# Mount the static directory for serving images
app.mount("/static", StaticFiles(directory="../static"), name="static")

# Jinja2 templates for HTML rendering
templates = Jinja2Templates(directory="../templates")

# Load the YOLOv5 model
# def load_yolo_model():
#     return torch.hub.load("ultralytics/yolov5", "custom", path="../model/yolov5n_rebar_kaggle.pt", device="0")

# Initialize YOLOv5 model
# yolo_model = load_yolo_model()
circles = DetectCircle()

# Default values for confidence threshold, IoU threshold, and image size
DEFAULT_CONFIDENCE_THRESHOLD = 0.25
DEFAULT_IOU_THRESHOLD = 0.1
DEFAULT_IMAGE_SIZE = 640


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

    # imge, ellips, _ = circles.process_image(im)

    return imge, f"{ellips} objects"

class CountRequest(BaseModel):
    base64_image: str
    conf: float = DEFAULT_CONFIDENCE_THRESHOLD
    iou: float = DEFAULT_IOU_THRESHOLD
    size: int = DEFAULT_IMAGE_SIZE

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

    # Store count information directly in the user's counts field
    count_info = {
        "count_text": count_text,
        "processed_image_path": processed_image_path,
        "timestamp": datetime.utcnow(),
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



# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup tasks
#     await init_beanie(
#         "mongodb://localhost:27017",
#         database=db,
#         document_models=User,
#     )
@app.on_event("startup")
async def on_startup():
    await init_beanie(
        database=db,
        document_models=[User]
    )