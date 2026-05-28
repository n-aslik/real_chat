from fastapi import HTTPException,status
from connections.dbconn import connection
import lib.acl as ACL
from src.models import models



# region ADMINISTRATION

async def create_user(data: models.User):

    with connection() as cur:
        result = None
        cur.execute("CALL common.create_user(%s, %s, %s, %s);",(data.username, data.phone_number, data.password ,'{}'))
        result = cur.fetchone()[0]
        if result['status'] == 0:
            return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")

async def update_user(user_id: str, data: models.User):

    with connection() as cur:
        result = None
        cur.execute("CALL common.update_user(%s, %s, %s, %s, %s);" ,(user_id, '{}', data.username, data.phone_number, data.password))
        result = cur.fetchone()[0]
        if result['status'] == 0:
            return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")

async def delete_user(user_id: str ):
    result = None
    with connection() as cur:
        cur.execute("CALL common.delete_admin(%s, %s);", (user_id, '{}'))
        result = cur.fetchone()[0]
        if result["status"] == 0:
            return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")

async def get_users(user_id: str):
    result = None
    with connection() as cur:
        cur.execute("SELECT common.get_users(%s);",(user_id,))
        result = cur.fetchone()[0]
        return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")

async def get_user_by_id(user_id: str):
    result = None
    with connection() as cur:
        cur.execute("SELECT common.get_user_by_id(%s);", (user_id,))
        result = cur.fetchone()[0]
        return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")


# endregion

# region AUTHORIZATION

async def login(data: models.Login):
    result = None
    with connection() as cur:
        cur.execute("CALL common.login(%s, %s, %s);" ,(data.phone_number, data.password, '{}'))
        result = cur.fetchone()[0]
        if result['status'] == 0:
            result['access_token'] = ACL.generate_jwt_token(1, result['id'], data.phone_number, result['role'], result['username'] )
            result['refresh_token'] = ACL.generate_jwt_token(2, result['id'], data.phone_number, result['role'], result['username'])
            del result["phone_number"]
            return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")
 
async def refresh_token(payload):
    access_token = ACL.generate_jwt_token(1, payload["user_id"], payload["phone_number"], payload["role"], payload['username'])
    refresh_token = ACL.generate_jwt_token(2, payload["user_id"], payload["phone_number"], payload["role"], payload['username'])
    return {
        'status': 1,
        'user_id': payload["user_id"],
        'access_token': access_token,
        'refresh_token': refresh_token
        
    }
    
async def logout(id: str):
    result = None
    with connection() as cur:
        cur.execute("CALL common.logout(%s, %s);", (id, '{}'))
        result = cur.fetchone()[0]
        if result["status"] == 0:
            return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")
    
# endregion

    
