import os
import magic
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from typing import List

app = FastAPI()

# Конфигурация
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "application/pdf", "text/plain"]
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Функция для проверки безопасности файла
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
    
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Неподдерживаемый тип файла")
        
    return file

@app.post("/chat/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    # Применяем валидацию
    validate_file(file)
    
    # 3. Безопасное сохранение: генерация нового имени, чтобы избежать path traversal
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
        
    return {"info": f"Файл {file.filename} загружен успешно", "saved_as": safe_filename}


from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from minio import Minio
from minio.error import S3Error
import io

app = FastAPI()

# --- Настройка MinIO ---
MINIO_CLIENT = Minio(
    "localhost:9000",  # Адрес вашего MinIO
    access_key="minioadmin",  # Ваш access key
    secret_key="minioadmin",  # Ваш secret key
    secure=False  # Поставьте True, если используете HTTPS
)
BUCKET_NAME = "my-bucket"

# Инициализация бакета при старте
if not MINIO_CLIENT.bucket_exists(BUCKET_NAME):
    MINIO_CLIENT.make_bucket(BUCKET_NAME)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Загрузка файла в MinIO"""
    try:
        # Получаем данные файла
        file_data = await file.read()
        file_size = len(file_data)
        
        # Загружаем в MinIO
        MINIO_CLIENT.put_object(
            BUCKET_NAME,
            file.filename,
            data=io.BytesIO(file_data),
            length=file_size,
            content_type=file.content_type
        )
        return {"message": f"Файл {file.filename} успешно загружен"}
    except S3Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{file_name}")
async def download_file(file_name: str):
    """Скачивание файла из MinIO"""
    try:
        # Получаем объект из MinIO
        response = MINIO_CLIENT.get_object(BUCKET_NAME, file_name)
        
        # Читаем данные и закрываем ответ
        file_data = response.read()
        response.close()
        response.release_conn()
        
        # Возвращаем файл в виде потока
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Файл не найден")

# Для запуска: uvicorn main:app --reload


async function sendFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file || ws.readyState !== WebSocket.OPEN) return;

    // 1. Готовим данные для загрузки
    const formData = new FormData();
    formData.append("file", file);

    try {
        // 2. Загружаем файл на бэкенд (MinIO)
        const response = await fetch("/chats/v1/upload", {
            method: "POST",
            body: formData,
            headers: {
                // Если нужна авторизация: "Authorization": `Bearer ${token}`
            }
        });
        const result = await response.json();

        // 3. Отправляем ссылку в WebSocket
        ws.send(JSON.stringify({
            type: "group",
            target: parseInt(cleanRoomId),
            text: "", 
            file_url: result.file_url, // Теперь передаем URL вместо Base64
            file_name: result.file_name
        }));

    } catch (error) {
        console.error("Ошибка загрузки:", error);
        alert("Не удалось отправить файл");
    }

    fileInput.value = "";
}



