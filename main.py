from typing import List
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

import models, crud, schemas
import database
import config
import authenticate
import authorize

from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

oauth2scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
async def get_current_grahaka(db: Session = Depends(get_db), token: str = Depends(oauth2scheme)):
    """
    Decodes the token to get the logged-in grahaka.
    Executes the following steps:
    1. Creates an exception class extending HTTPException.
    2. Decodes the token and extracts the username (email).
    3. Checks that the grahaka's record exists in the database.
    4. Returns the grahaka object or raises an HTTP exception.
    """
    credential_exception = HTTPException(
        status_code=401,
        detail="Granted no access.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credential_exception
        grahaka = crud.get_grahaka_by_email(db, username)
        if not grahaka:
            raise credential_exception
        return grahaka

    except JWTError:
        raise credential_exception

    pass

async def get_current_active_grahaka(grahaka: models.Grahaka = Depends(get_current_grahaka)):
    if not grahaka.is_active:
        raise HTTPException(status_code=400, detail="Grahaka status inactive.")
    return grahaka

async def get_current_admin(admin: models.Grahaka = Depends(get_current_active_grahaka)):
    """
    Restrict certain path operations by injecting admin via Dependency Injection.
    This requires the following:
    1. Write a SQL query to ugrade a grahaka to admin. Use command-line interface to SQLite3.
    2. Inject admin via Dependency Injection in a restricted path op using get_current_admin function.
    3. That's all! Verify using Swagger docs by logging in as admin, logging out and logging in as grahaka.
    """
    if not admin.is_admin:
        raise HTTPException(status_code=400, detail="Found no admin privileges to continue.")
    return admin

@app.post("/token", tags=["Security"], summary="Generate token after verifying credentials presented.")
async def create_JWT_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Issue a token when the grahaka signs in with username and password.
    The username and password are passed through a form.
    Executes the steps as follows:
    1. Authenticates the grahaka with the credentials supplied.
    2. Create an access token.
    3. Return the token in the expected format per specification.
    """
    grahaka = authenticate.authenticate_grahaka(db, form_data.username, form_data.password)
    if not grahaka:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Issued no token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_JWT = authorize.create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRES_MINUTES)
    )
    return {"access_token": token_JWT, "token_type": "bearer"}

@app.post("/grahaka/", response_model=schemas.Grahaka, 
tags=["Grahaka"], 
summary="Create a new grahaka account.")
async def add_grahaka(grahaka: schemas.GrahakaCreate, db: Session = Depends(get_db)):
    grahaka_DB = crud.get_grahaka_by_email(db=db, email=grahaka.email)
    if grahaka_DB:
        raise HTTPException(status_code=400, detail="Already have the grahaka.")
    return crud.create_grahaka(db=db, grahaka=grahaka)

@app.get("/grahaka/", response_model=List[schemas.Grahaka], 
tags=["Grahaka", "Admin"], 
summary="Retrieve all grahaka for admin.")
async def access_grahaka(skip: int=0, limit: int=99, 
    db: Session = Depends(get_db), 
    admin: schemas.Grahaka = Depends(get_current_admin)):
    return crud.get_grahaka(db=db, skip=skip, limit=limit)

@app.get("/grahaka/me/", response_model=schemas.Grahaka, 
tags=["Grahaka", "Security"], 
summary="Who am I?")
async def access_loggedin_grahaka(grahaka_loggedin: models.Grahaka = Depends(get_current_active_grahaka)):
    return grahaka_loggedin

@app.get("/grahaka/{ID}", response_model=schemas.Grahaka, 
tags=["Grahaka", "Admin"], 
summary="Retrieve grahaka's record by ID for admin.")
async def access_grahaka_by_ID(ID: int, 
    db: Session = Depends(get_db),
    admin: schemas.Grahaka = Depends(get_current_admin)):
    grahaka_DB = crud.get_grahaka_by_ID(db=db, grahaka_id=ID)
    if not grahaka_DB:
        raise HTTPException(status_code=404, detail=f"Found no user with {ID}.")
    return grahaka_DB

@app.delete("/grahaka/{ID}", response_model=schemas.Grahaka, 
tags=["Grahaka", "Admin"], 
summary="Remove grahaka's account and records with ID for admin.")
async def remove_grahaka_by_ID(ID: int, 
    db: Session = Depends(get_db),
    admin: schemas.Grahaka = Depends(get_current_admin)):
    grahaka_DB = crud.delete_grahaka(db=db, grahaka_id=ID)
    if not grahaka_DB:
        raise HTTPException(status_code=404, detail=f"Found no grahaka with {ID}.")
    return grahaka_DB

@app.post("/grahaka/{ID}/patra/", response_model=schemas.Patra, 
tags=["Grahaka", "Patra", "Admin"], 
summary="Add a patra to grahaka's collection with ID for admin.")
async def add_patra_for_grahaka(ID: int, patra: schemas.PatraCreate, 
    db = Depends(get_db),
    admin: schemas.Grahaka = Depends(get_current_admin)):
    return crud.create_patra_for_grahaka(db=db, patra=patra, grahaka_id=ID)

@app.post("/patra/", response_model=schemas.Patra,
tags=["Grahaka", "Patra"],
summary="Upload the logged-in grahaka's patra.")
async def upload_patra(
    patra: schemas.PatraCreate,
    db: Session = Depends(get_db), 
    grahaka: schemas.Grahaka = Depends(get_current_active_grahaka)):
    return crud.create_patra_for_grahaka(db=db, patra=patra, grahaka_id=grahaka.id)
    

@app.get("/patra/", response_model=List[schemas.Patra], 
tags=["Patra"], 
summary="Retrieve records for logged-in grahaka.")
async def access_patra(skip: int=0, limit: int=99, 
    db: Session = Depends(get_db), 
    grahaka: schemas.Grahaka = Depends(get_current_active_grahaka)):
    return crud.get_patra_for_grahaka(db=db, grahaka_id=grahaka.id, skip=skip, limit=limit)

@app.get("/patra/{ID}", response_model=schemas.Patra, 
tags=["Patra", "Admin"], 
summary="Retrieve patra by ID for admin.")
async def access_patra_by_ID(ID: int, 
    db = Depends(get_db),
    admin: schemas.Grahaka = Depends(get_current_admin)):
    patra_DB = crud.get_patra_by_ID(db=db, patra_id=ID)
    if not patra_DB:
        raise HTTPException(status_code=404, detail=f"Found no patra with {ID}")
    return patra_DB
