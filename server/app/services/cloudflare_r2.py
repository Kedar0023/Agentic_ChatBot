from botocore.exceptions import ClientError

from app.core.cloudflare_r2_config import get_r2_client
from app.core.app_configs import getAppConfig
from app.core.logging import logger

settings = getAppConfig()
client = get_r2_client()

def upload_file(
    *,
    key: str,
    file_bytes: bytes,
    content_type: str,
) -> None:

    try:
        client.put_object(
            Bucket=settings.cloudflare_bucket_name.get_secret_value(),
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError("Failed to upload file to Cloudflare R2.") from e




def delete_file(*, key: str) -> None:
    try:
        client.delete_object(
            Bucket=settings.cloudflare_bucket_name.get_secret_value(),
            Key=key,
        )
    except ClientError:
        logger.exception("Failed to delete R2 object: %s", key)


def get_downloadable_file(*, key: str)-> bytes:
    try:
        return client.get_object(
            Bucket=settings.cloudflare_bucket_name.get_secret_value(),
            Key=key,
        )
    except ClientError as e:
        raise RuntimeError("Failed to retrieve file from Cloudflare R2.") from e
