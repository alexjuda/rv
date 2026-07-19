"""
Things we keep in local storage, regardless of the persistence backend.
"""

from dataclasses import dataclass
from datetime import datetime

from .github import FullPR


@dataclass
class SyncMeta:
    synced_at: datetime


@dataclass
class StoredPR:
    """
    A PR as stored in local cache, bundled with its sync metadata.
    """

    pr: FullPR
    meta: SyncMeta
