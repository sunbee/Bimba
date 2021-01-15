from sqlalchemy import Column, Boolean, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base

class Grahaka(Base):
    __tablename__ = 'grahaka'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hashed = Column(String)
    is_active = Column(Boolean)

    items = relationship("Patra", back_populates="owner")

class Patra(Base):
    __tablename__ = 'patra'

    id = Column(Integer, primary_key=True, index=True)
    image = Column(String)
    document = Column(String)
    tags = Column(String)
    owner_id = Column(Integer, ForeignKey('grahaka.id'))

    owner = relationship("Grahaka", back_populates="items")

