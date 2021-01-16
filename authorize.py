import config
from jose import JWTError, jwt
from typing import Optional
from datetime import datetime, timedelta

SECRET_KEY=config.SECRET_KEY
ALGORITHM=config.ALGORITHM
ACCESS_TOKEN_EXPIRES_MINUTES=config.ALGORITHM

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates a JWT token with a dictionary 
    that has the username stashed with the key 'sub' or 'subject'.
    The validiity defaults to 20 minutes unless otherwise specified.
    Implements teh steps as follows:
    1. Makes a copy of the dictionary with username.
    2. Calculates the expiry timestaamp after checking whether default has override.
    3. Adds the expiry timestamp to the dictionary to encode.
    4. Encodes and returns the token.
    """
    to_encode = data.copy()
    if expires_delta:
        expiry = datetime.utcnow() + expires_delta
    else:
        expiry = datetime.utcnow() + timedelta(minutes=20)
    to_encode.update({"exp": expiry})
    encoded_jwt = jwt.encode(to_encode, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt