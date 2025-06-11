from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = None

    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)

class ChatRequest(BaseModel):
    user_id: str
    message: str
    use_memory: bool = True

class ChatResponse(BaseModel):
    response: str
    used_memory: bool = False
    relevant_memories: List[str] = []

class Memory(BaseModel):
    user_id: str
    content: str
    embedding: Optional[List[float]] = None
    timestamp: datetime = None
    metadata: dict = {}

    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class ClearMemoriesRequest(BaseModel):
    user_id: str