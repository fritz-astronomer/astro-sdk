from __future__ import annotations

import os
from urllib.parse import urlparse, urlunparse

from airflow.providers.amazon.aws.hooks.s3 import S3Hook

from astro.constants import FileLocation
from astro.files.locations.base import BaseFileLocation


class S3Location(BaseFileLocation):
    """Handler S3 object store operations"""

    location_type = FileLocation.S3

    @property
    def hook(self) -> S3Hook:
        return S3Hook(aws_conn_id=self.conn_id) if self.conn_id else S3Hook()

    @staticmethod
    def _parse_s3_env_var() -> tuple[str, str]:
        """Return S3 ID/KEY pair from environment vars"""
        return os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"]

    @property
    def transport_params(self) -> dict:
        """Structure s3fs credentials from Airflow connection.
        s3fs enables pandas to write to s3
        """
        session = self.hook.get_session()
        return {"client": session.client("s3")}

    @property
    def paths(self) -> list[str]:
        """Resolve S3 file paths with prefix"""
        url = urlparse(self.path)
        bucket_name = url.netloc
        prefix = url.path[1:]
        prefixes = self.hook.list_keys(bucket_name=bucket_name, prefix=prefix)
        paths = [
            urlunparse((url.scheme, url.netloc, keys, "", "", "")) for keys in prefixes
        ]
        return paths

    @property
    def size(self) -> int:
        return -1
