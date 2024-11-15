"""
Copyright (c) Kae Bartlett

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

from typing import Generic, TypeVar


__all__ = (
    "MaxLenList",
)


LI = TypeVar("LI")


class MaxLenList(list, Generic[LI]):
    """
    A list implementation that has a maximum number of entries.

    Parameters
    ----------
    max_entries : int
        The maximum number of items allowed in the list.
    """

    def __init__(self, max_entries: int = 250):
        self.max_entries: int = max_entries

    def append(self, _object: LI, /):
        """
        Appends an object into the list and removes the first element of
        the list until the length is less than the maximum length provided

        Parameters
        ----------
        _object : LI
            The object to append to the list

        """
        # Keep removing the first item until we are within queue bounds
        super().append(_object)
        while len(self) > self.max_entries:
            super().pop(0)
