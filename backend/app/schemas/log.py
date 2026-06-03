from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SystemLogOut(BaseModel):
    id: int
    branch_id: int | None
    level: str
    category: str
    source: str | None
    message: str
    details: dict | None
    status: str
    admin_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemLogUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|reviewed|resolved)$")
    admin_note: str | None = None
