from pydantic import BaseModel
from typing import Optional, Dict, List


class User(BaseModel): 
    username: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None

    
class Login(BaseModel):
    phone_number: str
    password: str

class ReturnChatParticipantsModel(BaseModel):
    group_id: str
    user_ids: List[str]


class CreateGroupSchema(BaseModel):
    user_ids: List[str]
    
class SendMessageModel(BaseModel):
    chat_id: int
    sender_id: str
    messages: Optional[str] = None

    
    

