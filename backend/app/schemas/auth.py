from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CaptchaChallenge(BaseModel):
    captcha_token: str
    question: str
    expires_in_seconds: int


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    branch_id: int | None
    branch_name: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)
    role: str = Field(pattern="^(superadmin|admin|kuzatuvchi|viewer)$")
    branch_id: int | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8)
    role: str | None = Field(default=None, pattern="^(superadmin|admin|kuzatuvchi|viewer)$")
    branch_id: int | None = None
    is_active: bool | None = None
