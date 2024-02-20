import boto3
from botocore.exceptions import NoCredentialsError
import logging

_log = logging.getLogger()

def generate_presigned_url(bucket_name, object_key, expiration_time=3600):
    """
    Generate a pre-signed URL for accessing an S3 object.

    Parameters:
        - bucket_name (str): The name of the S3 bucket.
        - object_key (str): The key (path) of the S3 object.
        - expiration_time (int): The expiration time of the URL in seconds. Default is 1 hour.

    Returns:
        - str: The pre-signed URL.
    """
    s3 = boto3.client('s3')

    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration_time
        )

        return url

    except NoCredentialsError:
        _log.error("S3 generate_presigned_url error: Credentials not available")

def upload_file(local_file_path, bucket_name, s3_object_key):
    """
    Upload a file to an S3 bucket.

    Parameters:
        - local_file_path (str): The local path of the file to upload.
        - bucket_name (str): The name of the S3 bucket.
        - s3_object_key (str): The key (path) to the object in the bucket.

    Returns:
        - None
    """
    s3 = boto3.client('s3')

    try:
        s3.upload_file(local_file_path, bucket_name, s3_object_key)
        _log.info(f"S3: File uploaded successfully to s3://{bucket_name}/{s3_object_key}")

    except FileNotFoundError:
        _log.error(f"S3 file upload error: The file {local_file_path} was not found.")

    except Exception as e:
        _log.error(f"S3 file upload error: An error occurred: {e}")