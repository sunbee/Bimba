import config
import crud

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(password, password_hashed):
    return pwd_context.verify(password, password_hashed)

def get_hashed_password(password):
    return pwd_context.hash(password)

def authenticate_grahak(db, username:str, password: str):
    """
    AUthenticate the grahak in the following steps:
    1. Check that the username (email) exists in the database.
    2. Retrieve the grahak's profile from database and verify password.
    3. Return the grahak using pydantic model.
    """
    grahaka_db = crud.get_grahaka_by_email(db, username)
    if not grahaka_db:
        return False
    if not verify_password(password, grahaka_db.password_hashed):
        return False
    return grahaka_db

