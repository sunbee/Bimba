from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, Path, Query, File, UploadFile, Response, Header, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from jinja2 import Environment, FileSystemLoader
import requests
from requests.exceptions import HTTPError

import models, crud, schemas
import database
import config
import authenticate
import authorize
import FireCRUD

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
async def create_JWT_token(*, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), 
response: Response):
    """
    Issue a token when the grahaka signs in with username and password.
    The username and password are passed through a form.
    Executes the steps as follows:
    1. Authenticate the grahaka with the credentials supplied.
    2. Create an access token.
    3. Return the token in the expected format per specification.

    4. EXPERIMENTAL: Saet a cookie for browser to natively manage token.
        The client needs a mechanism to stash the token 
        and send it with future requests. By setting a cookie with the token, 
        we open up the opportunity 
        of using the native capabilities of a browser to handle cookies,
        avoiding client-side programming in javascript (for example.)
        So in addition to sending the token generated in the response body, 
        we have set a cookie which is retrieved in token-decoding function.
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
    response.delete_cookie(key="access_token")
    response.set_cookie(key="access_token_cookie", value=token_JWT)
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
summary="Add a patra to grahaka's collection with ID for admin.",
deprecated=True)
async def add_patra_for_grahaka(ID: int, patra: schemas.PatraCreate, 
    db = Depends(get_db),
    admin: schemas.Grahaka = Depends(get_current_admin)):
    return crud.create_patra_for_grahaka(db=db, patra=patra, grahaka_id=ID)

@app.post("/patra/", response_model=schemas.Patra,
tags=["Grahaka", "Patra"],
summary="Upload a patra for the logged-in grahaka.",
deprecated=True)
async def upload_patra(
    patra: schemas.PatraCreate,
    db: Session = Depends(get_db), 
    grahaka: schemas.Grahaka = Depends(get_current_active_grahaka)):
    return crud.create_patra_for_grahaka(db=db, patra=patra, grahaka_id=grahaka.id)

@app.post("/patra_upload/", response_model=schemas.Patra,
tags=["Grahaka", "Patra"],
summary="Upload a patra for the logged-in grahaka.")
async def upload_patra(
    bimba: UploadFile = File(...),
    tags: List[str] = Query(..., description="Furnish tags for searchability."),
    db: Session = Depends(get_db), 
    grahaka: schemas.Grahaka = Depends(get_current_active_grahaka)):
    try:
        fire_token = FireCRUD.retrieve_authToken()
    except HTTPError as errHTTP:
        raise HTTPException(status_code=404, detail=f'Got no token from Firebase. See: {errHTTP}')
    except Exception as err:
        raise HTTPException(status_code=404, detail=f'Got no auth token. See: {err}')
    else:
        print(fire_token)
        if not len(tags) > 1:
            label = tags[0]
        else:
            label = ",".join(tags)
        print(tags)
        url2fire = 'https://firebasestorage.googleapis.com/v0/b/shiva-923e9.appspot.com/o/stash%2F'
        url2file = url2fire + bimba.filename.replace(" ", "_")
        headers = {"Content-Type": bimba.content_type, "Authorization": "Bearer "+fire_token["idToken"]}
        try:
            r = requests.post(url2file, data=bimba.file.read(), headers=headers)
            r.raise_for_status()
        except HTTPError as errHTTP:
            raise HTTPException(status_code=404, detail=f'Uploaded no image to Firebase. See: {errHTTP}')
        except Exception as err:
            raise HTTPException(status_code=404, detail=f'Posted no image to Firebase. See: {err}')
        else:           
            response = r.json()
            print(response)
            bimbaURL = url2file + '?alt=media&token=' + response["downloadTokens"]
            bimbapatra = schemas.PatraCreate(image=bimbaURL, tags=label)
            
    return crud.create_patra_for_grahaka(db=db, patra=bimbapatra, grahaka_id=grahaka.id)

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

@app.delete("/patra/{ID}", response_model=schemas.Patra,
tags=["Patra"],
summary="Delete a patra by ID for the logged-in grahaka.")
async def remove_patra_by_ID(ID: int,
    db = Depends(get_db),
    grahaka: schemas.Grahaka = Depends(get_current_active_grahaka)):
    patra_DB = crud.delete_patra_for_grahaka(db=db, grahaka_id=grahaka.id, patra_id=ID)
    if not patra_DB:
        raise HTTPException(status_code=404, detail=f"Found no patra with {ID}")
    return patra_DB

@app.delete("/patra_delete/{ID}", response_model=schemas.Patra,
tags=["Patra"],
summary="Delete a patra by ID for the logged-in grahaka or admin.")
async def remove_patra_by_ID(ID: int,
    db = Depends(get_db),
    grahaka: schemas.Grahaka = Depends(get_current_active_grahaka)):
    patra_DB = crud.get_patra_by_ID(db=db, patra_id=ID)
    if not patra_DB:
        raise HTTPException(status_code=404, detail=f"Found no patra {ID}.")
    if not (patra_DB.owner_id == grahaka.id or grahaka.is_admin):
        raise HTTPException(status_code=401, detail=f"Grahaka has no right to delete {ID}.")
    try:
        fire_token = FireCRUD.retrieve_authToken()
    except HTTPError as errHTTP:
        raise HTTPException(status_code=404, detail=f'Got no token from Firebase. See: {errHTTP}')
    except Exception as err:
        raise HTTPException(status_code=404, detail=f'Got no auth token. See: {err}')
    else:
        print(fire_token)
        bimba2delete = patra_DB.image
        headers = {"Authorization": "Bearer "+fire_token["idToken"]}
        try:
            r = requests.delete(bimba2delete, headers=headers)
            r.raise_for_status()
        except HTTPError as errHTTP:
            raise HTTPException(status_code=404, detail=f'Removed no image from Firebase. See: {errHTTP}.')
        except Exception as err:
            raise HTTPException(status_code=404, detail=f'Removed no image. See: {err}.')
        else:           
            if r: # Successsful response to DELETE is an empty string
                print(f"DELETE operation successful with {bimba2delete}")
    
    return crud.delete_patra(db=db, patra_id=ID)
    
@app.delete("/patra_dosh/{ID}", response_model=schemas.Patra,
tags=["Patra", "Admin"],
summary="Delete a patra by ID for admin.", 
deprecated=True)
async def remove_patra_admin(ID: int,
    db = Depends(get_db),
    admin: schemas.Grahaka = Depends(get_current_admin)):

    patra_DB = crud.get_patra_by_ID(db=db, patra_id=ID)
    if not patra_DB:
        raise HTTPException(status_code=404, detail=f"Found no patra {ID}.")
    if not (patra_DB.owner_id == admin.id or admin.is_admin):
        raise HTTPException(status_code=401, detail=f"Grahaka has no right to delete {ID}.")
    try:
        fire_token = FireCRUD.retrieve_authToken()
    except HTTPError as errHTTP:
        raise HTTPException(status_code=404, detail=f'Got no token from Firebase. See: {errHTTP}')
    except Exception as err:
        raise HTTPException(status_code=404, detail=f'Got no auth token. See: {err}')
    else:
        print(fire_token)
        bimba2delete = patra_DB.image
        headers = {"Authorization": "Bearer "+fire_token["idToken"]}
        try:
            r = requests.delete(bimba2delete, headers=headers)
            r.raise_for_status()
        except HTTPError as errHTTP:
            raise HTTPException(status_code=404, detail=f'Removed no image from Firebase. See: {errHTTP}.')
        except Exception as err:
            raise HTTPException(status_code=404, detail=f'Removed no image. See: {err}.')
        else:           
            if r: # Successsful response to DELETE is an empty string
                print(f"DELETE operation successful with {bimba2delete}")
    
    return crud.delete_patra(db=db, patra_id=ID)
    """
    patra_DB = crud.delete_patra(db=db, patra_id=ID)
    if not patra_DB:
        raise HTTPException(status_code=404, detail=f"Found no patra with {ID}")
    return patra_DB
    """

@app.get("/sign-in", tags=["Web: Limited Feature"])
async def html_form_auth():
    """
    Serves a simple web-page for the grahaka to sign in.
    Grahaka can access information through a web-page 
    once authenticated in this way.
    """
    form_body = """
    <body>
        <div class="container">
            <form action="/token" enctype="multipart/form-data" method="POST">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
                <input type="submit" value="Submit">
            </form>
        </div>
    <body>
    """
    pass_unbreakable = """
    <input type="password" id="password" name="password" pattern="(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}" title="Must contain at least one number and one uppercase and lowercase letter, and at least 8 or more characters" required><input type="submit" value="Submit">
    """
    return HTMLResponse(content=form_body)

async def get_cookie_grahaka(db: Session = Depends(get_db), access_token_cookie: str = Cookie(None)):
    """
    Accepts token as cookie and decodes it to get the logged-in grahaka.
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
        payload = jwt.decode(access_token_cookie, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credential_exception
        grahaka = crud.get_grahaka_by_email(db, username)
        if not grahaka:
            raise credential_exception
        return grahaka
    except JWTError:
        raise credential_exception


@app.get("/web_patra", tags=["Web: Limited Feature"])
async def access_patra_by_tags(skip: int=0, limit: int=99,
    q: Optional[List[str]] = Query(None, description="Enter as many or as few tags as you desire."),
    db: Session = Depends(get_db),
    grahaka: schemas.Grahaka = Depends(get_cookie_grahaka)):
    """
    SPECIAL CASE FOR VIEWING IN BROWSER.
    The graghaka will need to /sign-in from the browser.
    The 
    """
    search_scope = crud.get_patra_for_grahaka(db=db, grahaka_id=grahaka.id, skip=skip, limit=limit)
    if not search_scope:
        HTTPException(status_code=404, detail="Found not matching results.")
    if q:
        search_terms = q
        while True:
            search_term = search_terms.pop()
            matches = [record for record in search_scope if search_term in record.tags.split(",")]
            search_scope = matches
            if len(matches) == 0:
                break
            if len(search_terms) == 0:
                break
    
    # Jinja-fy!
    file_loader = FileSystemLoader("templates")
    env = Environment(loader=file_loader)

    template = env.get_template("bimbapatra.html")
    output_html = template.render(records=search_scope)

    return HTMLResponse(content=output_html) # search_scope