from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Request, Query
from src.modules.websocket_manage import ChatManager
from lib.acl import secret
from src.modules import ws_module
import jwt
from datetime import datetime
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

manager = ChatManager()
router = APIRouter(prefix='/v1')

templates = Jinja2Templates(directory="templates")

@router.get("/sign-in", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/sign-up", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/chat-interface", response_class=HTMLResponse)
async def get_chat_interface(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})
    

# @router.websocket("/ws/chat/{room_id}")
# async def websocket_endpoint(
#     websocket: WebSocket, 
#     room_id: str, # Изменили на str, чтобы избежать автоматической 422 ошибки
#     token: str = Query(None) # Делаем необязательным для первичного перехвата
# ):
#     # 1. Сначала ПРИНИМАЕМ соединение, чтобы иметь право закрыть его корректно
#     if not token:
#         await websocket.close(code=1008)
#         return

#     # 2. Проверка JWT
#     try:
#         payload = jwt.decode(token, secret.public_key, algorithms=["RS256"])
#         auth_user_id = str(payload["user_id"])
#     except Exception as e:
#         print(f"JWT Error: {e}")
#         await websocket.close(code=1008)
#         return

#     # 3. Подключение к менеджеру
#     await manager.connect(auth_user_id, websocket)
#     # Приводим к int только здесь
#     await manager.join_room(auth_user_id, int(room_id)) 

#     try:
#         while True:
#             data = await websocket.receive_json()
            
#             # Сохранение в БД
#             payload_msg = await ws_module.save_message_to_db(
#                 chat_id=int(room_id),
#                 sender_id=auth_user_id,
#                 messages=data.get("text")
#             )

#             if payload_msg:
#                 if data.get("type") == "group":
#                     await manager.broadcast_to_group(int(room_id), payload_msg)
                
#     except WebSocketDisconnect:
#         manager.disconnect(auth_user_id)

# @router.websocket("/ws/chat/{room_id}")
# async def websocket_endpoint(
#     websocket: WebSocket,
#     room_id: str,
#     token: str = Query(None)
# ):
#     if not token:
#         await websocket.close(code=1008)
#         return

#     try:
#         payload = jwt.decode(token, secret.public_key, algorithms=["RS256"])
#         user_id = str(payload["user_id"])
#         username = payload.get("username") or payload.get("sub") or "User"
#     except:
#         await websocket.close(code=1008)
#         return


#     await manager.connect(user_id, websocket)
#     manager.join_room(user_id, room_id)

#     try:
#         while True:
#             data = await websocket.receive_json()

#             payload_msg = await ws_module.save_message_to_db(
#                 chat=room_id,
#                 sender_id=user_id,
#                 messages=data.get("messages"),
#                 file_path=data.get("file_path"),
#                 file_name=data.get("file_name")
#             )

#             if payload_msg and payload_msg.get("status") == 0:

#                 payload_msg.update({
#                     "username": username,
#                     "sender_id": user_id,
#                     "messages": payload_msg.get("messages") or data.get("messages"),
#                     "room_id": room_id
#                 })

#                 await manager.broadcast_to_room(room_id, payload_msg)

#     except WebSocketDisconnect:
#         manager.disconnect(user_id, websocket)
@router.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(None)
):
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(token, secret.public_key, algorithms=["RS256"])
        user_id = str(payload["user_id"])
        username = payload.get("username") or payload.get("sub") or "User"
    except:
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)
    manager.join_room(user_id, room_id)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")  
            message_id = data.get("message_id") 


            if action == "delete" and message_id:
                result = await ws_module.delete_message(
                    chat=room_id, 
                    sender_id=user_id, 
                    message_id=message_id
                )
                if result.get("status") == 0:
                    current_time = datetime.now().strftime("%H:%M")
                    edited_label = f"Иваз карда шуд {current_time}"
                    
                    await manager.broadcast_to_room(room_id, {
                        "action": "delete",
                        "message_id": message_id,
                        "status": 0
                    })
                continue 

            elif action == "update" and message_id:
                result = await ws_module.update_message(
                    chat=room_id,
                    sender_id=user_id,
                    message_id=message_id,
                    messages=data.get("messages")
                )
                if result.get("status") == 0:
                    # Инициализируем метку времени изменения
                    current_time = datetime.now().strftime("%H:%M")
                    edited_label = f"Иваз карда шуд {current_time}"
                    
                    # Рассылаем обновленное сообщение
                    payload_update = {
                        "action": "update",      # Передаем экшен
                        "status": 0,             # Передаем статус успеха
                        "id": message_id,        # Дублируем как 'id' для универсальности JS
                        "message_id": message_id,
                        "messages": data.get("messages"),
                        "username": username,
                        "sender_id": user_id,
                        "room_id": room_id,
                        "edited_text": edited_label
                    }
                    await manager.broadcast_to_room(room_id, payload_update)
                continue

            else:
                payload_msg = await ws_module.save_message_to_db(
                    chat=room_id,
                    sender_id=user_id,
                    messages=data.get("messages"),
                    file_path=data.get("file_path"),
                    file_name=data.get("file_name")
                )

                if payload_msg and payload_msg.get("status") == 0:
                    payload_msg.update({
                        "username": username,
                        "sender_id": user_id,
                        "messages": payload_msg.get("messages") or data.get("messages"),
                        "room_id": room_id,
                        "day": payload_msg.get("day")
                    })
                    await manager.broadcast_to_room(room_id, payload_msg)

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)