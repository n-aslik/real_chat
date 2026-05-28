from typing import Dict, Set, List
from fastapi import WebSocket
import asyncio


class ChatManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.rooms: Dict[str, Set[str]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, room_id: str, websocket: WebSocket):
    # 1. Удаляем конкретное соединение из списка активных
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # 2. Если у пользователя больше нет открытых вкладок/соединений вообще
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # 3. Удаляем пользователя из конкретной комнаты
        if room_id in self.rooms:
            # Проверяем, есть ли у пользователя другие активные сокеты.
            # Если их нет, только тогда убираем его из рассылки этой комнаты.
            if user_id not in self.active_connections:
                self.rooms[room_id].discard(user_id)
                
                # Чистим комнату, если она стала пустой
                if not self.rooms[room_id]:
                    del self.rooms[room_id]

    def join_room(self, user_id: str, room_id: str):
        self.rooms.setdefault(room_id, set()).add(user_id)

    async def broadcast_to_room(self, room_id: str, message: dict):
        users = self.rooms.get(room_id, set())

        for uid in users:
            sockets = self.active_connections.get(uid, [])

            for ws in sockets:
                try:
                    await ws.send_json({
                        **message,
                        "is_self": uid == message.get("sender_id")
                    })
                except:
                    pass