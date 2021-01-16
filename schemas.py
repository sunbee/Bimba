from typing import List, Optional
from pydantic import BaseModel, HttpUrl, EmailStr

class PatraBase(BaseModel):
    # Common to reading/writing
    image: HttpUrl
    document: Optional[HttpUrl]=None
    tags: str

class PatraCreate(PatraBase):
    # For writing ops
    pass

class Patra(PatraBase):
    # For reading ops
    id: int
    owner_id: int

    class Config:
        orm_mode=True

class GrahakaBase(BaseModel):
    # Common to reading/writing
    email: EmailStr

class GrahakaCreate(GrahakaBase):
    # For writing ops
    password: str

class Grahaka(GrahakaBase):
    # For reading ops
    id: int
    is_active: bool = True
    is_admin: bool = False
    items: List[Patra] = []

    class Config:
        orm_mode=True

