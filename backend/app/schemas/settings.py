from typing import Any, Dict

from pydantic import BaseModel


class SettingsOut(BaseModel):
    preferences: Dict[str, Any]


class SettingsUpdate(BaseModel):
    preferences: Dict[str, Any]