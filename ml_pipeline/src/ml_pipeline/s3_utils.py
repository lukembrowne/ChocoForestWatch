"""
ml_pipeline.s3_utils
~~~~~~~~~~~~~~~~~~~
Utility functions for interacting with S3-compatible storage (DigitalOcean Spaces).

Requires
--------
pip install boto3 python-dotenv
"""

from __future__ import annotations
from pathlib import Path
import os
import boto3
from dotenv import load_dotenv
from typing import Optional

def get_s3_client(bucket: str = "choco-forest-watch") -> tuple[boto3.client, str]:
    """
    Get an S3 client configured for DigitalOcean Spaces.
    
    Parameters
    ----------
    bucket : str, optional
        The bucket name to use, by default "choco-forest-watch"
        
    Returns
    -------
    tuple[boto3.client, str]
        A tuple containing the S3 client and bucket name
    """
    load_dotenv()
    s3 = boto3.session.Session().client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        endpoint_url="https://" + os.getenv("AWS_S3_ENDPOINT"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    return s3, bucket

def upload_file(
    local_path: Path,
    remote_key: str,
    content_type: str = "image/tiff",
    bucket: Optional[str] = None
) -> None:
    """
    Upload a file to DigitalOcean Spaces.
    
    Parameters
    ----------
    local_path : Path
        Path to the local file to upload
    remote_key : str
        The key (path) where the file should be stored in the bucket
    content_type : str, optional
        The content type of the file, by default "image/tiff"
    bucket : str, optional
        The bucket to upload to. If None, uses the default bucket.
    """
    s3, default_bucket = get_s3_client()
    bucket = bucket or default_bucket
    
    print(f"⤴️  Uploading {local_path.name} → {remote_key}")
    s3.upload_file(
        Filename=str(local_path),
        Bucket=bucket,
        Key=remote_key,
        ExtraArgs={"ContentType": content_type},
    )
    print(f"✓ Uploaded {local_path.name} to {remote_key}")
    
def list_files(prefix: str, bucket: Optional[str] = None) -> list[dict]:
    """
    List files in a bucket under a given prefix.
    
    Parameters
    ----------
    prefix : str
        The prefix to list files under
    bucket : str, optional
        The bucket to list from. If None, uses the default bucket.
        
    Returns
    -------
    list[dict]
        List of dictionaries containing file information with 'key' and 'url' fields
    """
    s3, default_bucket = get_s3_client()
    bucket = bucket or default_bucket
    
    print(f"Listing files under {prefix}")
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    return [
        {"key": o["Key"], "url": f"s3://{bucket}/{o['Key']}"}
        for o in resp.get("Contents", [])
        if o["Key"].lower().endswith((".tif", ".tiff"))
    ] 