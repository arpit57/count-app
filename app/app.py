# app/app.py

import logging
from beanie import init_beanie
from fastapi import Depends, FastAPI, Request, HTTPException, Body, Form, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from db import User, db
from schemas import UserCreate, UserRead, UserUpdate
from users import auth_backend, current_active_user, fastapi_users, auth_router
from typing import List, Dict
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from PIL import Image
import cv2
import base64
import uuid
from datetime import datetime, date, timedelta
import numpy as np
import os
from detect_circles import DetectCircle
from detect_circles_yolo import count_objects_with_yolo
from aws_config import AWSConfig
from utils.system_logger import log_request_stats as log_system_stats
import razorpay
from dotenv import load_dotenv

app = FastAPI()

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
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


async def save_base64_image(base64_str):
    try:
        image_data = base64.b64decode(base64_str)
    except base64.binascii.Error:
        logger.error("Invalid base64 format")
        raise ValueError(
            "Invalid base64 format. Please submit a valid base64-encoded image."
        )

    # Define the local path for saving the image
    original_image_path = f"../static/original_{uuid.uuid4()}.png"

    # Write the image data to a local file
    with open(original_image_path, "wb") as f:
        f.write(image_data)

    bucket_name = "alvision-count"
    object_name = f"count/original/original_{uuid.uuid4()}.png"

    # Use the existing upload_to_s3 method
    aws_config = AWSConfig()
    original_image_url = aws_config.upload_to_s3(
        original_image_path, bucket_name, object_name
    )

    logger.info(f"Original image saved to {original_image_url}")

    # Optionally, remove the local file if not needed
    os.remove(original_image_path)

    return original_image_url


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


async def get_current_admin_user(user: User = Depends(current_active_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Access forbidden: Requires admin role"
        )
    return user


@app.post("/count")
async def count(
    request: Request,
    count_request: CountRequest,
    admin: User = Depends(get_current_admin_user),
):
    original_image_url = await save_base64_image(count_request.base64_image)

    processed_img, count_text = count_objects_from_base64(
        circles, count_request.base64_image
    )
    # print(type(processed_img), type(count_text), count_text)
    processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
    processed_pil = Image.fromarray(processed_img)
    processed_image_path = f"../static/processed_{uuid.uuid4()}.png"
    processed_pil.save(processed_image_path)

    bucket_name = "alvision-count"  # Replace with your bucket name
    object_name = f"count/processed/processed_{uuid.uuid4()}.png"
    processed_image_url = aws_config.upload_to_s3(
        processed_image_path, bucket_name, object_name
    )

    current_utc_datetime = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    current_ist_datetime = current_utc_datetime + ist_offset
    ist_date = current_ist_datetime.date().isoformat()
    ist_time = current_ist_datetime.time().isoformat(timespec="seconds")

    count_info = {
        "ID": str(uuid.uuid4()),
        "Date": ist_date,
        "Time": ist_time,
        "Count": count_text,
        "Processed_Image_URL": processed_image_url,
        "Original_Image_URL": original_image_url,
    }

    # List to update counts for both admin and associated users
    users_to_update = [admin] + [
        await User.find_one(User.email == email) for email in admin.associated_users
    ]

    # Update the count_requests field for the admin only
    current_date = current_ist_datetime.date()
    count_request_entry = next(
        (
            entry
            for entry in admin.count_requests
            if entry["date"] == current_date.isoformat()
        ),
        None,
    )
    if count_request_entry:
        count_request_entry["count"] += 1
    else:
        admin.count_requests.append({"date": current_date.isoformat(), "count": 1})
    await admin.save()

    # Update counts for all users including admin
    for user in users_to_update:
        if user:
            user.counts.append(count_info)
            await user.save()
            logger.info(f"Count and processed image are saved for user {user.email}")

    os.remove(processed_image_path)

    return {"Count": count_text, "Processed_Image_URL": processed_image_url}


@app.post("/count-with-yolo")
async def count_with_yolo(
    request: Request,
    count_request: CountRequest,
    admin: User = Depends(get_current_admin_user),
):
    original_image_url = await save_base64_image(count_request.base64_image)

    processed_img, count_text = count_objects_with_yolo(count_request.base64_image)
    # print(type(processed_img), type(count_text), count_text)
    processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
    processed_pil = Image.fromarray(processed_img)
    processed_image_path = f"../static/processed_{uuid.uuid4()}.png"
    processed_pil.save(processed_image_path)

    bucket_name = "alvision-count"  # Replace with your bucket name
    object_name = f"count/processed/processed_{uuid.uuid4()}.png"
    processed_image_url = aws_config.upload_to_s3(
        processed_image_path, bucket_name, object_name
    )

    current_utc_datetime = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    current_ist_datetime = current_utc_datetime + ist_offset
    ist_date = current_ist_datetime.date().isoformat()
    ist_time = current_ist_datetime.time().isoformat(timespec="seconds")

    count_info = {
        "ID": str(uuid.uuid4()),
        "Date": ist_date,
        "Time": ist_time,
        "Count": count_text,
        "Processed_Image_URL": processed_image_url,
        "Original_Image_URL": original_image_url,
    }

    # List to update counts for both admin and associated users
    users_to_update = [admin] + [
        await User.find_one(User.email == email) for email in admin.associated_users
    ]

    # Update the count_requests field for the admin only
    current_date = current_ist_datetime.date()
    count_request_entry = next(
        (
            entry
            for entry in admin.count_requests
            if entry["date"] == current_date.isoformat()
        ),
        None,
    )
    if count_request_entry:
        count_request_entry["count"] += 1
    else:
        admin.count_requests.append({"date": current_date.isoformat(), "count": 1})
    await admin.save()

    # Update counts for all users including admin
    for user in users_to_update:
        if user:
            user.counts.append(count_info)
            await user.save()
            logger.info(f"Count and processed image are saved for user {user.email}")

    os.remove(processed_image_path)

    return {"Count": count_text, "Processed_Image_URL": processed_image_url}


@app.post("/associate-user")
async def associate_user(
    user_email: str = Body(..., embed=True),
    admin: User = Depends(get_current_admin_user),
):
    # Retrieve the user to be associated based on provided email
    target_user = await User.find_one(User.email == user_email)
    if not target_user:
        raise HTTPException(status_code=404, detail="User to be associated not found")

    # Check if the user email is already in the admin's associated_users list
    if user_email in admin.associated_users:
        raise HTTPException(
            status_code=400, detail="User already associated with this admin"
        )

    # Add the user's email to the admin's associated_users list
    admin.associated_users.append(user_email)
    await admin.save()

    # Copy the counts data from admin to user
    target_user.counts = admin.counts
    await target_user.save()

    return {"message": "User successfully associated and data copied"}


@app.patch("/manual-count")
async def update_count(
    increment: int, processed_image_url: str, user: User = Depends(current_active_user)
):
    if not user.counts:
        raise HTTPException(status_code=404, detail="No records found for this user.")

    # Retrieve the last count record
    last_record = user.counts[-1]

    # Extract the numeric part and the suffix from the last count
    parts = last_record["Count"].split(" ")
    if len(parts) < 2 or not parts[0].isdigit():
        raise HTTPException(status_code=400, detail="Current count format is invalid.")

    # Calculate the new count
    new_count = int(parts[0]) + increment
    updated_count = f"{new_count} {parts[1]}"  # Assuming the suffix is always the same and at index 1

    # Update the count in the last record
    last_record["Count"] = updated_count
    last_record["Processed_Image_URL"] = processed_image_url

    # Save the updated user document
    await user.update({"$set": {"counts": user.counts}})
    logger.info("Last record updated")

    return {"msg": "Count and processed image URL updated", "Last_Record": last_record}


@app.get("/user-counts", response_model=List[Dict])
async def get_user_counts(user: User = Depends(current_active_user)):
    # filtered_counts = [count for count in user.counts if 'ID' in count]
    logger.info("Retrieving user counts")
    return user.counts


@app.get("/user-counts/{date}", response_model=List[Dict])
async def get_user_counts_by_date(
    date: date, user: User = Depends(current_active_user)
):
    # filtered_counts = [count for count in user.counts if count["Date"] == date.isoformat() and 'ID' in count]
    filtered_counts = [
        count for count in user.counts if count["Date"] == date.isoformat()
    ]
    logger.info(f"Retrieving user counts for date: {date}")
    return filtered_counts


dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

rzp_api_key = os.getenv("RAZORPAY_API_KEY")
rzp_secret_key = os.getenv("RAZORPAY_SECRET_KEY")

razorpay_client = razorpay.Client(auth=(rzp_api_key, rzp_secret_key))


@app.get("/payment", response_class=HTMLResponse)
async def payment_page(
    request: Request,
    user: User = Depends(current_active_user),
    subscription_type: str = Query(..., regex="^(monthly|yearly)$"),
):
    if subscription_type not in ["monthly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid subscription type")
    try:
        order_data = {
            "amount": 100,  # Amount in paise
            "currency": "INR",
            "payment_capture": 1,
        }
        order = razorpay_client.order.create(data=order_data)
        # print(order)
        order_id = order["id"]
    except Exception as e:
        return HTMLResponse(
            content=f"Error in processing payment: {e}", status_code=500
        )

    # Render the payment.html template with the necessary context variables
    return templates.TemplateResponse(
        "payment.html",
        {
            "request": request,
            "email": user.email,
            "order_id": order_id,
            "subscription_type": subscription_type,
            "amount": 100 if subscription_type == "monthly" else 200,
            "razorpay_key": rzp_api_key,
        },
    )


@app.post("/payment/success")
async def payment_success(
    request: Request,
    email: str = Form(...),
    order_id: str = Form(...),
    subscription_type: str = Form(...),
):
    try:
        user = await User.find_one(User.email == email)
        IST_OFFSET = timedelta(hours=5, minutes=30)
        if user:
            if user.subscription_status == "active" and user.subscription_type:
                user.subscription_type.append(subscription_type)
            else:
                user.subscription_id = order_id
                user.subscription_status = "active"
                user.subscription_type = [subscription_type]
                user.subscription_start_date = datetime.utcnow() + IST_OFFSET

            await user.save()
            if subscription_type == "yearly":
                message = "you're now subscribed to alvision count yearly plan"
            else:
                message = "you're now subscribed to alvision count monthly plan"
            return JSONResponse(
                content={"message": message},
                status_code=200,
            )
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error processing payment success: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/subscription-check")
async def subscription_check(user: User = Depends(current_active_user)):
    start_date = user.subscription_start_date
    subscription_days = 0

    for period in user.subscription_type:
        if period == "yearly":
            subscription_days += 365
        elif period == "monthly":
            subscription_days += 30
        elif period == "trial":
            subscription_days += 7
        else:
            raise HTTPException(status_code=400, detail="Invalid subscription type")

    end_date = start_date + timedelta(days=subscription_days)

    if (end_date - datetime.now()).days < 0:
        user.subscription_status = "inactive"
        user.subscription_type = []
        await user.save()
        days_remaining = 0
    else:
        days_remaining = (end_date - datetime.now()).days

    return {
        "subscription_status": user.subscription_status,
        "subscription_type": user.subscription_type,
        "start_date": start_date,
        "end_date": end_date.strftime("%Y-%m-%d"),
        "days_remaining": days_remaining,
    }


@app.get("/no-of-requests")
async def get_no_of_requests(date: date):
    users = await User.find().to_list()
    total_count = sum(
        entry["count"]
        for user in users
        for entry in user.count_requests
        if entry.get("date") == date.isoformat()
    )
    return {"date": date.isoformat(), "total_count": total_count}


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    logger.info(f"Authenticated route accessed by {user.email}")
    return {"message": f"Hello {user.email}!"}


@app.get("/logs")
async def get_logs():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    logs_path = os.path.join(current_file_dir, "utils", "logs.txt")

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
