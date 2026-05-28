from fastapi import APIRouter,Depends,  UploadFile, File, HTTPException, status, Request, Form, Body
from ..models import models
from fastapi.responses import Response, StreamingResponse
from ..modules import auth_module, chat_module, ws_module
from typing import Optional
import lib.acl as ACL
from minio import Minio
from minio.error import S3Error
import os
from typing import List
import io


bucket = os.getenv("BUCKET_NAME","chatproj")

endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000").replace("http://", "").replace("https://", "")

s3 = Minio(
    endpoint=endpoint,
    access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
    secure=False  # Ставим False, если используем http (как в локальном докере)
)

try:
    if not s3.bucket_exists(bucket):
        s3.make_bucket(bucket)
except S3Error as e:
    print(f"Ошибка при работе с бакетом: {e}")

router=APIRouter(prefix="/v1")

# region AUTHORIZATON

@router.post("/login", tags=["AUTHORIZATON"])
async def login(data: models.Login ):
    return await auth_module.login(data)

@router.post('/refresh/token', tags=["AUTHORIZATON"])
async def refresh_token(response: Response, payload: dict = Depends(ACL.refresh_token)):
    return await auth_module.refresh_token(payload)

@router.delete('/logout', tags=["AUTHORIZATON"])
async def logout(payload: dict = Depends(ACL.access_token)):
    return await auth_module.logout(payload['user_id'])

# endregion

# region USERS

@router.post('/register', tags=["USERS"])
async def create_user(data: models.User ):
    return await auth_module.create_user(data)

@router.put("/update-user", tags=["USERS"])
async def update_user(user_id: str, data: models.User, payload:dict = Depends(ACL.access_token)):
    return  await auth_module.update_user(user_id,data)

@router.delete('/delete-user' , tags=["USERS"])
async def delete_user(user_id: str, payload: dict = Depends(ACL.access_token)):
    return await auth_module.delete_user(user_id)

@router.get('/get-users', tags=["USERS"] )
async def get_user(payload: dict = Depends(ACL.access_token)):
    return await auth_module.get_users(payload["user_id"])

@router.get('/get-user-by-id', tags=["USERS"])
async def get_user_by_id(user_id: str, payload: dict = Depends(ACL.access_token)):
    return await auth_module.get_user_by_id(user_id)

@router.get('/get-profile', tags=["USERS"] )
async def get_profile(payload: dict = Depends(ACL.access_token)):
    return await auth_module.get_user_by_id(payload["user_id"])

# endregion

# region FILES
@router.post("/upload", tags=["FILES"])
async def upload_file(file: UploadFile = File(...), payload:dict = Depends(ACL.access_token)):
    """Загрузка файла в MinIO"""
    try:
        check_file = ws_module.validate_file(file=file)

        # Получаем данные файла
        file_data = await check_file.read()
        file_size = len(file_data)
        # Загружаем в MinIO
        s3.put_object(
            bucket,
            check_file.filename,
            data=io.BytesIO(file_data),
            length=file_size,
            content_type=check_file.content_type
        )
        return {"message": f"Файл {file.filename} успешно загружен"}
    except S3Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/files/{file_name}", tags=["FILES"])
async def get_file_from_minio(file_name: str):
    """
    Позволяет открывать файлы напрямую по ссылке /chats/v1/files/название_файла
    """
    try:
        # Формируем путь к объекту в бакете (как при загрузке)
        # Если при загрузке ты добавлял префикс, добавь его и тут
        object_path = file_name 

        # 1. Проверяем наличие объекта в MinIO
        try:
            s3.stat_object(bucket, object_path)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise HTTPException(status_code=404, detail="Файл не найден в хранилище")
            raise

        # 2. Получаем поток данных
        response = s3.get_object(bucket, object_path)

    
        return StreamingResponse(
            response.stream(32 * 1024),
            media_type="application/octet-stream"
        )

    except Exception as e:
        print(f"Ошибка MinIO: {e}") 
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении файла: {str(e)}")
# endregion

# region CHAT-TYPES

@router.post('/create-dialog-chat', tags=["CHAT-TYPES"])
async def create_dialog_chat(user_ids: list[str], payload: dict = Depends(ACL.access_token)):
    current_user_id = payload["user_id"]
    if current_user_id not in user_ids:
        user_ids.append(current_user_id)
    return await chat_module.create_dialog_chat(user_ids)

@router.post('/create-notice-chat', tags=["CHAT-TYPES"])
async def create_group_chat(data: models.CreateGroupSchema, payload: dict = Depends(ACL.access_token)):
    current_user_id = payload["user_id"]
    if current_user_id not in data.user_ids:
        data.user_ids.append(current_user_id)
    if payload['role'] == "Волидайн":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return await chat_module.create_notice_chat(data)

@router.put('/return-chat-participants', tags=["CHAT-TYPES"])
async def return_chat_participants(data: models.ReturnChatParticipantsModel, payload: dict = Depends(ACL.access_token)):
    if payload["role"]=='User':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return await chat_module.return_chat_participants(data)


@router.get('/my-chats', tags=["CHAT-TYPES"])
async def get_my_chats(payload: dict = Depends(ACL.access_token)):
    return  await chat_module.get_my_chats(payload["user_id"])

@router.get('/chat-participants', tags=["CHAT-TYPES"])
async def get_chat_participants(chat_id: str):
    return  await chat_module.get_chats_participants(chat_id)

@router.get('/chats/{chat_id}/history', tags=["CHAT-TYPES"])
async def get_chat_messages(chat_id: str, last_date: Optional[str] = None, last_id: Optional[int] = None, limit: Optional[int] = None, payload: dict = Depends(ACL.access_token)):
    return  await chat_module.get_chats_messages(chat_id, last_date,  last_id, limit)

@router.delete('/delete-chat', tags=["CHAT-TYPES"])
async def delete_chat(chat_id: str, is_all: Optional[bool]= False, payload: dict = Depends(ACL.access_token)):
    return await chat_module.delete_chat(chat_id, payload["user_id"],is_all)

# end region


