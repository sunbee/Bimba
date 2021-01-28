import requests
from requests import HTTPError
import config

def retrieve_authToken():
    """
    Executes a POST request to obatin a bearer token from Firebase auth services.
    Uses the API key for the Firebase project. This key belongs to the project owner.
    It must be kept secure at all times. 

    args: None
    returns: reponse (json) that has the bearer token on success
    usage: bearer_token = get_authToken()['idToken']
    """
    response = None

    # API Essentials
    authAPI_endPoint_signIn = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key='
    API_KEY=config.GoogleServices_API_KEY

    # Collect data for making HTTP request
    URL = authAPI_endPoint_signIn + API_KEY
    print(URL)
    payload = {
        "email": config.email,
        "password": config.password,
        "returnSecureToken": True
    }

    # Make request
    r_auth = requests.post(URL, json=payload)
    response = r_auth.json()

    return response
    