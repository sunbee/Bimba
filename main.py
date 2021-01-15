from typing import List

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/grahaka/", response_model=schemas.Grahaka)
def add_grahaka(grahaka: schemas.GrahakaCreate, db: Session = Depends(get_db):
    grahaka_DB = crud.get_grahaka_by_email(db=db, email=grahaka.email)
    if grahaka_DB:
        raise HTTPException(status_code=400, detail="Already have the grahaka.")
    return crud.create_grahaka(db=db, grahaka=grahaka)

@app.get("/grahaka/", response_model=List[schemas.Grahaka])
def access_grahaka(skip: int=0, limit: int=99, db: Session = Depends(get_db)):
    return crud.get_grahaka(db=db, skip=skip, limit=limit)

@app.get("/grahaka/{ID}", response_model=schemas.Grahaka)
def access_grahaka_by_ID(ID: int, db: Session = Depends(get_db)):
    grahaka_DB = crud.get_grahaka_by_ID(db=db, grahaka_id=ID)
    if not grahaka_DB:
        raise HTTPException(status_code=404, detail="Found no user with {ID}.")
    return grahaka_DB

@app.post("/grahaka/{ID}/patra/", response_model=schemas.Patra):
def add_patra_for_grahaka(ID: int, patra: schemas.PatraCreate, db = Depends(get_db)):
    return crud.create_patra_for_grahaka(db=db, patra=patra, grahaka_id=ID)

@app.get("/patra/", response_model=schemas.Patra)
def access_patra(ID: int, db = Depends(get_db)):
    return crud.get_patra()
