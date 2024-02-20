import boto3
from botocore.exceptions import NoCredentialsError
import uuid

def upload_to_s3(file_name, bucket_name, object_name=None):
    """
    Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket_name: Bucket to upload to
    :param object_name: S3 object name. If not specified, file_name is used
    :return: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket_name, object_name)
        # After upload, get the file's URL
        location = s3_client.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
        url = f"https://{bucket_name}.s3.{location}.amazonaws.com/{object_name}"
        return url
    except NoCredentialsError:
        print("Credentials not available")
        return None

# Your existing code to save the image locally
# processed_img, count_text = count_objects_from_base64(circles, count_request.base64_image)
# processed_pil = Image.fromarray(processed_img)
# local_image_path = f"../static/processed_{uuid.uuid4()}.png"
local_image_path = f"truck.jpg"

# processed_pil.save(local_image_path)

# New code to upload the image to S3 and get the URL
bucket_name = 'pi-processed-images'  # Replace with your new bucket name
object_name = f"processed_{uuid.uuid4()}.png"  # You can use the same name as local or a different one
s3_image_url = upload_to_s3(local_image_path, bucket_name, object_name)

# Now s3_image_url contains the URL to the image in S3
print(s3_image_url)
