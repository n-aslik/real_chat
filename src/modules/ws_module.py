from fastapi import HTTPException, status, UploadFile
from connections.dbconn import connection
import magic
from pathlib import Path
import uuid



# Настройки остаются прежними
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/mpeg", "video/ogg"]
ALLOWED_AUDIO_TYPES = ["audio/mpeg", "audio/wav", "audio/ogg"]
ALLOWED_FILE_TYPES = ["application/pdf"]
ALL_ALLOWED_TYPES = ALLOWED_AUDIO_TYPES+ ALLOWED_IMAGE_TYPES+ALLOWED_VIDEO_TYPES+ ALLOWED_FILE_TYPES
MAX_FILE_SIZE = 100 * 1024 * 1024 

def validate_file(file: UploadFile):
    # 1. Проверка размера
    file.file.seek(0, 2)  # Переходим в конец файла
    file_size = file.file.tell()
    file.file.seek(0)  # Возвращаемся в начало
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс 5MB)")

    # 2. Проверка реального типа контента (Magic Numbers)
    header = file.file.read(2048)  # Читаем первые 2Кб
    file.file.seek(0)  # Возвращаемся в начало
    mime_type = magic.from_buffer(header, mime=True)
    
    if mime_type not in ALL_ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Неподдерживаемый тип файла")
        
    return file

async def is_user_in_chat(user_id: str, chat_name: str):
    with connection() as cur:
        cur.execute("SELECT common.get_is_user_in_chat(%s, %s)", (user_id, chat_name))
        result = cur.fetchone()[0]
        return result
    raise HTTPException(status_code=404, detail=str(result))

async def save_message_to_db(chat: str, sender_id: str, messages: str, file_path: str, file_name: str):
        with connection() as cur:
            cur.execute("CALL common.create_messages(%s, %s, %s, %s, %s, %s)", (chat, sender_id, '{}', messages, file_path, file_name))
            result = cur.fetchone()[0]
            if result.get('status') == 0:
                return result
                
        raise HTTPException(status_code=404, detail=str(result))

async def update_message(chat: str, sender_id: str,message_id: str,  messages: str):
    with connection() as cur:
        cur.execute("CALL common.update_messages(%s::character varying, %s::uuid, %s::character varying, %s::json, %s::text)", (chat, sender_id, message_id, '{}', messages))
        result = cur.fetchone()[0]
        if result.get('status') == 0:
            return result
            
    raise HTTPException(status_code=404, detail=str(result))


async def delete_message(chat: str, sender_id: str, message_id: str):
    with connection() as cur:
        cur.execute("CALL common.delete_messages(%s::character varying, %s::uuid, %s::character varying, %s::json)", (chat, sender_id, message_id,'{}'))
        result = cur.fetchone()[0]
        if result.get('status') == 0:
            return result
            
    raise HTTPException(status_code=404, detail=str(result))




    
