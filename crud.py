from sqlalchemy.orm import Session

import models, schemas
import authenticate

# Read (cRud)
#   - Single user by ID or email
#   - Multiple users
#   - Multiple items

def get_grahaka_by_ID(db: Session, grahaka_id: int):
    return db.query(models.Grahaka).filter(models.Grahaka.id == grahaka_id).first()

def get_grahaka_by_email(db: Session, email: str):
    return db.query(models.Grahaka).filter(models.Grahaka.email == email).first()

def get_grahaka(db: Session, skip: int=0, limit: int=99):
    return db.query(models.Grahaka).offset(skip).limit(limit).all()

def get_patra_by_ID(db: Session, patra_id: int):
    return db.query(models.Patra).filter(models.Patra.id == patra_id).first()

def get_patra(db: Session, skip: int=0, limit: int=99):
    return db.query(models.Patra).offset(skip).limit(limit).all()

def get_patra_for_grahaka(db: Session, grahaka_id: int, skip: int=0, limit: int=99):
    return db.query(models.Patra).filter(models.Patra.owner_id == grahaka_id).offset(skip).limit(limit).all()
    

# Create (Crud)

def create_grahaka(db: Session, grahaka: schemas.GrahakaCreate):
    password_hashed = authenticate.get_hashed_password(grahaka.password)
    grahaka_DB = models.Grahaka(email=grahaka.email, is_active=True, is_admin=False, password_hashed=password_hashed)
    db.add(grahaka_DB)
    db.commit()
    db.refresh(grahaka_DB)
    return grahaka_DB

def create_patra_for_grahaka(db: Session, patra: schemas.PatraCreate, grahaka_id: int):
    patra_DB = models.Patra(**patra.dict(), owner_id=grahaka_id)
    db.add(patra_DB)
    db.commit()
    db.refresh(patra_DB)
    return patra_DB

# Delete (cruD)

def delete_grahaka(db: Session, grahaka_id: int):
    grahaka_DB = db.query(models.Grahaka).filter(models.Grahaka.id == grahaka_id).first()
    if grahaka_DB:
        db.delete(grahaka_DB)
        db.commit()
    return grahaka_DB

def delete_patra_for_grahaka(db: Session, grahaka_id: int, patra_id: int):
    patra_DB = db.query(models.Patra).filter(models.Grahaka.id == grahaka_id, models.Patra.id == patra_id).first()
    if patra_DB:
        db.delete(patra_DB)
        db.commit()
    return patra_DB

def delete_patra(db: Session, patra_id: int):
    patra_DB = db.query(models.Patra).filter(models.Patra.id == patra_id).first()
    if patra_DB:
        db.delete(patra_DB)
        db.commit()
    return patra_DB