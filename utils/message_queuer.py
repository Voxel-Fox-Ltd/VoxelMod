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
