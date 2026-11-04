from pydantic import BaseModel, Field #type: ignore
from datetime import datetime
from typing import Literal, Optional, Dict, Any, List


class Message(BaseModel):
    timestamp: datetime
    speaker: Literal["User", "AI", "System"]
    message: str = Field(min_length=1, max_length=4000)


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
    message: str = Field(min_length=1, max_length=2000)
    current_code: Optional[str] = Field(default=None, max_length=60000)
    language_id: Literal[71, 63, 62, 54] = 71


class InterviewMessageResponse(BaseModel):
    ai_response: str
    should_switch_mode: bool
    new_mode: Optional[str] = None
    technical_data: Optional[Dict[str, Any]] = None


class CodeExecutionRequest(BaseModel):
    code: str = Field(max_length=60000)
    output: str = Field(max_length=16000)
    status: str = Field(max_length=80)  # "Accepted", "Wrong Answer", "Runtime Error", etc.


class CodeExecutionResponse(BaseModel):
    feedback: str
    execution_status: str


class InterviewEnd(BaseModel):
    transcript: List[Message] = Field(default_factory=list, max_length=120)
    final_code: Optional[str] = Field(default=None, max_length=60000)


class InterviewSummaryLite(BaseModel):
    duration: int
    interview_id: int
    scores: Optional[Dict[str, Any]] = None
    start_time: datetime
    end_time: datetime


class InterviewSummary(InterviewSummaryLite):
    transcript: Optional[List[Dict]] = None

class CodeContext(BaseModel):
    current_code: str = Field(max_length=60000)
    language_id: Literal[71, 63, 62, 54]
