from pydantic import BaseModel #type: ignore
from datetime import datetime
from typing import Literal, Optional, Dict, Any

class Message(BaseModel):
    timestamp: datetime
    speaker: str
    message: str


class Interview(BaseModel):
    user_id: int
    transcript: Optional[list[Message]] = None
    status: Literal['pending', 'active', 'completed']
    start_time: datetime
    end_time: Optional[datetime] = None
    scores: Optional[Dict[str, Any]] = None
    
class InterviewCreate(BaseModel):
   pass
    

class InterviewEnd(BaseModel):
    transcript: list[Message]
    
class InterviewSummaryLite(BaseModel):
    duration: int
    interview_id: int
    scores: Optional[Dict[str, Any]] = None
    start_time: datetime
    end_time: datetime
    

class InterviewSummary(InterviewSummaryLite):
    transcript: Optional[list[dict]] = None
