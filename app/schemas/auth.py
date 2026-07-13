from datetime import datetime

from pydantic import BaseModel

from app.models.user import Role


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: Role
    jurisdiction: str
    badge_number: str = ""


class UserOut(BaseModel):
    id: str
    username: str
    full_name: str
    role: Role
    jurisdiction: str
    badge_number: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
