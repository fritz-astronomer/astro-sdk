from typing import List

from astro.constants import FileLocation
from astro.files.locations.base import BaseFileLocation


class HttpLocation(BaseFileLocation):
    """Handler http location operations"""

    location_type = FileLocation.HTTP

    @property
    def paths(self) -> List[str]:
        """Resolve patterns in path"""
        return [self.path]
