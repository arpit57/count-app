import boto3
import os
from botocore.exceptions import NoCredentialsError

class AWSConfig:
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION')
        )

    def upload_to_s3(self, file_name, bucket_name, object_name=None):
        """
        Upload a file to an S3 bucket directly using session client.

        :param file_name: File to upload
        :param bucket_name: Bucket to upload to
        :param object_name: S3 object name. If not specified, file_name is used
        :return: URL of the uploaded file if successful, else None
        """
        if object_name is None:
            object_name = file_name

        s3_client = self.session.client('s3')
        try:
            s3_client.upload_file(file_name, bucket_name, object_name)
            location = s3_client.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
            url = f"https://{bucket_name}.s3.{location}.amazonaws.com/{object_name}"
            return url
        except NoCredentialsError:
            print("Credentials not available")
            return None
