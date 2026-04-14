import os
import boto3
from app.config import settings


class StorageService:
    def __init__(self):
        self.backend = settings.storage_backend

        if self.backend == "s3":
            self._s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url or None,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            )
            self._bucket = settings.s3_bucket
        else:
            os.makedirs(settings.storage_local_root, exist_ok=True)
            self._root = settings.storage_local_root

    def save(self, key: str, data: bytes) -> None:
        if self.backend == "s3":
            self._s3.put_object(Bucket=self._bucket, Key=key, Body=data)
        else:
            path = os.path.join(self._root, key)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)

    def delete(self, key: str) -> None:
        if self.backend == "s3":
            self._s3.delete_object(Bucket=self._bucket, Key=key)
        else:
            path = os.path.join(self._root, key)
            if os.path.exists(path):
                os.remove(path)

    def exists(self, key: str) -> bool:
        if self.backend == "s3":
            try:
                self._s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except Exception:
                return False
        else:
            return os.path.exists(os.path.join(self._root, key))

    def url(self, key: str, expires: int = 3600) -> str:
        if self.backend == "s3":
            return self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
        else:
            return f"/files/{key}"

    def presigned_upload_url(self, key: str, expires: int = 3600) -> str:
        """Return a presigned PUT URL for direct upload (S3 only). Local returns /api/v1/assets/upload-local/{key}."""
        if self.backend == "s3":
            return self._s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
        return f"/api/v1/assets/upload-local/{key}"

    def read(self, key: str) -> bytes:
        if self.backend == "s3":
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            return obj["Body"].read()
        else:
            path = os.path.join(self._root, key)
            with open(path, "rb") as f:
                return f.read()


storage = StorageService()
