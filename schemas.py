from typing import List, Optional
from pydantic import BaseModel, HttpUrl, EmailStr

class PatraBase(BaseModel):
    image: HttpUrl
    document: Optional[HttpUrl]=None
    tags: str

class PatraCreate(PatraBase):
    pass

class Patra(PatraBase):
    id: int
    owner_id: int

    class Config:
        orm_mode=True

class GrahakaBase(BaseModel):
    email: EmailStr
    ia_active: bool

class GrahakaCreate(GrahakaBase):
    password: str

class Grahaka(GrahakaBase):
    id: int
    items: List[Patra] = []

    class Config:
        orm_mode=True

