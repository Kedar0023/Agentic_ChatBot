from functools import lru_cache

import boto3
from botocore.config import Config
from mypy_boto3_s3.client import S3Client

from app.core.app_configs import getAppConfig

R2_CONFIG = Config(
    signature_version="s3v4",  # Required authentication method for Cloudflare R2 (AWS Signature Version 4)
    connect_timeout=5,         # Wait up to 5 seconds to establish a connection
    read_timeout=60,           # Wait up to 60 seconds for data after the connection is established
    retries={
        "max_attempts": 5,     # Retry failed requests up to 5 times (helps with transient network issues)
        "mode": "standard",    # AWS recommended retry strategy with exponential backoff
    },
)


@lru_cache
def get_r2_client() -> S3Client:
    settings = getAppConfig()

    return boto3.client(
        service_name="s3",
        endpoint_url=f"https://{settings.cloudflare_account_id.get_secret_value()}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.cloudflare_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.cloudflare_secret_access_key.get_secret_value(),
        region_name="auto",
        config=R2_CONFIG,
    )