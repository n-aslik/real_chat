from fastapi import HTTPException,status
from connections.dbconn import connection
from ..models import models
from typing import List





# region Chat types (dialog/group)

async def create_dialog_chat(user_ids:list[str]):
    result = None
    with connection() as cur:
        cur.execute("CALL common.create_dialog_chat(%s::uuid[], %s)", (user_ids, '{}'))
        result = cur.fetchone()[0]
        if result['status'] == 0:
            return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(result))


async def create_notice_chat(data: models.CreateGroupSchema):
    result = None
    with connection() as cur:
        cur.execute("CALL common.create_group_chat(%s::uuid[], %s::json )", (data.user_ids, '{}'))
        result = cur.fetchone()[0]
        if result['status'] == 0:
            return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(result))

async def return_chat_participants(data: models.ReturnChatParticipantsModel):
    result = None
    with connection() as cur:
        cur.execute("CALL common.return_chat_participants(%s::character varying, %s::uuid[], %s::json)", (data.group_id, data.user_ids ,'{}'))
        result = cur.fetchone()[0]
        if result['status'] == 0:
            return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(result))

async def get_my_chats(user_id: str):
    result = None
    with connection() as cur:
        cur.execute("SELECT common.get_my_chats(%s);", (user_id,))
        result = cur.fetchone()[0]
        return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")

async def get_chats_participants( chat_id: str):
    result = None
    with connection() as cur:
        cur.execute("SELECT common.get_chats_participants( %s);", ( chat_id,))
        result = cur.fetchone()[0]
        return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")

async def get_chats_messages(chat_id: str, last_date: str, last_id: int, limit: int):
    result = None
    with connection() as cur:
        cur.execute("SELECT common.get_chat_messages(%s::character varying, %s::timestamp without time zone, %s::bigint, %s::integer);", (chat_id, last_date, last_id, limit))
        result = cur.fetchone()[0]
        return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")

async def delete_chat(chat_id: str, user_id: str, is_all: bool):
    result = None
    with connection() as cur:
        cur.execute("CALL common.delete_chat(%s::character varying, %s::uuid, %s::json, %s::boolean);", (chat_id, user_id, '{}', is_all))
        result = cur.fetchone()[0]
        return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = f"{result}")


# endregion
