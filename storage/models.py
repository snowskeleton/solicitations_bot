from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    email: str
    is_admin: bool = False

@dataclass
class MagicLinkToken:
    token: str
    email: str
    expires_at: float


@dataclass
class Schedule:
    id: int
    user_id: int
    name: str
    monday: Optional[str]
    tuesday: Optional[str]
    wednesday: Optional[str]
    thursday: Optional[str]
    friday: Optional[str]
    saturday: Optional[str]
    sunday: Optional[str]


@dataclass
class Filter:
    id: int
    user_id: int
    name: str
    criteria: str
