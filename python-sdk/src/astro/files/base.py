from __future__ import annotations

import io

import pandas as pd
import smart_open
from attr import define, field

from astro import constants
from astro.airflow.datasets import Dataset
from astro.files.locations import create_file_location
from astro.files.locations.base import BaseFileLocation
from astro.files.types import FileType, create_file_type


@define
class File(Dataset):
    """
    Handle all file operations, and abstract away the details related to location and file types.
    Intended to be used within library.

    :param path: Path to a file in the filesystem/Object stores
    :param conn_id: Airflow connection ID
    :param filetype: constant to provide an explicit file type
    :param normalize_config: parameters in dict format of pandas json_normalize() function.
    """

    path: str
    conn_id: str | None = None
    filetype: constants.FileType | None = None
    normalize_config: dict | None = None

    uri: str = field(init=False)
    extra: dict | None = field(init=False, factory=dict)

    template_fields = (
        "path",
        "conn_id",
    )

    @property
    def location(self) -> BaseFileLocation:
        return create_file_location(self.path, self.conn_id)

    @property
    def type(self) -> FileType:  # noqa: A003
        return create_file_type(
            path=self.path,
            filetype=self.filetype,
            normalize_config=self.normalize_config,
        )

    @property
    def size(self) -> int:
        """
        Return the size in bytes of the given file.

        :return: File size in bytes
        """
        size: int = self.location.size
        return size

    def is_binary(self) -> bool:
        """
        Return a constants.FileType given the filepath. Uses a naive strategy, using the file extension.

        :return: True or False
        """
        result: bool = self.type.name == constants.FileType.PARQUET
        return result

    def create_from_dataframe(self, df: pd.DataFrame) -> None:
        """Create a file in the desired location using the values of a dataframe.

        :param df: pandas dataframe
        """
        with smart_open.open(
            self.path, mode="wb", transport_params=self.location.transport_params
        ) as stream:
            self.type.create_from_dataframe(stream=stream, df=df)

    def _convert_remote_file_to_byte_stream(self) -> io.IOBase:
        """
        Read file from all supported location and convert them into a buffer that can be streamed into other data
        structures.

        Due to noted issues with using smart_open with pandas (like
        https://github.com/RaRe-Technologies/smart_open/issues/524), we create a BytesIO or StringIO buffer
        before exporting to a dataframe. We've found a sizable speed improvement with this optimizat

        Returns: an io object that can be streamed into a dataframe (or other object)

        """
        mode = "rb" if self.is_binary() else "r"
        remote_obj_buffer = io.BytesIO() if self.is_binary() else io.StringIO()
        with smart_open.open(
            self.path, mode=mode, transport_params=self.location.transport_params
        ) as stream:
            remote_obj_buffer.write(stream.read())
        remote_obj_buffer.seek(0)
        return remote_obj_buffer

    def export_to_dataframe(self, **kwargs) -> pd.DataFrame:
        """Read file from all supported location and convert them into dataframes.

        Due to noted issues with using smart_open with pandas (like
        https://github.com/RaRe-Technologies/smart_open/issues/524), we create a BytesIO or StringIO buffer
        before exporting to a dataframe. We've found a sizable speed improvement with this optimization.
        """

        return self.type.export_to_dataframe(
            self._convert_remote_file_to_byte_stream(), **kwargs
        )

    def exists(self) -> bool:
        """Check if the file exists or not"""
        file_exists: bool = self.location.exists()
        return file_exists

    def __str__(self) -> str:
        return self.path

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.location == other.location and self.type == other.type

    def __hash__(self) -> int:
        return hash((self.path, self.conn_id, self.filetype))

    @uri.default
    def _path_to_dataset_uri(self) -> str:
        """Build a URI to be passed to Dataset obj introduced in Airflow 2.4"""
        from urllib.parse import urlencode, urlparse

        parsed_url = urlparse(url=self.path)
        netloc = parsed_url.netloc
        # Local filepaths do not have scheme
        parsed_scheme = parsed_url.scheme or "file"
        scheme = f"astro+{parsed_scheme}"
        extra = {}
        if self.filetype:
            extra["filetype"] = str(self.filetype)

        new_parsed_url = parsed_url._replace(
            netloc=f"{self.conn_id}@{netloc}" if self.conn_id else netloc,
            scheme=scheme,
            query=urlencode(extra),
        )
        return new_parsed_url.geturl()


def resolve_file_path_pattern(
    path_pattern: str,
    conn_id: str | None = None,
    filetype: constants.FileType | None = None,
    normalize_config: dict | None = None,
) -> list[File]:
    """get file objects by resolving path_pattern from local/object stores
    path_pattern can be
    1. local location - glob pattern
    2. s3/gcs location - prefix

    :param path_pattern: path/pattern to a file in the filesystem/Object stores,
        supports glob and prefix pattern for object stores
    :param conn_id: Airflow connection ID
    :param filetype: constant to provide an explicit file type
    :param normalize_config: parameters in dict format of pandas json_normalize() function
    """
    location = create_file_location(path_pattern, conn_id)

    files = [
        File(
            path=path,
            conn_id=conn_id,
            filetype=filetype,
            normalize_config=normalize_config,
        )
        for path in location.paths
        if not path.endswith("/")
    ]
    if len(files) == 0:
        raise ValueError(f"File(s) not found for path/pattern '{path_pattern}'")

    return files
