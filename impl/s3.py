import boto3
from botocore.exceptions import NoCredentialsError

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
        print("Credentials not available")

def upload_file(file_path, bucket_name, object_key):
    """
    Upload a file to an S3 bucket.

    Parameters:
        - file_path (str): The local path of the file to upload.
        - bucket_name (str): The name of the S3 bucket.
        - object_key (str): The key (path) to the object in the bucket.

    Returns:
        - None
    """
    s3 = boto3.client('s3')

    try:
        s3.upload_file(file_path, bucket_name, object_key)
        print(f"File uploaded successfully to {bucket_name}/{object_key}")

        url = generate_presigned_url(bucket_name, object_key)
        print(f"Pre-signed URL for {object_key} : {url}")

    except FileNotFoundError:
        print(f"The file {file_path} was not found.")

    except Exception as e:
        print(f"An error occurred: {e}")