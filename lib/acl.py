from fastapi import HTTPException, Request, Depends, WebSocket, Query
import jwt
from.config import Keys 
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
import time


ACCESS_TOKEN_EXPIRATION = 360  * 24 * 30
REFRESH_TOKEN_EXPIRATION = 360 * 24 * 60
TOKEN_TYPES = {
    1:{"token_type": "access_token", "expiration": ACCESS_TOKEN_EXPIRATION},
    2:{"token_type": "refresh_token", "expiration": REFRESH_TOKEN_EXPIRATION}
}

secret = Keys()
# access_expire_token=30


class  JWTTokenBearer(HTTPBearer):
    def __init__(self, auto_error: bool = False):
        super(JWTTokenBearer, self).__init__(auto_error=auto_error)
    async def __call__(self, request:Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTTokenBearer, self).__call__(request)
        if credentials:
            if not self.verify_jwt(credentials.credentials, request):
                raise HTTPException(status_code=403, detail="Invalid token")
            return credentials.credentials
        else:
            return HTTPException(status_code=401, detail="Not authentificated")
            
    def verify_jwt(self, jwt_token: str, request: Request) -> bool:
        IsValidToken: bool = False
        try:
            payload = jwt.decode(jwt_token, secret.public_key, algorithms=["RS256"])
            if time.time() < payload["expires"]:
                IsValidToken = True
            else:
                raise HTTPException(status_code=403, detail="JWT token is expired")
            
        except Exception as e :
            print(f"Token verification error{str(e)}")
            payload = None
        
        return IsValidToken
            
def generate_jwt_token (token_type:int, user_id:str, phone: str, role: str, username: str)->dict:
    token = TOKEN_TYPES.get(token_type)
    if not token:
        raise ValueError(f"Unknown token type {token_type}")
    payload = {
       "token_type" : token["token_type"],
        "user_id" : user_id,
        "phone_number" : phone,
        "role" : role,
        "username": username,
        "expires" : time.time()+token["expiration"]
    }
    header = {'alg' : 'RS256'}
    encoded_token=jwt.encode(payload, secret.private_key, algorithm='RS256')
    return encoded_token

def access_token (credentials: str = Depends(JWTTokenBearer()))->dict:
    try:
        decoded_token = jwt.decode(credentials, secret.public_key, algorithms=["RS256"])
        if decoded_token.get("token_type") != "access_token":
            raise HTTPException(status_code=403, detail="Invalid token type: must be access token")
        if time.time() > decoded_token["expires"]:
            raise HTTPException(status_code=401, detail="Token expired")
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=403, detail="JWT payload error: {}".format(e))


def refresh_token (credentials: str = Depends(JWTTokenBearer()))->dict:
    try:
        decoded_token = jwt.decode(credentials, secret.public_key, algorithms=["RS256"])
        if decoded_token.get("token_type") != "refresh_token":
            raise HTTPException(status_code=403, detail="Invalid token type: must be refresh token")
        if time.time() > decoded_token["expires"]:
            raise HTTPException(status_code=401, detail="Token expired")
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=403, detail="JWT payload error {}".format(e))


def parse_token (token:str)->dict:
    try:
        decoded_token=jwt.decode(token,secret.public_key, algorithms=["RS256"])
        return decoded_token
    except :
        raise HTTPException(status_code=403, detail="JWT decode error")



