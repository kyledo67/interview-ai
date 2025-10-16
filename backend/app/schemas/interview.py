from pydantic import BaseModel #type: ignore
from datetime import datetime
from typing import Literal, Optional, Dict, Any, List


class Message(BaseModel):
    timestamp: datetime
    speaker: str
    message: str


class Interview(BaseModel):
    user_id: int
    transcript: Optional[List[Dict]] = None
    status: Literal['pending', 'active', 'completed']
    start_time: datetime
    end_time: Optional[datetime] = None
    scores: Optional[Dict[str, Any]] = None
    meta_info: Optional[Dict[str, Any]] = None 


class InterviewCreate(BaseModel):
    pass


class InterviewMessageRequest(BaseModel):
    message: str
    current_code: Optional[str] = None


class InterviewMessageResponse(BaseModel):
    ai_response: str
    should_switch_mode: bool
    new_mode: Optional[str] = None
    technical_data: Optional[Dict[str, Any]] = None


class CodeExecutionRequest(BaseModel):
    code: str
    output: str
    status: str  # "Accepted", "Wrong Answer", "Runtime Error", etc.


class CodeExecutionResponse(BaseModel):
    feedback: str
    execution_status: str


class InterviewEnd(BaseModel):
    transcript: List[Message]
    final_code: Optional[str] = None  


class InterviewSummaryLite(BaseModel):
    duration: int
    interview_id: int
    scores: Optional[Dict[str, Any]] = None
    start_time: datetime
    end_time: datetime


class InterviewSummary(InterviewSummaryLite):
    transcript: Optional[List[Dict]] = None